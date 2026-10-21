import asyncio
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'skill/ai-practical-video/scripts'))
import voice_edge_preview as voice
from pipeline import init, read, seal, write


class VoicePreview(unittest.TestCase):
    def test_explicit_voice_is_required_and_paid_or_default_fallback_is_rejected(self):
        with self.assertRaises(ValueError):
            voice.configuration()
        with self.assertRaises(ValueError):
            voice.configuration({'provider': 'kokoro-local', 'voice_id': 'zf_001'})
        with self.assertRaises(ValueError):
            voice.configuration({'provider': 'edge-online-preview', 'voice_id': 'zh-CN-XiaoxiaoNeural'})
        configured = voice.configuration(voice='zh-CN-XiaoxiaoNeural')
        self.assertEqual(configured['publication_rights'], 'not_verified')
        self.assertEqual(configured['rate'], '+3%')

    def test_no_padding_duration_configuration(self):
        configured = voice.configuration(voice='zh-CN-XiaoxiaoNeural')
        configured['scene_gap'] = 2
        with self.assertRaises(ValueError):
            voice.configuration(configured)

    def test_whole_scene_is_one_request_with_original_punctuation_and_english(self):
        calls = []
        class FakeCommunicate:
            def __init__(self, text, selected, **kwargs):
                calls.append((text, selected, kwargs))
            async def stream(self):
                yield {'type': 'audio', 'data': b'actual-audio-placeholder'}
                yield {'type': 'WordBoundary', 'text': 'AI', 'offset': 1000000, 'duration': 2000000}
        text = 'AI 整理好了。接下来，核对三处数字！'
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(sys.modules, {'edge_tts': type('FakeModule', (), {'Communicate': FakeCommunicate})}):
                words = asyncio.run(voice.synthesize(text, 'zh-CN-XiaoxiaoNeural', '+3%', pathlib.Path(directory) / 'raw.mp3'))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], text)
        self.assertEqual(calls[0][2]['boundary'], 'WordBoundary')
        self.assertEqual(words[0], {'text': 'AI', 'start': .1, 'end': .3})

    def test_trim_preserves_internal_silence_and_reports_leading_offset(self):
        import numpy as np
        samples = np.concatenate([np.zeros(100), np.ones(100) * .1, np.zeros(100), np.ones(100) * .1, np.zeros(200)])
        audio, leading, trailing = voice.trim_samples(samples, 1000)
        self.assertAlmostEqual(leading, .07)
        self.assertAlmostEqual(trailing, .17)
        self.assertEqual(len(audio), 360)
        self.assertTrue(np.all(audio[130:230] == 0))
        with self.assertRaises(ValueError):
            voice.trim_samples(np.zeros(100), 1000)

    def test_captions_use_measured_words_after_trim_and_keep_original_text(self):
        text = '先用AI整理客户名单，接着检查重复邮箱。'
        words = [{'text': '先用', 'start': .2, 'end': .6},
                 {'text': 'AI', 'start': .7, 'end': 1},
                 {'text': '整理客户名单', 'start': 1.1, 'end': 2.5},
                 {'text': '接着检查重复邮箱', 'start': 3.2, 'end': 5.2}]
        aligned = voice.align_characters(text, words, .2, 5.1)
        captions = voice.caption_segments(aligned, maximum=12)
        self.assertEqual(''.join(x['text'] for x in captions), text)
        self.assertTrue(all(len(x['text']) <= 12 for x in captions))
        self.assertAlmostEqual(captions[0]['start'], 0)
        self.assertAlmostEqual(captions[1]['start'], 3.0)
        self.assertTrue(all(a['end'] <= b['start'] for a, b in zip(captions, captions[1:])))
        self.assertEqual(aligned['lexical_match'], 1)

    def test_unrelated_word_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            voice.align_characters('客户名单需要核对', [{'text': '完全错误', 'start': 0, 'end': 2}], 0, 3)

    def test_cache_verifies_raw_words_and_audio_before_reuse(self):
        import numpy as np
        import soundfile as sf
        requests = []
        async def fake_service(text, selected, rate, path):
            requests.append(text)
            sf.write(path, np.sin(np.arange(voice.SR) * .05) * .1, voice.SR, format='WAV')
            return [{'text': text, 'start': 0, 'end': 1}]
        identity = {'voice_id': 'zh-CN-XiaoxiaoNeural', 'rate': '+3%', 'engine_version': 'test'}
        with tempfile.TemporaryDirectory() as directory, patch.object(voice, 'synthesize', fake_service):
            target, key, reused = voice.render_scene('检查结果。', identity, directory)
            self.assertFalse(reused)
            self.assertTrue(voice.render_scene('检查结果。', identity, directory)[2])
            write(target / 'words.json', [{'text': 'corrupted'}])
            self.assertFalse(voice.render_scene('检查结果。', identity, directory)[2])
            self.assertEqual(requests, ['检查结果。', '检查结果。'])

    def test_pipeline_seals_all_evidence_and_rejects_short_audio(self):
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory() as directory:
            run = init(directory, 'test')
            for stage in ['research', 'demo']:
                (run / (stage + '.txt')).write_text(stage)
                seal(run, stage, [], [stage + '.txt'])
            write(run / 'script/script.json', {'scenes': [
                {'id': 's01', 'narration': 'AI 检查客户名单，随后核对邮箱。'},
                {'id': 's02', 'narration': '先看结果，再判断是否需要补充规则。'}]})
            seal(run, 'script', [], ['script/script.json'])
            cache = pathlib.Path(directory) / 'mock-cache'
            cache.mkdir()
            write(cache / 'trim.json', {'leading_seconds': 0})
            (cache / 'raw.mp3').write_bytes(b'test-raw-audio')
            audio_length = [30]
            calls = []
            def fake_render(text, identity, root):
                calls.append(text)
                sf.write(cache / 'trimmed.wav', np.ones(voice.SR * audio_length[0]) * .02, voice.SR)
                write(cache / 'words.json', [{'text': text, 'start': 0, 'end': audio_length[0]}])
                return cache, 'test-cache-key', False
            with patch.object(voice, 'validate_script'), patch.object(voice, 'render_scene', fake_render), patch.object(voice.importlib.metadata, 'version', return_value='test'):
                voice.generate(run, voice.configuration(voice='zh-CN-XiaoxiaoNeural'))
                manifest = read(run / 'manifest.json')
                self.assertEqual(manifest['stages']['voice']['state'], 'complete')
                self.assertIn('voice/s01.raw.mp3', manifest['stages']['voice']['outputs'])
                self.assertIn('voice/s02.alignment.json', manifest['stages']['voice']['outputs'])
                data = read(run / 'voice/manifest.json')
                self.assertAlmostEqual(data['duration'], 60.88)
                self.assertEqual(len(calls), 2)
                self.assertEqual(data['publication_rights'], 'not_verified')
                audio_length[0] = 1
                with self.assertRaisesRegex(ValueError, 'outside 60–90s'):
                    voice.generate(run, voice.configuration(voice='zh-CN-XiaoxiaoNeural'))
                self.assertEqual(read(run / 'manifest.json')['stages']['voice']['state'], 'failed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
