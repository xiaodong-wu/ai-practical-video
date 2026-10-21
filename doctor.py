#!/usr/bin/env python3
"""Read-only local runtime checks; does not generate audio or contact paid services."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from bootstrap import sha256

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', type=Path, default=ROOT / 'skill' / 'ai-practical-video')
    args = parser.parse_args()
    skill = args.skill.expanduser().resolve()
    config = skill / 'scripts' / 'local.json'
    if not config.exists():
        raise SystemExit('Missing scripts/local.json. Run bootstrap.py first.')
    local = json.loads(config.read_text())
    for command in ('node', 'ffmpeg', 'ffprobe'):
        if not shutil.which(command):
            raise SystemExit(f'Missing executable: {command}')
    for key in ('python', 'playwright_from', 'voice_config', 'cover_font'):
        if not Path(local.get(key, '')).is_file():
            raise SystemExit(f'Missing or invalid configuration: {key}')
    voice = json.loads(Path(local['voice_config']).read_text())
    if voice.get('provider') != 'kokoro-local' or voice.get('cost_per_generation') != 0:
        raise SystemExit('The bundled adapter requires free local Kokoro.')
    lock = json.loads((skill / 'references' / 'model-lock.json').read_text())
    for key in ('model', 'voices'):
        path = Path(voice[key])
        record = lock.get(path.name)
        if not record or not path.is_file() or sha256(path) != record['sha256']:
            raise SystemExit(f'Model identity check failed: {key}')
    subprocess.run([local['python'], '-c', 'import kokoro_onnx, misaki, soundfile, numpy, PIL, yaml; from misaki import zh; zh.ZHG2P(version="1.1"); print("Python imports and Chinese phonemizer OK")'], check=True)
    code = "const {createRequire}=require('node:module');const p=createRequire(process.argv[1])('playwright');(async()=>{const b=await p.chromium.launch({headless:true});await b.close();console.log('Playwright Chromium OK')})().catch(e=>{console.error(e);process.exit(1)})"
    subprocess.run(['node', '-e', code, local['playwright_from']], check=True)
    print('Ready: pinned models, free local voice, browser, encoder and cover font are available.')


if __name__ == '__main__':
    main()
