#!/usr/bin/env python3
"""Explicit online voice preview: whole-scene prosody and service word timestamps.

This optional adapter never changes the default local voice. Generated audio's
publication rights are not verified by the open-source client's software license.
"""
import argparse
import asyncio
import difflib
import importlib.metadata
import pathlib
import re
import shutil
import subprocess
import tempfile

from pipeline import digest, fail, lock, read, reconcile, seal, sha, validate_script, write

VERSION = '1.0.0'
SR = 48000
TRIM = {'threshold_db': -45, 'frame_ms': 10, 'keep_ms': 30}


def configuration(config=None, voice=None, rate='+3%', cache=None):
    if config and voice:
        raise ValueError('Choose --config or --voice; never silently override a saved voice')
    if config:
        conf = read(config) if not isinstance(config, dict) else dict(config)
    elif voice:
        conf = {'provider': 'edge-online-preview', 'voice_id': voice, 'rate': rate,
                'approved_style_change': True, 'scene_gap': .28, 'tail': .6}
    else:
        raise ValueError('Explicit --voice or an approved --config is required')
    if conf.get('provider') != 'edge-online-preview' or conf.get('approved_style_change') is not True:
        raise ValueError('Online preview requires provider edge-online-preview and approved_style_change: true')
    if not re.fullmatch(r'[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural', conf.get('voice_id', '')):
        raise ValueError('Configure an explicit neural voice ID')
    conf.setdefault('rate', '+3%')
    if not re.fullmatch(r'[+-]\d+%', conf['rate']):
        raise ValueError('rate must be an explicit percentage such as +3%')
    conf.setdefault('scene_gap', .28)
    conf.setdefault('tail', .6)
    if not 0 <= conf['scene_gap'] <= .28 or conf['tail'] != .6:
        raise ValueError('Scene gaps must be 0–0.28 seconds and the final tail 0.6 seconds')
    conf.update(source_service='Microsoft Edge online speech service',
                publication_rights='not_verified', cost_per_generation=0,
                cost_note='No API key, paid API or credit-consuming operation in this workflow; not a service pricing or rights guarantee')
    if cache:
        conf['cache'] = str(cache)
    return conf


async def synthesize(text, voice, rate, mp3):
    import edge_tts
    words = []
    # One request per semantic scene. Do not pre-split punctuation or replace English.
    with pathlib.Path(mp3).open('wb') as output:
        async for item in edge_tts.Communicate(text, voice, rate=rate, boundary='WordBoundary').stream():
            if item['type'] == 'audio':
                output.write(item['data'])
            elif item['type'] == 'WordBoundary':
                words.append({'text': item['text'], 'start': item['offset'] / 1e7,
                              'end': (item['offset'] + item['duration']) / 1e7})
    if not words or not pathlib.Path(mp3).stat().st_size:
        raise RuntimeError('The online service returned no audio or word timestamps; no fallback was attempted')
    return words


def trim_samples(samples, sample_rate=SR):
    """Remove only leading/trailing quiet frames; preserve all internal pauses."""
    import numpy as np
    if samples.ndim != 1 or not len(samples):
        raise ValueError('Expected non-empty mono audio')
    size = max(1, round(sample_rate * TRIM['frame_ms'] / 1000))
    frames = np.pad(samples, (0, (-len(samples)) % size)).reshape(-1, size)
    active = np.flatnonzero(np.sqrt(np.mean(frames.astype('float64') ** 2, axis=1)) > 10 ** (TRIM['threshold_db'] / 20))
    if not len(active):
        raise ValueError('The service returned silence')
    keep = round(sample_rate * TRIM['keep_ms'] / 1000)
    first = max(0, int(active[0]) * size - keep)
    last = min(len(samples), (int(active[-1]) + 1) * size + keep)
    return samples[first:last], first / sample_rate, (len(samples) - last) / sample_rate


def align_characters(text, words, lead, duration):
    """Anchor matching characters to WordBoundary spans; interpolate punctuation.

    Character positions within a multi-character word are interpolated inside
    that word, not claimed as phoneme-level alignment. Low lexical coverage fails.
    """
    if not text or not words or duration <= 0:
        raise ValueError('Text, real word timestamps and measured duration are required')
    source = []
    for word in words:
        chars = [c for c in word['text'] if c.isalnum()]
        a, b = max(0, word['start'] - lead), min(duration, word['end'] - lead)
        if b <= a:
            continue
        for i, char in enumerate(chars):
            source.append((char.casefold(), a + (b - a) * i / len(chars), a + (b - a) * (i + 1) / len(chars)))
    target = [(i, c.casefold()) for i, c in enumerate(text) if c.isalnum()]
    spans = [None] * len(text)
    matched = 0
    for block in difflib.SequenceMatcher(None, [c for _, c in target], [x[0] for x in source], autojunk=False).get_matching_blocks():
        for n in range(block.size):
            spans[target[block.a + n][0]] = source[block.b + n][1:]
            matched += 1
    coverage = matched / max(1, len(target))
    if coverage < .65:
        raise ValueError(f'WordBoundary/text match is only {coverage:.0%}; inspect pronunciation and timestamps before continuing')
    known = [i for i, span in enumerate(spans) if span is not None]
    for i in range(len(spans)):
        if spans[i] is not None:
            continue
        left = next((k for k in reversed(known) if k < i), None)
        right = next((k for k in known if k > i), None)
        a = spans[left][1] if left is not None else 0
        b = spans[right][0] if right is not None else duration
        lo, hi = (-1 if left is None else left), (len(spans) if right is None else right)
        gap = max(0, b - a)
        spans[i] = (a + gap * (i - lo - 1) / max(1, hi - lo - 1),
                    a + gap * (i - lo) / max(1, hi - lo - 1))
    return {'method': 'service-word-boundaries; character interpolation within words and unmatched punctuation',
            'lexical_match': coverage,
            'characters': [{'text': c, 'start': max(0, min(duration, a)),
                            'end': max(0, min(duration, b))} for c, (a, b) in zip(text, spans)]}


def caption_segments(alignment, maximum=20):
    chars = alignment['characters']
    result = []
    start = 0
    while start < len(chars):
        end = min(start + maximum, len(chars))
        if end < len(chars):
            breaks = [i + 1 for i in range(start + min(7, maximum - 1), end)
                      if chars[i]['text'] in '，。！？；：,.!?;:']
            if breaks:
                end = breaks[-1]
        selected = chars[start:end]
        a = selected[0]['start']
        b = max(c['end'] for c in selected)
        if b <= a:
            raise ValueError('A caption has no measurable speech span')
        result.append({'text': ''.join(c['text'] for c in selected), 'start': a, 'end': b})
        start = end
    return result


def render_scene(text, identity, cache):
    import soundfile as sf
    key = digest({'text': text, 'voice': identity, 'trim': TRIM, 'adapter_version': VERSION})
    target = pathlib.Path(cache) / key
    target.parent.mkdir(parents=True, exist_ok=True)
    names = ['raw.mp3', 'words.json', 'trimmed.wav', 'trim.json']
    metadata = read(target / 'cache.json') if (target / 'cache.json').exists() else {}
    reused = all((target / name).is_file() and metadata.get('hashes', {}).get(name) == sha(target / name) for name in names)
    if not reused:
        with tempfile.TemporaryDirectory(dir=target.parent, prefix=key[:10] + '-') as temporary:
            work = pathlib.Path(temporary)
            words = asyncio.run(synthesize(text, identity['voice_id'], identity['rate'], work / 'raw.mp3'))
            write(work / 'words.json', words)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(work / 'raw.mp3'), '-ar', str(SR), '-ac', '1', str(work / 'decoded.wav')], check=True)
            audio, _ = sf.read(work / 'decoded.wav', dtype='float32')
            audio, leading, trailing = trim_samples(audio)
            sf.write(work / 'trimmed.wav', audio, SR, subtype='PCM_16')
            write(work / 'trim.json', {'leading_seconds': leading, 'trailing_seconds': trailing,
                                      'duration': len(audio) / SR, 'policy': TRIM})
            write(work / 'cache.json', {'key': key, 'hashes': {name: sha(work / name) for name in names}})
            target.mkdir(exist_ok=True)
            for name in names + ['cache.json']:
                shutil.copyfile(work / name, target / name)
    return target, key, reused


def generate(run, conf):
    import numpy as np
    import soundfile as sf
    run = pathlib.Path(run).resolve()
    conf = configuration(conf)
    validate_script(run)
    if reconcile(run)['stages'].get('script', {}).get('state') != 'complete':
        raise ValueError('Seal the verified script before voice generation')
    try:
        engine_version = importlib.metadata.version('edge-tts')
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError('Optional dependency missing: install edge-tts==7.3.1 in the selected Python environment') from exc
    conf.setdefault('cache', str(run.parent.parent / 'voice-cache-edge-preview'))
    conf['engine_version'] = engine_version
    write(run / 'voice/config.json', conf)
    identity = {key: conf[key] for key in ['provider', 'voice_id', 'rate', 'engine_version', 'source_service', 'publication_rights']}
    identity['adapter_version'] = VERSION
    scenes, segments, outputs, whole, scene_records = [], [], [], [], []
    cursor = 0.0
    script = read(run / 'script/script.json')
    for index, scene in enumerate(script['scenes']):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', scene['id']):
            raise ValueError('Scene IDs must be safe filenames')
        cache, key, reused = render_scene(scene['narration'], identity, conf['cache'])
        names = {'raw.mp3': 'raw.mp3', 'words.json': 'words.json', 'trimmed.wav': 'wav', 'trim.json': 'trim.json'}
        for name, suffix in names.items():
            relative = f"voice/{scene['id']}.{suffix}"
            shutil.copyfile(cache / name, run / relative)
            outputs.append(relative)
        audio, sample_rate = sf.read(cache / 'trimmed.wav', dtype='float32')
        if sample_rate != SR:
            raise ValueError('Cached sample rate differs from the adapter sample rate')
        duration = len(audio) / SR
        trim = read(cache / 'trim.json')
        alignment = align_characters(scene['narration'], read(cache / 'words.json'), trim['leading_seconds'], duration)
        alignment_file = f"voice/{scene['id']}.alignment.json"
        write(run / alignment_file, alignment)
        outputs.append(alignment_file)
        for part in caption_segments(alignment):
            segments.append({**part, 'scene_id': scene['id'], 'start': cursor + part['start'],
                             'end': cursor + part['end'], 'file': f"voice/{scene['id']}.wav",
                             'cache_key': key, 'cache_hit': reused, 'sha256': sha(cache / 'trimmed.wav'),
                             'timing_source': 'WordBoundary'})
        begin = cursor
        whole.append(audio)
        cursor += duration
        scene_records.append({'id': scene['id'], 'spoken': scene['narration'], 'start': begin,
                              'speech_end': cursor, 'cache_key': key, 'cache_hit': reused,
                              'alignment': alignment_file, 'raw_audio_sha256': sha(cache / 'raw.mp3'),
                              'word_timestamps_sha256': sha(cache / 'words.json')})
        gap = conf['scene_gap'] if index < len(script['scenes']) - 1 else conf['tail']
        pause = np.zeros(round(SR * gap), dtype='float32')
        whole.append(pause)
        cursor += len(pause) / SR
        scenes.append({**scene, 'start': begin, 'end': cursor})
    sf.write(run / 'voice/narration.wav', np.concatenate(whole), SR, subtype='PCM_16')
    write(run / 'voice/measured-scenes.json', scenes)
    write(run / 'voice/manifest.json', {'script_hash': sha(run / 'script/script.json'), 'voice': identity,
          'segments': segments, 'scenes': scene_records, 'duration': cursor, 'cost': 0,
          'publication_rights': 'not_verified', 'license': 'edge-tts client LGPLv3 (srt_composer MIT); service audio publication rights not verified',
          'range_ok': 60 <= cursor <= 90, 'trim_policy': TRIM, 'scene_gap': conf['scene_gap'], 'tail': conf['tail']})
    if not 60 <= cursor <= 90:
        reason = f'Measured narration is {cursor:.2f}s, outside 60–90s; revise the script, never pad, truncate or accelerate to fit'
        fail(run, 'voice', reason)
        raise ValueError(reason)
    seal(run, 'voice', ['script/script.json', 'voice/config.json'],
         ['voice/manifest.json', 'voice/narration.wav', 'voice/measured-scenes.json'] + outputs)
    print(f'VOICE PREVIEW: {cursor:.2f}s; whole-scene synthesis; publication_rights=not_verified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--config')
    group.add_argument('--voice')
    parser.add_argument('--rate', default='+3%')
    parser.add_argument('--cache')
    args = parser.parse_args()
    settings = configuration(args.config, args.voice, args.rate, args.cache)
    with lock(pathlib.Path(args.run).resolve().parent.parent):
        generate(args.run, settings)
