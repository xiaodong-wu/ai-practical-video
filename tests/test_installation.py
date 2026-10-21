import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('release_' + name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load('bootstrap')
installer = load('install')


class Installation(unittest.TestCase):
    def test_verified_model_reuses_existing_file_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'model.onnx'
            p.write_bytes(b'model bytes')
            record = {'bytes': 11, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            with patch.object(bootstrap.urllib.request, 'urlopen', side_effect=AssertionError('unexpected network')):
                bootstrap.download_verified(p, record)

    def test_changed_existing_model_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'model.onnx'
            p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                bootstrap.download_verified(p, {'bytes': 11, 'sha256': '0' * 64})
            self.assertEqual(p.read_bytes(), b'changed')

    def test_install_refuses_unrequested_replace_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'ai-practical-video'
            target.mkdir()
            (target / 'user-file.txt').write_text('keep me')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                installer.install(target, instructions_only=True)
            installer.install(target, replace=True, instructions_only=True)
            backups = list((Path(tmp) / '.ai-practical-video-backups').glob('*/user-file.txt'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), 'keep me')
            self.assertTrue((target / 'SKILL.md').is_file())

    def test_install_cannot_replace_source(self):
        with self.assertRaisesRegex(ValueError, 'separate'):
            installer.install(installer.SOURCE, replace=True, instructions_only=True)


if __name__ == '__main__':
    unittest.main()
