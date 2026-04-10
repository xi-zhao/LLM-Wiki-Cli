#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

APP_ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
SCRIPTS = APP_ROOT / 'scripts'
WECHAT_SCRIPT = SCRIPTS / 'ingest_wechat_direct_url.py'
WEB_SCRIPT = SCRIPTS / 'ingest_web_direct_url.py'
SORTED = BASE / 'sorted'
TOPICS = BASE / 'topics'
TOPIC_DIGEST_SCRIPT = SCRIPTS / 'generate_topic_digest.py'
TOPIC_MAINTAINER_SCRIPT = SCRIPTS / 'topic_maintainer.py'
RESULT_ENRICHER_SCRIPT = SCRIPTS / 'ingest_result_enricher.py'
WIKI_LINT_SCRIPT = SCRIPTS / 'wiki_lint.py'


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def detect_source_type(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if 'mp.weixin.qq.com' in host:
        return 'wechat'
    return 'web'


def parse_json_output(stdout: str) -> dict:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith('{') and line.endswith('}'):
            try:
                return json.loads(line)
            except Exception:
                continue
    return {}


def infer_topic_candidates(result: dict) -> list[str]:
    candidates = []
    for value in result.get('topics', []) or []:
        if isinstance(value, str) and value.endswith('.md'):
            candidates.append(value)
    related = result.get('related_topics') or []
    for value in related:
        if isinstance(value, str) and value.endswith('.md'):
            candidates.append(value)
    seen = set()
    out = []
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def maintain_topics(topic_files: list[str], parsed_file: str) -> list[dict]:
    updated = []
    for topic in topic_files:
        proc = run(['python3', str(TOPIC_MAINTAINER_SCRIPT), '--topic', topic, '--parsed', parsed_file])
        if proc.returncode == 0:
            payload = parse_json_output(proc.stdout)
            if payload:
                updated.append(payload)
    return updated


def maybe_generate_digests(topic_files: list[str]) -> list[str]:
    created = []
    for topic in topic_files:
        topic_path = TOPICS / topic
        if not topic_path.exists():
            continue
        proc = run(['python3', str(TOPIC_DIGEST_SCRIPT), topic])
        if proc.returncode == 0:
            out = proc.stdout.strip().splitlines()
            if out:
                created.append(out[-1].strip())
    return created


def enrich_payload(payload: dict) -> dict:
    temp_path = SORTED / 'last-ingest-payload.json'
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    proc = run(['python3', str(RESULT_ENRICHER_SCRIPT), '--payload', str(temp_path)])
    if proc.returncode != 0:
        return payload
    return parse_json_output(proc.stdout) or json.loads(temp_path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description='Unified ingest entrypoint for WeChat and web URLs')
    parser.add_argument('url', help='Source URL to ingest')
    parser.add_argument('--with-digests', action='store_true', help='Generate topic digests for detected topics after ingest')
    parser.add_argument('--skip-lint', action='store_true', help='Skip wiki lint after ingest')
    args = parser.parse_args()

    source_type = detect_source_type(args.url)
    script = WECHAT_SCRIPT if source_type == 'wechat' else WEB_SCRIPT

    proc = run(['python3', str(script), args.url])
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout or 'ingest failed\n')
        sys.exit(proc.returncode)

    payload = parse_json_output(proc.stdout)
    payload['source_type'] = source_type

    topic_files = infer_topic_candidates(payload)
    parsed_file = ((payload.get('files') or {}).get('parsed') or '').strip()
    if topic_files and parsed_file:
        payload['updated_topics'] = maintain_topics(topic_files, parsed_file)
    else:
        payload['updated_topics'] = []

    if args.with_digests and topic_files:
        payload['generated_digests'] = maybe_generate_digests(topic_files)
    else:
        payload['generated_digests'] = []

    payload = enrich_payload(payload)

    if not args.skip_lint:
        lint_proc = run(['python3', str(WIKI_LINT_SCRIPT)])
        payload['lint_ok'] = lint_proc.returncode == 0
        payload['lint_output'] = (lint_proc.stdout or '').strip().splitlines()[-1] if (lint_proc.stdout or '').strip() else ''
        if lint_proc.returncode != 0:
            payload['lint_error'] = (lint_proc.stderr or lint_proc.stdout).strip()
    else:
        payload['lint_ok'] = None

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == '__main__':
    main()
