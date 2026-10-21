#!/usr/bin/env python3
"""Install the skill, retaining an explicit backup when replacing an existing one."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'skill' / 'ai-practical-video'


def install(target, replace=False, instructions_only=False):
    target = Path(target).expanduser().resolve()
    if target == SOURCE.resolve() or SOURCE.resolve() in target.parents or target in SOURCE.resolve().parents:
        raise ValueError('Installation target must be separate from the source tree')
    if not instructions_only and not (SOURCE / 'scripts' / 'local.json').is_file():
        raise ValueError('Run bootstrap.py first, or use --instructions-only to install before configuring the runtime')
    if target.exists():
        if not replace:
            raise ValueError(f'{target} already exists; inspect it and use --replace if appropriate')
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = target.parent / '.ai-practical-video-backups' / stamp
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(backup))
        print('Previous installation backed up:', backup)
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc', 'install-origin.json')
    shutil.copytree(SOURCE, target, ignore=ignore)
    for source in SOURCE.rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts and source.name != 'install-origin.json':
            copied = target / source.relative_to(SOURCE)
            if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(copied.read_bytes()).digest():
                raise RuntimeError(f'Installation checksum mismatch: {source.relative_to(SOURCE)}')
    (target / 'references' / 'install-origin.json').write_text(
        json.dumps({'source': str(SOURCE), 'instructions_only': instructions_only}, ensure_ascii=False, indent=2) + '\n')
    print('Installed:', target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    codex = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    parser.add_argument('--target', type=Path, default=codex / 'skills' / 'ai-practical-video')
    parser.add_argument('--replace', action='store_true')
    parser.add_argument('--instructions-only', action='store_true')
    args = parser.parse_args()
    try:
        install(args.target, args.replace, args.instructions_only)
    except ValueError as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
