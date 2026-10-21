#!/usr/bin/env python3
"""An optional, original gentle pluck bed; no downloaded music or voice changes."""
import argparse
import hashlib
import json
import math
import pathlib
import subprocess

import numpy as np
import soundfile as sf

SAMPLE_RATE = 48000
VERSION = 'original-plucks-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_note(buffer, start, midi, pan, gain=1.0):
    """Short sine partials with a soft attack, composed directly in this file."""
    count = min(round(.62 * SAMPLE_RATE), len(buffer) - start)
    if count <= 0:
        return
    t = np.arange(count, dtype=np.float64) / SAMPLE_RATE
    hz = 440 * 2 ** ((midi - 69) / 12)
    envelope = (1 - np.exp(-t / .006)) * np.exp(-t / .15)
    envelope *= np.minimum(1, np.maximum(0, (.62 - t) / .05))
    signal = (np.sin(2 * np.pi * hz * t)
              + .24 * np.sin(2 * np.pi * hz * 2 * t)
              + .06 * np.sin(2 * np.pi * hz * 3 * t)) * envelope * gain
    buffer[start:start + count, 0] += signal * math.sqrt((1 - pan) / 2)
    buffer[start:start + count, 1] += signal * math.sqrt((1 + pan) / 2)


def synth_bed(frames, scene_starts=()):
    """48 kHz stereo, 110 BPM, sparse C pentatonic plucks and soft transition pops."""
    bed = np.zeros((frames, 2), dtype=np.float64)
    beat = 60 / 110
    # An original 16-beat phrase with plenty of space for speech.
    phrase = [(0, 72, -.3), (2, 79, .3), (3.5, 76, -.15),
              (6, 81, .3), (7.5, 79, -.2), (10, 74, .2),
              (12, 76, -.25), (14.5, 72, .25)]
    for bar in range(math.ceil(frames / SAMPLE_RATE / (16 * beat))):
        for offset, midi, pan in phrase:
            add_note(bed, round((bar * 16 + offset) * beat * SAMPLE_RATE), midi, pan)
        for offset, midi in [(0, 60), (8, 67)]:
            add_note(bed, round((bar * 16 + offset) * beat * SAMPLE_RATE), midi, 0, .28)
    peak = float(np.max(np.abs(bed))) if frames else 0
    if peak:
        bed /= peak
    accents = np.zeros_like(bed)
    for seconds in scene_starts:
        start = round(seconds * SAMPLE_RATE)
        if not 0 < start < frames - round(.5 * SAMPLE_RATE):
            continue
        count = min(round(.10 * SAMPLE_RATE), frames - start)
        t = np.arange(count) / SAMPLE_RATE
        # A falling, softly windowed bubble; no noise samples or external assets.
        phase = 2 * np.pi * (640 * t - 1400 * t * t)
        signal = np.sin(phase) * np.sin(np.pi * np.arange(count) / max(1, count - 1)) ** 2
        signal *= np.exp(-t / .032) * .010
        accents[start:start + count] += signal[:, None]
    fade = np.minimum(1, np.arange(frames) / max(1, round(.15 * SAMPLE_RATE)))
    fade *= np.minimum(1, np.arange(frames)[::-1] / max(1, round(.6 * SAMPLE_RATE)))
    return bed * fade[:, None], accents * fade[:, None]


def duck_envelope(narration):
    """Speech-responsive background level; fast attack and smooth release."""
    frames = len(narration)
    if not frames:
        return np.empty(0, dtype=np.float64)
    block = round(.01 * SAMPLE_RATE)
    padded = np.pad(np.mean(narration ** 2, axis=1), (0, (-frames) % block))
    rms = np.sqrt(padded.reshape(-1, block).mean(axis=1))
    target = .046 - .030 * np.clip(rms / .025, 0, 1)
    levels = np.empty_like(target)
    level = float(target[0])
    for i, value in enumerate(target):
        tau = .035 if value < level else .32
        level += (1 - math.exp(-.01 / tau)) * (float(value) - level)
        levels[i] = level
    return np.interp(np.arange(frames), np.arange(len(levels)) * block, levels)


def mix_audio(narration, frames, scene_starts=()):
    if narration.ndim != 2 or narration.shape[1] != 2:
        raise ValueError('narration must be stereo')
    delta = frames - len(narration)
    if delta < 0:
        raise ValueError('timeline would truncate narration')
    if delta > round(.04 * SAMPLE_RATE):
        raise ValueError('timeline tail exceeds the allowed 40 ms rounding tail')
    if not np.isfinite(narration).all():
        raise ValueError('non-finite narration samples')
    narration = np.pad(narration, ((0, delta), (0, 0)))
    bed, accents = synth_bed(frames, scene_starts)
    duck = duck_envelope(narration)
    background = bed * duck[:, None] + accents
    mixed = narration + background
    peak = float(np.max(np.abs(mixed))) if len(mixed) else 0
    gain = min(1.0, .94 / peak) if peak else 1.0
    return background * gain, mixed * gain, {
        'rounding_tail_seconds': delta / SAMPLE_RATE,
        'peak_before_ceiling': peak,
        'ceiling_gain': gain,
        'peak_after_ceiling': float(np.max(np.abs(mixed * gain))) if len(mixed) else 0,
        'bed_gain_min': float(duck.min()) if frames else 0,
        'bed_gain_max': float(duck.max()) if frames else 0,
    }


def create(run):
    timeline_path = run / 'timeline.json'
    narration_path = run / 'voice/narration.wav'
    timeline = json.loads(timeline_path.read_text(encoding='utf-8'))
    frames = round(float(timeline['duration']) * SAMPLE_RATE)
    if frames <= 0:
        raise ValueError('timeline duration must be positive')
    # The only speech operation is sample-rate/channel conversion, with no tempo,
    # trimming, fades, or synthetic pauses applied to the narration.
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(narration_path),
                          '-f', 'f32le', '-acodec', 'pcm_f32le', '-ac', '2',
                          '-ar', str(SAMPLE_RATE), '-'], check=True, capture_output=True).stdout
    narration = np.frombuffer(raw, dtype='<f4').reshape(-1, 2).astype(np.float64)
    starts = [float(scene['start']) for scene in timeline['scenes']]
    bed, mixed, measurements = mix_audio(narration, frames, starts)
    bed_path, mixed_path = run / 'voice/editorial-bed.wav', run / 'voice/mix.wav'
    sf.write(bed_path, bed, SAMPLE_RATE, subtype='PCM_24')
    sf.write(mixed_path, mixed, SAMPLE_RATE, subtype='PCM_24')
    metadata = {
        'version': VERSION,
        'source': 'original procedural synthesis',
        'license': 'Original composition for this user project; voice rights remain separate.',
        'music': {'tempo_bpm': 110, 'scale': 'C pentatonic', 'instruments': 'sine-partial plucks'},
        'narration_sha256': sha(narration_path),
        'timeline_sha256': sha(timeline_path),
        'bed_sha256': sha(bed_path),
        'mix_sha256': sha(mixed_path),
        'sample_rate': SAMPLE_RATE, 'channels': 2, 'frames': frames,
        'duration': frames / SAMPLE_RATE,
        'speech_stretched': False, 'speech_truncated': False,
        'measurements': measurements,
    }
    (run / 'voice/mix.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    print(json.dumps(create(pathlib.Path(args.run).resolve()), ensure_ascii=False, indent=2))
