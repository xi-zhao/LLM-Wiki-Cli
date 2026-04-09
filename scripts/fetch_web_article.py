#!/usr/bin/env python3

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

META_RE = re.compile(
    r"<meta\s+[^>]*?(?:property|name)\s*=\s*['\"](?P<name>[^'\"]+)['\"][^>]*?"
    r"content\s*=\s*['\"](?P<content>[^'\"]*)['\"][^>]*>",
    re.IGNORECASE,
)
TAG_RE = re.compile(r"<(?P<tag>article|main|body)\b[^>]*>(?P<content>.*?)</(?P=tag)>", re.IGNORECASE | re.DOTALL)
TIME_RE = re.compile(r"<time\b[^>]*?(?:datetime=['\"](?P<datetime>[^'\"]+)['\"])?[^>]*>(?P<text>.*?)</time>", re.IGNORECASE | re.DOTALL)
IMG_RE = re.compile(r"<img\b[^>]*?(?:data-src|src)=['\"](?P<src>[^'\"]+)['\"][^>]*>", re.IGNORECASE)
TITLE_RE = re.compile(r"<title\b[^>]*>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)
DATE_TOKEN_RE = re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})")
DAY_MONTH_YEAR_RE = re.compile(r"\b(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]{3,9})\.?,?\s+(?P<year>\d{4})\b")
MONTH_DAY_YEAR_RE = re.compile(r"\b(?P<month>[A-Za-z]{3,9})\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})\b")
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


class TextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "p",
        "div",
        "section",
        "article",
        "main",
        "li",
        "ul",
        "ol",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "br",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text or "")).strip()


def choose_main_html(html: str) -> str:
    matches = TAG_RE.findall(html)
    if not matches:
        return html
    ranked = sorted(matches, key=lambda item: len(item[1]), reverse=True)
    return ranked[0][1]


def html_to_text(fragment: str) -> str:
    parser = TextExtractor()
    parser.feed(fragment)
    lines = [collapse(line) for line in "".join(parser.parts).splitlines()]
    kept = [line for line in lines if len(line) >= 2]
    return "\n".join(kept)


def meta_map(html: str) -> dict[str, str]:
    result = {}
    for match in META_RE.finditer(html):
        result[match.group("name").strip().lower()] = collapse(match.group("content"))
    return result


def normalize_date(text: str) -> str:
    if not text:
        return ""
    compact = collapse(text)
    match = DATE_TOKEN_RE.search(text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    for pattern in (DAY_MONTH_YEAR_RE, MONTH_DAY_YEAR_RE):
        match = pattern.search(compact)
        if not match:
            continue
        month_name = match.group("month").lower().rstrip(".")
        month = MONTHS.get(month_name)
        if month is None:
            continue
        return f"{int(match.group('year')):04d}-{month:02d}-{int(match.group('day')):02d}"
    return compact[:10]


def extract_title(html: str, metas: dict[str, str]) -> str:
    for key in ("og:title", "twitter:title", "title"):
        value = metas.get(key, "")
        if value:
            return value
    match = TITLE_RE.search(html)
    if match:
        return collapse(match.group("title"))
    return "待补标题"


def extract_source_account(metas: dict[str, str], url: str) -> str:
    for key in ("author", "article:author", "og:site_name", "application-name"):
        value = metas.get(key, "")
        if value:
            return value
    host = urlparse(url).netloc
    return host.replace("www.", "") if host else "待补来源"


def extract_publish_time(html: str, metas: dict[str, str]) -> str:
    for key in (
        "article:published_time",
        "article:modified_time",
        "publishdate",
        "pubdate",
        "date",
        "dc.date",
    ):
        value = metas.get(key, "")
        normalized = normalize_date(value)
        if normalized:
            return normalized
    match = TIME_RE.search(html)
    if match:
        for value in (match.group("datetime"), match.group("text")):
            normalized = normalize_date(value or "")
            if normalized:
                return normalized
    return ""


def extract_images(fragment: str, url: str) -> list[dict]:
    images = []
    seen = set()
    for match in IMG_RE.finditer(fragment):
        src = collapse(match.group("src"))
        if not src or src.startswith("data:"):
            continue
        resolved = urljoin(url, src)
        if resolved in seen:
            continue
        seen.add(resolved)
        images.append({"url": resolved})
    return images


def page_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parts:
        stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", parts[-1]).strip("-")
        if stem:
            return stem[:80]
    host = re.sub(r"[^a-zA-Z0-9]+", "-", parsed.netloc).strip("-")
    return host or datetime.now().strftime("%Y%m%d-%H%M%S")


def fetch_url_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        data = resp.read()
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def extract_article_payload_from_html(html: str, url: str) -> dict:
    metas = meta_map(html)
    content_html = choose_main_html(html)
    content_text = html_to_text(content_html)
    title = extract_title(html, metas)
    publish_time = extract_publish_time(html, metas)
    source_account = extract_source_account(metas, url)
    images = extract_images(content_html, url)

    return {
        "page_id": page_id_from_url(url),
        "title": title,
        "source_account": source_account,
        "publish_time": publish_time,
        "url": url,
        "fetch_time": datetime.now().isoformat(),
        "page_html": html,
        "content_html": content_html,
        "content_text": content_text,
        "images": images,
        "completeness": "complete" if len(content_text) >= 400 else "partial",
    }


def build_assets_md(payload: dict) -> str:
    lines = [
        "# Assets",
        "",
        "## Summary",
        f"- total_images: {len(payload['images'])}",
        "",
        "## Article Info",
        f"- Title: {payload['title']}",
        f"- Source: {payload['source_account']}",
        f"- Publish Time: {payload['publish_time'] or '待补'}",
        f"- URL: {payload['url']}",
        "",
        "## Images",
    ]
    if payload["images"]:
        lines.extend(f"- {Path(item['url']).name or item['url']}" for item in payload["images"][:10])
    else:
        lines.append("- no captured images")
    return "\n".join(lines)


def save_payload(payload: dict, base_dir: Path) -> Path:
    page_dir = base_dir / payload["page_id"]
    page_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "title": payload["title"],
        "source_account": payload["source_account"],
        "publish_time": payload["publish_time"],
        "url": payload["url"],
        "fetch_time": payload["fetch_time"],
        "completeness": payload["completeness"],
        "image_count": len(payload["images"]),
        "source_origin": "web-page",
    }

    (page_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (page_dir / "page.html").write_text(payload["page_html"], encoding="utf-8")
    (page_dir / "content.html").write_text(payload["content_html"], encoding="utf-8")
    (page_dir / "text.txt").write_text(payload["content_text"], encoding="utf-8")
    (page_dir / "images.json").write_text(json.dumps(payload["images"], ensure_ascii=False, indent=2), encoding="utf-8")
    (page_dir / "assets.md").write_text(build_assets_md(payload), encoding="utf-8")
    return page_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--base-dir", default="./materials/web")
    args = parser.parse_args()

    html = fetch_url_html(args.url)
    payload = extract_article_payload_from_html(html, args.url)
    page_dir = save_payload(payload, Path(args.base_dir))

    output = {
        "success": True,
        "page_id": payload["page_id"],
        "title": payload["title"],
        "source_account": payload["source_account"],
        "publish_time": payload["publish_time"],
        "completeness": payload["completeness"],
        "content_preview": payload["content_text"][:500],
        "images_count": len(payload["images"]),
        "saved_to": str(page_dir),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise
