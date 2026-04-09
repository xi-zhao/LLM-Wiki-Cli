#!/usr/bin/env python3
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TOPICS = BASE / 'topics'
TIMELINES = BASE / 'timelines'
PARSED = BASE / 'articles' / 'parsed'
SORTED = BASE / 'sorted'
INDEX = BASE / 'index.md'
SCHEMA = BASE / 'WIKI_SCHEMA.md'
SOURCES = BASE / 'sources' / 'index.md'

summary = {
    'has_schema': SCHEMA.exists(),
    'has_index': INDEX.exists(),
    'topic_files': 0,
    'timeline_files': 0,
    'parsed_files': 0,
    'sorted_files': 0,
    'issues': [],
    'suggestions': [],
}

summary['topic_files'] = len([p for p in TOPICS.glob('*.md') if not p.name.startswith('_')]) if TOPICS.exists() else 0
summary['timeline_files'] = len([p for p in TIMELINES.glob('*.md') if not p.name.startswith('_')]) if TIMELINES.exists() else 0
summary['parsed_files'] = len([p for p in PARSED.glob('*.md') if not p.name.startswith('_')]) if PARSED.exists() else 0
summary['sorted_files'] = len([p for p in SORTED.glob('*.md') if not p.name.startswith('_')]) if SORTED.exists() else 0

if not summary['has_schema']:
    summary['issues'].append('missing WIKI_SCHEMA.md')
if not summary['has_index']:
    summary['issues'].append('missing index.md')
if not SOURCES.exists():
    summary['issues'].append('missing sources/index.md')

# check parsed backlinks to topic files
known_topics = {p.name for p in TOPICS.glob('*.md') if not p.name.startswith('_')}
for parsed in [p for p in PARSED.glob('*.md') if not p.name.startswith('_')]:
    txt = parsed.read_text(encoding='utf-8')
    if '## 关联主题' not in txt:
        summary['issues'].append(f'missing related topics section: {parsed.name}')
        continue
    matches = re.findall(r'-\s+([A-Za-z0-9._-]+\.md)', txt)
    if not matches:
        summary['issues'].append(f'no topic link found in related topics: {parsed.name}')
    for m in matches:
        if m not in known_topics and m not in {'small-models-and-edge-ai.md'}:
            summary['issues'].append(f'unknown topic reference in {parsed.name}: {m}')

if summary['topic_files'] and summary['sorted_files'] == 0:
    summary['suggestions'].append('consider generating topic digests into sorted/')
if summary['parsed_files'] > summary['topic_files'] * 3:
    summary['suggestions'].append('topic coverage may be too thin relative to parsed article volume')
if not any(p.name.endswith('-digest.md') for p in SORTED.glob('*.md')):
    summary['suggestions'].append('no digest outputs detected, query results may not be compounding yet')

out = BASE / 'sorted' / 'wiki-lint-report.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(out)
print(json.dumps(summary, ensure_ascii=False))
