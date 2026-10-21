import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'skill/ai-practical-video/scripts'))
from pipeline import init, write, read, seal
from produce import timeline


class CaptureRange(unittest.TestCase):
    def test_timeline_maps_action_range_and_rejects_invalid_indices(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = init(temporary, 'action range regression')
            write(run / 'research/candidates.json', [])
            seal(run, 'research', [], ['research/candidates.json'])
            (run / 'demo/capture').mkdir()
            write(run / 'demo/capture/log.json', {'actions': [
                {'start': 1.0, 'end': 3.0}, {'start': 3.2, 'end': 6.0}, {'start': 6.2, 'end': 9.0}]})
            (run / 'demo/capture/recording.webm').write_bytes(b'timeline fixture; no media decoding in this test')
            seal(run, 'demo', [], ['demo/capture/log.json', 'demo/capture/recording.webm'])
            write(run / 'script/script.json', {'test': True})
            seal(run, 'script', [], ['script/script.json'])
            write(run / 'voice/manifest.json', {'duration': 60, 'script_hash': 'fixture', 'segments': [
                {'start': 0, 'end': 60, 'text': '区间映射测试'}]})
            scenes = [{'id': 'input-and-calculate', 'start': 0, 'end': 30, 'capture_index': 0, 'capture_end_index': 1},
                      {'id': 'single-action', 'start': 30, 'end': 60, 'capture_index': 2}]
            write(run / 'voice/measured-scenes.json', scenes)
            seal(run, 'voice', [], ['voice/manifest.json', 'voice/measured-scenes.json'])
            timeline(run)
            for relative in ('film/timeline.json', 'timeline.json'):
                result = read(run / relative)['scenes']
                self.assertEqual((result[0]['clip_start'], result[0]['clip_end']), (1.0, 5.85))
                self.assertEqual((result[1]['clip_start'], result[1]['clip_end']), (6.2, 8.85))
            for start, end in ((-1, 1), (1, 0), (0, 3), (0, '1')):
                with self.subTest(start=start, end=end):
                    scenes[0].update(capture_index=start, capture_end_index=end)
                    write(run / 'voice/measured-scenes.json', scenes)
                    seal(run, 'voice', [], ['voice/manifest.json', 'voice/measured-scenes.json'])
                    with self.assertRaisesRegex(ValueError, 'capture range must satisfy'):
                        timeline(run)


if __name__ == '__main__':
    unittest.main()
