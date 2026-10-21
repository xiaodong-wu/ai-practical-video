#!/usr/bin/env python3
"""Build a private local runtime from pinned dependencies. No hosted API calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import venv

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / 'skill' / 'ai-practical-video'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def download_verified(destination, record):
    """Never silently replace an existing model whose identity has changed."""
    if destination.exists():
        if destination.stat().st_size != record['bytes'] or sha256(destination) != record['sha256']:
            raise ValueError(f'Existing model checksum mismatch: {destination}; inspect or move it before retrying')
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.part')
    try:
        with urllib.request.urlopen(record['source'], timeout=90) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        if temporary.stat().st_size != record['bytes'] or sha256(temporary) != record['sha256']:
            raise ValueError(f'Download checksum mismatch: {destination.name}')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def choose_font(explicit=None):
    candidates = [Path(explicit).expanduser()] if explicit else [
        Path('/System/Library/Fonts/Hiragino Sans GB.ttc'),
        Path('/System/Library/Fonts/STHeiti Light.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'),
    ]
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise ValueError('No CJK font found. Install Noto Sans CJK or pass --font /path/to/chinese-font.ttc')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT / '.runtime')
    parser.add_argument('--font', help='CJK font file for covers')
    parser.add_argument('--plan', action='store_true', help='Print planned operations without downloading or modifying anything')
    args = parser.parse_args()
    runtime = args.runtime.expanduser().resolve()
    refs = SKILL / 'references'
    models = json.loads((refs / 'model-lock.json').read_text())
    if args.plan:
        print(json.dumps({'runtime': str(runtime), 'python': '3.12', 'steps': [
            'create isolated Python venv', 'install exact requirements-lock.txt',
            'npm ci with pinned lockfile', 'install Playwright Chromium',
            'download and SHA256-verify models', 'write private local configuration'],
            'model_bytes': sum(item['bytes'] for item in models.values()),
            'paid_services': False}, ensure_ascii=False, indent=2))
        return
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Use Python 3.12 for the validated dependency lock: python3.12 bootstrap.py')
    if os.name != 'posix':
        raise SystemExit('The pipeline uses POSIX file locking. Use macOS or Linux; Windows is not supported.')
    missing = [name for name in ('node', 'npm', 'ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        raise SystemExit('Install these system dependencies first: ' + ', '.join(missing))
    if int(subprocess.check_output(['node', '-p', 'process.versions.node.split(".")[0]'], text=True)) < 20:
        raise SystemExit('Node.js 20 or newer is required')
    font = choose_font(args.font)
    runtime.mkdir(parents=True, exist_ok=True)
    venv.EnvBuilder(with_pip=True).create(runtime / 'venv')
    python = runtime / 'venv' / 'bin' / 'python'
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(refs / 'requirements-lock.txt')], check=True)
    shutil.copyfile(refs / 'node-package.json', runtime / 'package.json')
    shutil.copyfile(refs / 'node-package-lock.json', runtime / 'package-lock.json')
    subprocess.run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=runtime, check=True)
    subprocess.run(['node', str(runtime / 'node_modules' / 'playwright' / 'cli.js'), 'install', 'chromium'], check=True)
    for name, record in models.items():
        print('Verify model:', name, flush=True)
        download_verified(runtime / 'models' / name, record)
    voice = {'provider': 'kokoro-local', 'voice_id': 'zf_001', 'speed': 1.0,
             'engine_version': 'kokoro-onnx 0.6.0 / misaki 0.9.4',
             'model': str(runtime / 'models' / 'kokoro-v1.1-zh.onnx'),
             'voices': str(runtime / 'models' / 'voices-v1.1-zh.bin'),
             'model_sha256': models['kokoro-v1.1-zh.onnx']['sha256'],
             'voices_sha256': models['voices-v1.1-zh.bin']['sha256'],
             'cache': str(runtime / 'voice-cache'), 'cost_per_generation': 0,
             'license': 'Apache-2.0 model / MIT kokoro-onnx'}
    write_json(runtime / 'voice.json', voice)
    write_json(SKILL / 'scripts' / 'local.json', {
        'python': str(python), 'playwright_from': str(runtime / 'package.json'),
        'voice_config': str(runtime / 'voice.json'), 'cover_font': str(font)})
    print('Runtime configured. Next: python3 install.py; python3 doctor.py')


if __name__ == '__main__':
    main()
