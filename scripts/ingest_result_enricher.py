#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SORTED = BASE / 'sorted'
REVIEW_QUEUE = SORTED / 'review-queue.json'
INGEST_FAILURES = SORTED / 'ingest-failures.json'

CHROME_NOISE_MARKERS = [
    'You signed in with another tab or window',
    'You signed out in another tab or window',
    'You switched accounts on another tab or window',
    'Reload to refresh your session',
    'Back to GitHub',
    'View pricing',
    'Start using our',
    'Instantly share code, notes, and snippets',
]


def read_json(path: Path):
    if not path.exists():
        return [] if path.name.endswith('.json') else {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def read_text(path_str: str) -> str:
    path = Path(path_str)
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8')


def assess_extraction_quality(parsed_text: str) -> tuple[str, list[str]]:
    reasons = []
    if not parsed_text.strip():
        return 'low', ['parsed file is empty']

    if any(marker in parsed_text for marker in CHROME_NOISE_MARKERS):
        reasons.append('chrome_noise_detected')

    title_line = next((line for line in parsed_text.splitlines() if line.startswith('# 标题：')), '')
    if title_line.endswith('llm-wiki') or '待补' in title_line:
        reasons.append('weak_title_metadata')

    extracted_quotes = parsed_text.count('> ')
    if extracted_quotes < 1:
        reasons.append('missing_quotes')

    if '## 原文结构' not in parsed_text or '## 关键事实 / 证据' not in parsed_text:
        reasons.append('missing_core_sections')

    if 'chrome_noise_detected' in reasons:
        return 'low', reasons
    if len(reasons) >= 2:
        return 'medium', reasons
    return 'high', reasons


def assess_routing_quality(topic_files: list[str], updated_topics: list[dict]) -> tuple[str, list[str]]:
    reasons = []
    if not topic_files:
        reasons.append('no_topics_detected')
        return 'low', reasons
    if topic_files and not updated_topics:
        reasons.append('topic_detected_but_not_updated')
        return 'medium', reasons
    if updated_topics and all((item.get('status') == 'no_change') for item in updated_topics if isinstance(item, dict)):
        reasons.append('topics_unchanged')
        return 'medium', reasons
    return 'high', reasons


def derive_lifecycle_status(payload: dict, extraction_quality: str, routing_quality: str) -> str:
    files = payload.get('files') or {}
    has_raw = bool(files.get('raw'))
    has_parsed = bool(files.get('parsed'))
    has_brief = bool(files.get('brief'))
    has_topic = bool(payload.get('updated_topics'))
    has_digest = bool(payload.get('generated_digests'))

    if extraction_quality == 'low':
        return 'needs_review'
    if has_digest:
        return 'digested'
    if has_topic and routing_quality == 'high':
        return 'integrated'
    if has_topic:
        return 'linked'
    if has_brief:
        return 'briefed'
    if has_parsed:
        return 'parsed'
    if has_raw:
        return 'captured'
    return 'failed'


def update_review_queue(payload: dict, quality: dict, lifecycle_status: str):
    if lifecycle_status not in {'needs_review', 'failed'} and not quality.get('review_required'):
        return
    queue = read_json(REVIEW_QUEUE)
    item = {
        'url': payload.get('url'),
        'title': payload.get('title'),
        'status': lifecycle_status,
        'source_type': payload.get('source_type'),
        'quality': quality,
        'files': payload.get('files') or {},
    }
    queue = [q for q in queue if q.get('url') != item['url']]
    queue.append(item)
    write_json(REVIEW_QUEUE, queue)


def main():
    parser = argparse.ArgumentParser(description='Enrich ingest payload with productized status and quality model')
    parser.add_argument('--payload', required=True, help='JSON payload file path')
    args = parser.parse_args()

    payload_path = Path(args.payload)
    payload = json.loads(payload_path.read_text(encoding='utf-8'))
    parsed_path = ((payload.get('files') or {}).get('parsed') or '').strip()
    parsed_text = read_text(parsed_path)

    extraction_quality, extraction_reasons = assess_extraction_quality(parsed_text)
    topic_files = []
    topics_value = payload.get('topics') or payload.get('related_topics') or []
    if isinstance(topics_value, str):
        topic_files = [t.strip() for t in topics_value.split(',') if t.strip().endswith('.md')]
    elif isinstance(topics_value, list):
        topic_files = [t for t in topics_value if isinstance(t, str) and t.endswith('.md')]

    updated_topics = payload.get('updated_topics') or []
    routing_quality, routing_reasons = assess_routing_quality(topic_files, updated_topics)
    review_required = extraction_quality != 'high' or routing_quality == 'low'

    lifecycle_status = derive_lifecycle_status(payload, extraction_quality, routing_quality)

    payload['quality'] = {
        'extraction': extraction_quality,
        'routing': routing_quality,
        'review_required': review_required,
        'reasons': {
            'extraction': extraction_reasons,
            'routing': routing_reasons,
        },
    }
    payload['routing'] = {
        'topics_detected': topic_files,
        'updated_topics': updated_topics,
        'primary_topic': topic_files[0] if topic_files else None,
        'secondary_topics': topic_files[1:] if len(topic_files) > 1 else [],
    }

    payload['next_actions'] = []
    if review_required:
        payload['next_actions'].append('review_required')
    if lifecycle_status in {'linked', 'integrated'} and not payload.get('generated_digests'):
        payload['next_actions'].append('digest_optional')
    payload['lifecycle_status'] = lifecycle_status

    update_review_queue(payload, payload['quality'], lifecycle_status)

    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == '__main__':
    main()
