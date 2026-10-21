import pathlib
import sys
import hashlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'skill/ai-practical-video/scripts'))
from voice import spoken_text, verify_models


class Pronunciation(unittest.TestCase):
    def test_missing_english_names_fail_before_synthesis(self):
        with self.assertRaisesRegex(ValueError, 'ChatGPT, Excel'):
            spoken_text('用 ChatGPT 整理 Excel 客户表。', {})

    def test_explicit_chinese_readings_preserve_names(self):
        self.assertEqual(
            spoken_text('用 AI 和 Codex 整理表格。', {'AI': '诶艾', 'Codex': '扣德克斯'}),
            '用 诶艾 和 扣德克斯 整理表格。')

    def test_modified_model_is_rejected_before_synthesis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            model, voices = root / 'model.onnx', root / 'voices.bin'
            model.write_bytes(b'expected model')
            voices.write_bytes(b'expected voices')
            config = {'model': str(model), 'voices': str(voices),
                      'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
                      'voices_sha256': hashlib.sha256(voices.read_bytes()).hexdigest()}
            self.assertEqual(verify_models(config)['model_sha'], config['model_sha256'])
            model.write_bytes(b'modified model')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch for model'):
                verify_models(config)


if __name__ == '__main__':
    unittest.main()
