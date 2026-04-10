#!/usr/bin/env python3
import argparse, hashlib, json, os, re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
KB_BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
BASE = KB_BASE / 'materials' / 'wechat'
BAD_SUFFIX_RE = re.compile(r'(\\x22|\")+$')


def clean_ext(name: str) -> str:
    name = BAD_SUFFIX_RE.sub('', name)
    return name


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def normalize_folder(folder: Path):
    img_dir = folder / 'images'
    if not img_dir.exists():
        return

    files = [p for p in sorted(img_dir.iterdir()) if p.is_file()]
    if not files:
        return

    seen_hash = {}
    normalized = []
    idx = 1
    removed = []

    for f in files:
        cleaned_name = clean_ext(f.name)
        tmp = f
        if cleaned_name != f.name:
            target = f.with_name(cleaned_name)
            if not target.exists():
                f.rename(target)
                tmp = target
            else:
                f.unlink()
                removed.append(f.name)
                continue

        digest = sha256(tmp)
        if digest in seen_hash:
            removed.append(tmp.name)
            tmp.unlink()
            continue

        ext = tmp.suffix.lower() or '.bin'
        target = img_dir / f'{idx:03d}{ext}'
        idx += 1
        if tmp != target:
            if target.exists():
                target.unlink()
            tmp.rename(target)
        seen_hash[digest] = target.name
        normalized.append(target)

    images_json = folder / 'images.json'
    old = []
    if images_json.exists():
        try:
            old = json.loads(images_json.read_text())
        except Exception:
            old = []

    new_entries = []
    old_urls = []
    for item in old:
        if isinstance(item, dict):
            url = str(item.get('url', ''))
            url = url.replace('\\x22', '').replace('"', '').strip()
            old_urls.append(url)
    for i, f in enumerate(normalized):
        url = old_urls[i] if i < len(old_urls) else ''
        new_entries.append({'url': url, 'path': str(f)})
    images_json.write_text(json.dumps(new_entries, ensure_ascii=False, indent=2), encoding='utf-8')

    assets_md = folder / 'assets.md'
    if assets_md.exists():
        txt = assets_md.read_text(encoding='utf-8')
        txt = re.sub(r'- duplicate handling: .*', f'- duplicate handling: removed {len(removed)} duplicate/dirty files', txt)
        assets_md.write_text(txt, encoding='utf-8')

    print(folder.name, 'kept', len(normalized), 'removed', len(removed))


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', nargs='?', help='Optional folder path or folder name under materials/wechat')
    args = ap.parse_args()

    for folder in iter_targets(args.folder):
        normalize_folder(folder)

if __name__ == '__main__':
    main()
