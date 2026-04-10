#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
SOURCES_INDEX = BASE / 'sources' / 'index.md'
OBSIDIAN_SOURCES_INDEX = BASE / 'sources' / 'sources-index.md'
PARSED_DIR = BASE / 'articles' / 'parsed'
SORTED_DIR = BASE / 'sorted'

HEADER = [
    '# 文章来源索引',
    '',
    '| 标题 | 来源账号 | 日期 | URL | 标签 | 相关主题 | 类型 | 完整性 | 置信度 | 复用级别 | 跟进需求 | 状态 |',
    '|------|----------|------|-----|------|----------|------|--------|--------|----------|----------|------|',
]


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.exists() else ''


def write_text(path: Path, text: str):
    path.write_text(text, encoding='utf-8')


def parse_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.startswith('|'):
            continue
        if line.startswith('| 标题 ') or line.startswith('|------'):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) != 12:
            continue
        rows.append({
            'title': cells[0],
            'source_account': cells[1],
            'date': cells[2],
            'url': cells[3],
            'tags': cells[4],
            'topics': cells[5],
            'type': cells[6],
            'completeness': cells[7],
            'confidence': cells[8],
            'reuse_level': cells[9],
            'followup_needed': cells[10],
            'status': cells[11],
        })
    return rows


def normalize_status(status: str) -> str:
    mapping = {
        'captured': 'captured',
        'parsed': 'parsed',
        'briefed': 'briefed',
        'linked': 'linked',
        'integrated': 'integrated',
        'digested': 'digested',
        'needs_review': 'needs_review',
        'failed': 'failed',
    }
    return mapping.get(status, status or 'briefed')


def infer_note_title(path: Path) -> str:
    text = read_text(path)
    for line in text.splitlines():
        if line.startswith('# 标题：'):
            return line.replace('# 标题：', '', 1).strip()
    return path.stem


def build_obsidian_source_index(rows: list[dict], stats: dict) -> str:
    lines = [
        '---',
        'type: source-index',
        'scope: sources',
        'tags:',
        '  - sources',
        '  - obsidian',
        '  - moc',
        '---',
        '',
        '# Sources Index',
        '',
        '## 用途',
        '- 这是 article/source notes 的导航页。',
        '- CLI 继续消费结构化结果，本页主要给 Obsidian 查看与组织。',
        '',
        '## 最新来源',
    ]
    parsed_notes = sorted(
        [path for path in PARSED_DIR.glob('*.md') if path.is_file() and not path.name.startswith('_')],
        key=lambda p: p.name,
        reverse=True,
    )
    if parsed_notes:
        for path in parsed_notes[:20]:
            title = infer_note_title(path)
            lines.append(f"- [[{path.stem}|{title}]]")
    else:
        lines.append('- 待补 source notes')
    lines.extend([
        '',
        '## Digests',
    ])
    digest_notes = sorted(
        [path for path in SORTED_DIR.glob('*-digest.md') if path.is_file()],
        key=lambda p: p.name,
        reverse=True,
    )
    if digest_notes:
        for path in digest_notes[:20]:
            lines.append(f'- [[{path.stem}]]')
    else:
        lines.append('- 待补 digest notes')
    lines.extend([
        '',
        '## Topic Links',
    ])
    topic_refs = []
    for row in rows:
        topics = [item.strip() for item in row.get('topics', '').split(',') if item.strip() and item.strip() != '-']
        for topic in topics:
            stem = Path(topic).stem
            if stem not in topic_refs:
                topic_refs.append(stem)
    if topic_refs:
        for stem in sorted(topic_refs):
            lines.append(f'- [[{stem}]]')
    else:
        lines.append('- [[topics-moc]]')
    lines.extend([
        '',
        '## 状态统计',
        f"- 总条目: {len(rows)}",
        f"- briefed: {stats['briefed']}",
        f"- integrated: {stats['integrated']}",
        f"- digested: {stats['digested']}",
        f"- needs_review: {stats['needs_review']}",
    ])
    return '\n'.join(lines) + '\n'


def build_stats(rows: list[dict]) -> dict:
    stats = {k: 0 for k in ['captured', 'parsed', 'briefed', 'linked', 'integrated', 'digested', 'needs_review', 'failed']}
    for row in rows:
        key = normalize_status(row.get('status', 'briefed'))
        if key in stats:
            stats[key] += 1
    return stats


def refresh_obsidian_source_index() -> Path:
    rows = parse_rows(read_text(SOURCES_INDEX))
    stats = build_stats(rows)
    write_text(OBSIDIAN_SOURCES_INDEX, build_obsidian_source_index(rows, stats))
    return OBSIDIAN_SOURCES_INDEX


def update_entry(entry: dict):
    rows = parse_rows(read_text(SOURCES_INDEX))
    url = entry['url']
    replaced = False
    for idx, row in enumerate(rows):
        if row['url'] == url:
            rows[idx] = entry
            replaced = True
            break
    if not replaced:
        rows.append(entry)

    rows.sort(key=lambda row: (row['date'], row['title']), reverse=True)
    stats = build_stats(rows)

    lines = HEADER[:]
    for row in rows:
        lines.append(
            f"| {row['title']} | {row['source_account']} | {row['date']} | {row['url']} | "
            f"{row['tags']} | {row['topics']} | {row['type']} | {row['completeness']} | "
            f"{row['confidence']} | {row['reuse_level']} | {row['followup_needed']} | {row['status']} |"
        )
    lines.extend([
        '',
        '## 统计',
        '',
        f"- 总条目: {len(rows)}",
        f"- captured: {stats['captured']}",
        f"- parsed: {stats['parsed']}",
        f"- briefed: {stats['briefed']}",
        f"- linked: {stats['linked']}",
        f"- integrated: {stats['integrated']}",
        f"- digested: {stats['digested']}",
        f"- needs_review: {stats['needs_review']}",
        f"- failed: {stats['failed']}",
    ])
    write_text(SOURCES_INDEX, '\n'.join(lines))
    refresh_obsidian_source_index()


def main():
    parser = argparse.ArgumentParser(description='Update source index with normalized lifecycle status')
    parser.add_argument('--entry', required=True, help='JSON file containing source index entry')
    args = parser.parse_args()
    entry = json.loads(Path(args.entry).read_text(encoding='utf-8'))
    update_entry(entry)
    print(str(SOURCES_INDEX))


if __name__ == '__main__':
    main()
