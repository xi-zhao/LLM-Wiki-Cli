#!/usr/bin/env python3
import json
import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
SOURCES = BASE / 'sources' / 'index.md'
TOPICS = BASE / 'topics'
TIMELINES = BASE / 'timelines'
MATERIALS = BASE / 'materials' / 'wechat'
PARSED = BASE / 'articles' / 'parsed'

summary = {
    'source_rows': 0,
    'integrated_rows': 0,
    'topic_files': 0,
    'timeline_files': 0,
    'material_bundles': 0,
    'parsed_notes': 0,
    'issues': [],
}

if SOURCES.exists():
    lines = SOURCES.read_text(encoding='utf-8').splitlines()
    rows = [ln for ln in lines if ln.startswith('| 202')]
    summary['source_rows'] = len(rows)
    summary['integrated_rows'] = sum(1 for r in rows if '| integrated |' in r)
else:
    summary['issues'].append('missing source index')

summary['topic_files'] = len(list(TOPICS.glob('*.md'))) if TOPICS.exists() else 0
summary['timeline_files'] = len(list(TIMELINES.glob('*.md'))) if TIMELINES.exists() else 0
summary['material_bundles'] = len([p for p in MATERIALS.iterdir() if p.is_dir()]) if MATERIALS.exists() else 0
summary['parsed_notes'] = len(list(PARSED.glob('*.md'))) if PARSED.exists() else 0

for parsed in sorted(PARSED.glob('*.md')):
    if parsed.name.startswith('_'):
        continue
    txt = parsed.read_text(encoding='utf-8')
    nonstandard = ('来源形态：transcript-source' in txt or '来源形态：screenshot-source' in txt or '来源形态：mixed-source' in txt or '未建立公众号素材包' in txt)
    if (not nonstandard) and '## 本地素材' not in txt:
        summary['issues'].append(f'missing material backlink: {parsed.name}')
    if (not nonstandard) and '## 推荐引用素材' not in txt:
        summary['issues'].append(f'missing recommended assets: {parsed.name}')

for bundle in sorted(MATERIALS.iterdir()):
    if not bundle.is_dir():
        continue
    for need in ['meta.json', 'page.html', 'content.html', 'text.txt', 'images.json', 'assets.md']:
        if not (bundle / need).exists():
            summary['issues'].append(f'missing {need}: {bundle.name}')

out = BASE / 'sorted' / 'wechat-kb-maintenance-report.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(out)
print(json.dumps(summary, ensure_ascii=False))
