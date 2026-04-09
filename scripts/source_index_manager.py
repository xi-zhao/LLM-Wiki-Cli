#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SOURCES_INDEX = BASE / 'sources' / 'index.md'

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
    stats = {k: 0 for k in ['captured', 'parsed', 'briefed', 'linked', 'integrated', 'digested', 'needs_review', 'failed']}
    for row in rows:
        key = normalize_status(row.get('status', 'briefed'))
        if key in stats:
            stats[key] += 1

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


def main():
    parser = argparse.ArgumentParser(description='Update source index with normalized lifecycle status')
    parser.add_argument('--entry', required=True, help='JSON file containing source index entry')
    args = parser.parse_args()
    entry = json.loads(Path(args.entry).read_text(encoding='utf-8'))
    update_entry(entry)
    print(str(SOURCES_INDEX))


if __name__ == '__main__':
    main()
