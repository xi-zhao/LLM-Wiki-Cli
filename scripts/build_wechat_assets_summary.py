#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
KB_BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
BASE = KB_BASE / 'materials' / 'wechat'

def classify(name: str):
    lower = name.lower()
    if name.startswith('001.'):
        return 'cover'
    if any(k in lower for k in ['chart', 'table', 'fig', 'flow', 'arch', 'framework']):
        return 'body-core'
    return 'unknown'

def resolve_target(folder_arg: str) -> Path:
    candidate = Path(folder_arg).expanduser()
    if not candidate.is_absolute():
        candidate = BASE / folder_arg
    return candidate.resolve()


def iter_targets(folder_arg: str | None):
    if folder_arg:
        target = resolve_target(folder_arg)
        if not target.is_dir():
            raise SystemExit(f'folder not found: {target}')
        return [target]
    return [folder for folder in sorted(BASE.iterdir()) if folder.is_dir()]


def build_summary(folder: Path):
    meta = {}
    meta_path = folder / 'meta.json'
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    images = []
    img_json = folder / 'images.json'
    if img_json.exists():
        try:
            images = json.loads(img_json.read_text())
        except Exception:
            images = []
    existing_files = sorted((folder / 'images').glob('*')) if (folder / 'images').exists() else []
    total_images = len(existing_files)
    cover = 1 if total_images > 0 else 0
    body_core = 0
    body_supporting = 0
    unknown = 0
    core_lines = []
    for f in existing_files:
        bucket = classify(f.name)
        if bucket == 'cover':
            pass
        elif bucket == 'body-core':
            body_core += 1
            core_lines.append(f'- {f.name} — body-core')
        else:
            unknown += 1
    if total_images > 0 and not core_lines:
        core_lines.append(f'- {existing_files[0].name} — likely cover')
    broken = sum(1 for item in images if isinstance(item, dict) and item.get('error'))
    md = []
    md.append('# Assets')
    md.append('')
    md.append('## Summary')
    md.append(f'- title: {meta.get("title", folder.name)}')
    md.append(f'- total_images: {total_images}')
    md.append(f'- likely_cover: {cover}')
    md.append(f'- body_core_count: {body_core}')
    md.append(f'- body_supporting_count: {body_supporting}')
    md.append(f'- unknown_count: {unknown}')
    md.append('')
    md.append('## Notes')
    md.append('- duplicate handling: not fully normalized yet')
    md.append(f'- broken/missing assets: {broken}')
    md.append('- confidence: low-to-medium (heuristic classification)')
    md.append('')
    md.append('## Core assets')
    md.extend(core_lines or ['- none identified yet'])
    (folder / 'assets.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(folder.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', nargs='?', help='Optional folder path or folder name under materials/wechat')
    args = ap.parse_args()

    for folder in iter_targets(args.folder):
        build_summary(folder)


if __name__ == '__main__':
    main()
