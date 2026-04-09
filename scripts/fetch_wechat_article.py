#!/usr/bin/env python3
import argparse, html, json, os, re, subprocess, sys, urllib.request, urllib.parse
from pathlib import Path

FIELD_RE = re.compile(r"(nick_name|title|create_time|link|source_url|cdn_url|content_noencode): JsDecode\('((?:\\.|[^'])*)'\)")
GLOBAL_IMG_RE = re.compile(r'https?://mmbiz\.qpic\.cn/[^\'"\s)]+')
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent / 'materials' / 'wechat'


def decode_jsdecode(s: str) -> str:
    out = s
    replacements = {
        r'\\x5c': '\\',
        r'\\x0d': '\r',
        r'\\x22': '"',
        r'\\x26': '&',
        r"\\x27": "'",
        r'\\x3c': '<',
        r'\\x3e': '>',
        r'\\x0a': '\n',
        r'\\x09': '\t',
    }
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


def run(cmd: str, timeout: int = 45) -> str:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f'command timed out after {timeout}s: {cmd}') from e
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout)
    return p.stdout


def fetch_html(url: str) -> str:
    cmd = f"agent-browser open '{url}' && agent-browser get html body && agent-browser close"
    return run(cmd, timeout=90)


def fetch_text(url: str) -> str:
    cmd = f"agent-browser open '{url}' && agent-browser get text body && agent-browser close"
    return run(cmd, timeout=90)


def sanitize(name: str) -> str:
    name = html.unescape(name).replace('\\x26#39;', "'")
    name = re.sub(r'[\\/:*?"<>|]+', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:120] if name else 'untitled'


def download(url: str, path: Path):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    path.write_bytes(data)


def clean_url(url: str) -> str:
    url = html.unescape(url)
    url = url.replace('\\x26amp;', '&').replace('&amp;', '&')
    url = url.replace('\\x22', '').replace('"', '')
    return url.strip('\\"\' ')


def ext_from_url(url: str) -> str:
    url = clean_url(url)
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    wx = qs.get('wx_fmt', [''])[0]
    if wx:
        return '.' + wx
    suffix = Path(parsed.path).suffix
    return suffix or '.bin'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--base-dir', default=str(DEFAULT_BASE_DIR))
    args = ap.parse_args()

    raw_html = fetch_html(args.url)
    raw_text = fetch_text(args.url)

    field_values = {}
    for k, v in FIELD_RE.findall(raw_html):
        field_values.setdefault(k, []).append(decode_jsdecode(v))

    def pick(key: str, default: str = '') -> str:
        vals = [v for v in field_values.get(key, []) if v]
        if not vals:
            return default
        if key == 'title':
            preferred = [v for v in vals if '微信公众平台' not in v and len(v) >= 8]
            if preferred:
                return preferred[0]
            vals.sort(key=lambda s: (len(s), s.count('：'), s.count('！')), reverse=True)
        elif key == 'content_noencode':
            vals.sort(key=len, reverse=True)
        return vals[0]

    clean_text = ANSI_RE.sub('', raw_text)
    text_lines = []
    for line in clean_text.splitlines():
        line = line.strip()
        if not line or line == '---TEXT---' or line == '微信公众平台':
            continue
        if line.startswith('https://mp.weixin.qq.com/'):
            continue
        text_lines.append(line)
    text_title = text_lines[0] if text_lines else ''
    title = pick('title', 'untitled')
    if text_title and '微信公众平台' not in text_title and len(text_title) > len(title):
        title = text_title
    title = html.unescape(title).replace('\\x26#39;', "'")
    create_time = pick('create_time', '')
    slug = sanitize(title)
    folder = Path(args.base_dir) / slug
    img_dir = folder / 'images'
    folder.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    content_html = html.unescape(pick('content_noencode', ''))
    image_urls = []
    for u in GLOBAL_IMG_RE.findall(raw_html):
        u = clean_url(u)
        if u not in image_urls:
            image_urls.append(u)
    cdn_url = clean_url(pick('cdn_url')) if pick('cdn_url') else ''
    if cdn_url and cdn_url not in image_urls:
        image_urls.insert(0, cdn_url)

    meta = {
        'url': args.url,
        'title': title,
        'source_account': pick('nick_name', ''),
        'create_time': create_time,
        'link': pick('link', ''),
        'source_url': pick('source_url', ''),
        'cdn_url': cdn_url or '',
        'image_count': len(image_urls),
    }
    (folder / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'page.html').write_text(raw_html, encoding='utf-8')
    (folder / 'content.html').write_text(content_html, encoding='utf-8')
    (folder / 'text.txt').write_text(raw_text, encoding='utf-8')

    downloaded = []
    for i, u in enumerate(image_urls, 1):
        try:
            u = clean_url(u)
            ext = ext_from_url(u)
            p = img_dir / f'{i:03d}{ext}'
            download(u, p)
            downloaded.append({'url': u, 'path': str(p)})
        except Exception as e:
            downloaded.append({'url': u, 'error': str(e)})

    (folder / 'images.json').write_text(json.dumps(downloaded, ensure_ascii=False, indent=2), encoding='utf-8')
    print(str(folder))
    print(json.dumps({'title': title, 'images': len(image_urls)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
