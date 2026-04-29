import hashlib
import json
import os
import re
import shlex
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wikify.frontmatter import render_markdown_with_front_matter
from wikify.maintenance.agent_profile import resolve_agent_execution
from wikify.maintenance.bundle_producer import DEFAULT_TIMEOUT_SECONDS
from wikify.object_validation import validate_workspace_objects
from wikify.objects import (
    make_object_index,
    make_wiki_page_object,
    object_document_path,
    object_index_path,
    stable_object_id,
)
from wikify.sync import INGEST_QUEUE_SCHEMA_VERSION, SOURCE_ITEMS_SCHEMA_VERSION, ingest_queue_path, source_items_path
from wikify.workspace import load_workspace


WIKIIZATION_RUN_SCHEMA_VERSION = 'wikify.wikiization-run.v1'
WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION = 'wikify.wikiization-tasks.v1'
WIKIIZATION_REQUEST_SCHEMA_VERSION = 'wikify.wikiization-request.v1'
WIKIIZATION_RESULT_SCHEMA_VERSION = 'wikify.wikiization-result.v1'

MAX_SOURCE_TEXT_CHARS = 12000
MAX_EXCERPT_CHARS = 1200
MAX_CAPTURE_CHARS = 4000


class WikiizeError(ValueError):
    def __init__(self, message: str, code: str = 'wikiize_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _stable_digest(*parts: object) -> str:
    payload = '\0'.join(str(part) for part in parts)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def wiki_pages_dir(base: Path | str) -> Path:
    return _root(base) / 'wiki' / 'pages'


def wikiize_report_path(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'wikiization' / 'last-wikiize.json'


def wikiization_task_queue_path(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'queues' / 'wikiization-tasks.json'


def wikiization_request_dir(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'wikiization' / 'requests'


def wikiization_result_dir(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'wikiization' / 'results'


def _write_json_atomic(path: Path, document: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp_path.replace(path)


def _write_text_atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(text, encoding='utf-8')
    temp_path.replace(path)


def _read_json(path: Path, *, schema_version: str, missing_code: str, invalid_code: str) -> dict:
    if not path.exists():
        raise WikiizeError(f'wikiization input artifact is missing: {path}', code=missing_code, details={'path': str(path)})
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise WikiizeError(
            f'wikiization input artifact is invalid JSON: {path}',
            code=invalid_code,
            details={'path': str(path)},
        ) from exc
    if document.get('schema_version') != schema_version:
        raise WikiizeError(
            f'wikiization input artifact schema is unsupported: {path}',
            code=f'{invalid_code}_schema_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    return document


def _load_source_items(root: Path) -> dict:
    document = _read_json(
        source_items_path(root),
        schema_version=SOURCE_ITEMS_SCHEMA_VERSION,
        missing_code='wikiize_source_items_missing',
        invalid_code='wikiize_source_items_invalid',
    )
    if not isinstance(document.get('items'), dict):
        raise WikiizeError(
            'source item index items field is invalid',
            code='wikiize_source_items_invalid',
            details={'path': str(source_items_path(root))},
        )
    return document


def _load_ingest_queue(root: Path) -> dict:
    document = _read_json(
        ingest_queue_path(root),
        schema_version=INGEST_QUEUE_SCHEMA_VERSION,
        missing_code='wikiize_ingest_queue_missing',
        invalid_code='wikiize_ingest_queue_invalid',
    )
    if not isinstance(document.get('entries'), list):
        raise WikiizeError(
            'ingest queue entries field is invalid',
            code='wikiize_ingest_queue_invalid',
            details={'path': str(ingest_queue_path(root))},
        )
    return document


def _load_task_queue(root: Path) -> dict:
    path = wikiization_task_queue_path(root)
    if not path.exists():
        return {
            'schema_version': WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION,
            'generated_at': _utc_now(),
            'summary': {'task_count': 0, 'by_reason': {}},
            'tasks': [],
        }
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise WikiizeError(
            f'wikiization task queue is invalid JSON: {path}',
            code='wikiization_task_queue_invalid',
            details={'path': str(path)},
        ) from exc
    if document.get('schema_version') != WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION or not isinstance(document.get('tasks'), list):
        raise WikiizeError(
            'wikiization task queue schema is unsupported',
            code='wikiization_task_queue_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    return document


def _summarize_tasks(tasks: list[dict]) -> dict:
    by_reason = {}
    for task in tasks:
        reason = task.get('reason_code') or 'unknown'
        by_reason[reason] = by_reason.get(reason, 0) + 1
    return {'task_count': len(tasks), 'by_reason': dict(sorted(by_reason.items()))}


def _write_task_queue(root: Path, task_queue: dict):
    task_queue['generated_at'] = _utc_now()
    task_queue['summary'] = _summarize_tasks(task_queue.get('tasks', []))
    _write_json_atomic(wikiization_task_queue_path(root), task_queue)


def _select_entries(
    queue: dict,
    *,
    queue_id: str | None = None,
    item_id: str | None = None,
    source_id: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    entries = [
        entry
        for entry in queue.get('entries', [])
        if entry.get('action') == 'wikiize_source_item' and entry.get('status') == 'queued'
    ]
    if queue_id:
        entries = [entry for entry in entries if entry.get('queue_id') == queue_id]
    if item_id:
        entries = [entry for entry in entries if entry.get('item_id') == item_id]
    if source_id:
        entries = [entry for entry in entries if entry.get('source_id') == source_id]
    entries.sort(key=lambda entry: (entry.get('source_id') or '', entry.get('item_id') or '', entry.get('queue_id') or ''))
    if limit is not None:
        if limit < 0:
            raise WikiizeError('limit must be non-negative', code='wikiize_limit_invalid', details={'limit': limit})
        entries = entries[:limit]
    return entries


def _slug(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or 'page'


def _planned_identity(root: Path, entry: dict, item: dict | None) -> dict:
    existing = _existing_object_for_item(root, entry.get('item_id'))
    object_id = existing.get('id') if existing else stable_object_id('wiki_page', entry.get('item_id') or entry.get('queue_id') or 'source-item')
    title = _title_from_item(item) if item else entry.get('item_id') or object_id
    body_path = existing.get('body_path') if existing and existing.get('body_path') else f'wiki/pages/{object_id}-{_slug(title)[:48]}.md'
    object_path = object_document_path(root, 'wiki_page', object_id).relative_to(root).as_posix()
    return {
        'object_id': object_id,
        'body_path': body_path,
        'object_path': object_path,
        'title': title,
    }


def _title_from_item(item: dict | None) -> str:
    if not item:
        return 'Source Item'
    relative_path = item.get('relative_path')
    locator = item.get('locator') or item.get('path') or item.get('item_id') or 'source-item'
    return Path(relative_path or locator).stem or item.get('item_id') or 'Source Item'


def _source_ref(item: dict, confidence: float = 0.86) -> dict:
    ref = {
        'source_id': item.get('source_id'),
        'item_id': item.get('item_id'),
        'locator': item.get('locator'),
        'relative_path': item.get('relative_path'),
        'path': item.get('path'),
        'confidence': float(confidence),
    }
    fingerprint = item.get('fingerprint')
    if isinstance(fingerprint, dict):
        ref['fingerprint'] = fingerprint
    ref['span'] = {'kind': 'item'}
    return {key: value for key, value in ref.items() if value is not None}


def _is_remote_item(item: dict) -> bool:
    fingerprint = item.get('fingerprint') or {}
    return item.get('item_type') == 'remote' or fingerprint.get('kind') == 'remote'


def _is_processable_local_file(item: dict) -> bool:
    return item.get('item_type') == 'file' and bool(item.get('path')) and item.get('status') in {'new', 'changed'}


def _read_source_text(item: dict) -> str:
    path_value = item.get('path')
    if not path_value:
        raise WikiizeError('source item has no readable path', code='source_text_unreadable')
    path = Path(path_value).expanduser()
    try:
        return path.read_text(encoding='utf-8')[:MAX_SOURCE_TEXT_CHARS]
    except UnicodeDecodeError as exc:
        raise WikiizeError('source item is not valid UTF-8 text', code='source_text_unreadable', details={'path': str(path)}) from exc
    except OSError as exc:
        raise WikiizeError('source item could not be read', code='source_text_unreadable', details={'path': str(path)}) from exc


def _strip_front_matter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == '---':
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == '---':
                return '\n'.join(lines[index + 1:])
    return text


def _title_from_text(text: str, fallback: str) -> str:
    for line in _strip_front_matter(text).splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            title = stripped[2:].strip()
            if title:
                return title
    return fallback


def _meaningful_lines(text: str) -> list[str]:
    lines = []
    for line in _strip_front_matter(text).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        lines.append(stripped)
    return lines


def _summary_from_text(text: str, fallback_title: str) -> str:
    lines = _meaningful_lines(text)
    if not lines:
        return f'Imported source item for {fallback_title}.'
    summary = ' '.join(lines[:2])
    return summary[:280]


def _excerpt_from_text(text: str) -> str:
    lines = _meaningful_lines(text)
    excerpt = '\n'.join(lines)[:MAX_EXCERPT_CHARS].strip()
    return excerpt or 'No excerptable text was found.'


def _deterministic_draft(item: dict) -> dict:
    text = _read_source_text(item)
    fallback_title = _title_from_item(item)
    title = _title_from_text(text, fallback_title)
    summary = _summary_from_text(text, title)
    excerpt = _excerpt_from_text(text)
    source_ref = _source_ref(item)
    body = '\n'.join([
        f'# {title}',
        '',
        '## Summary',
        '',
        summary,
        '',
        '## Source References',
        '',
        f'- Source `{item.get("source_id")}` item `{item.get("item_id")}`.',
        '',
        '## Excerpt',
        '',
        excerpt,
        '',
    ])
    return {
        'title': title,
        'summary': summary,
        'body': body,
        'source_refs': [source_ref],
        'outbound_links': [],
        'confidence': 0.86,
        'review_status': 'generated',
        'generator': 'deterministic',
    }


def _existing_object_for_item(root: Path, item_id: str | None) -> dict | None:
    if not item_id:
        return None
    directory = root / 'artifacts' / 'objects' / 'wiki_pages'
    if not directory.exists():
        return None
    for path in sorted(directory.glob('*.json')):
        try:
            document = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            continue
        for source_ref in document.get('source_refs') or []:
            if isinstance(source_ref, dict) and source_ref.get('item_id') == item_id:
                document['_object_path'] = path
                return document
    return None


def _load_all_object_documents(root: Path) -> list[dict]:
    directory = root / 'artifacts' / 'objects'
    objects = []
    if not directory.exists():
        return objects
    for path in sorted(directory.rglob('*.json')):
        if path.name in {'object-index.json', 'validation.json'}:
            continue
        try:
            document = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            continue
        if isinstance(document, dict):
            objects.append(document)
    return objects


def _write_object_index(root: Path):
    objects = _load_all_object_documents(root)
    _write_json_atomic(object_index_path(root), make_object_index(root, objects))


def _validate_generated_objects(root: Path) -> dict:
    path = root / 'artifacts' / 'objects' / 'wiki_pages'
    result = validate_workspace_objects(root, path=path, strict=True, write_report=True)
    if result.get('summary', {}).get('error_count', 0):
        raise WikiizeError(
            'generated wiki page object validation failed',
            code='wikiize_validation_failed',
            details={'validation': result},
        )
    return result


def _object_from_draft(root: Path, entry: dict, item: dict, draft: dict, identity: dict, now: str, rendered_markdown: str) -> dict:
    existing = _existing_object_for_item(root, item.get('item_id'))
    created_at = existing.get('created_at') if existing else now
    obj = make_wiki_page_object(
        object_id=identity['object_id'],
        title=draft['title'],
        summary=draft['summary'],
        body_path=identity['body_path'],
        source_refs=draft['source_refs'],
        outbound_links=draft.get('outbound_links') or [],
        backlinks=[],
        created_at=created_at,
        updated_at=now,
        confidence=float(draft.get('confidence', 0.7)),
        review_status=draft.get('review_status') or 'generated',
        relative_path=identity['body_path'],
    )
    obj['generation'] = {
        'generator': draft.get('generator') or 'deterministic',
        'queue_id': entry.get('queue_id'),
        'source_item_id': item.get('item_id'),
        'source_item_fingerprint': item.get('fingerprint') or {},
        'markdown_sha256': _sha256(rendered_markdown),
        'body_sha256': _sha256(draft.get('body') or ''),
        'generated_at': now,
    }
    return obj


def _front_matter_for_object(obj: dict) -> dict:
    return {
        'schema_version': obj['schema_version'],
        'id': obj['id'],
        'type': obj['type'],
        'title': obj['title'],
        'summary': obj['summary'],
        'body_path': obj['body_path'],
        'source_refs': obj['source_refs'],
        'outbound_links': obj['outbound_links'],
        'backlinks': obj['backlinks'],
        'created_at': obj['created_at'],
        'updated_at': obj['updated_at'],
        'confidence': obj['confidence'],
        'review_status': obj['review_status'],
    }


def _can_overwrite_existing(root: Path, identity: dict, existing: dict | None) -> tuple[bool, str | None]:
    body_path = root / identity['body_path']
    if not body_path.exists():
        return True, None
    generation = (existing or {}).get('generation') or {}
    expected_hash = generation.get('markdown_sha256')
    if expected_hash and expected_hash == _sha256(body_path.read_text(encoding='utf-8')):
        return True, None
    return False, 'generated_page_drifted'


def _task_id(entry: dict, reason_code: str) -> str:
    return f'wikiize-task-{_stable_digest(entry.get("queue_id"), entry.get("item_id"), reason_code)[:16]}'


def _upsert_task(task_queue: dict, task: dict):
    tasks = [existing for existing in task_queue.get('tasks', []) if existing.get('id') != task.get('id')]
    tasks.append(task)
    tasks.sort(key=lambda value: value.get('id') or '')
    task_queue['tasks'] = tasks


def _make_task(root: Path, entry: dict, item: dict | None, identity: dict, reason_code: str, now: str, message: str | None = None) -> dict:
    task_id = _task_id(entry, reason_code)
    source_id = entry.get('source_id') or (item or {}).get('source_id')
    item_id = entry.get('item_id') or (item or {}).get('item_id')
    return {
        'id': task_id,
        'schema_version': WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION,
        'created_at': now,
        'updated_at': now,
        'source_id': source_id,
        'item_id': item_id,
        'queue_id': entry.get('queue_id'),
        'target_paths': {
            'body_path': identity.get('body_path'),
            'object_path': identity.get('object_path'),
        },
        'evidence': {
            'queue_entry': dict(entry),
            'source_item': dict(item or {}),
        },
        'reason_code': reason_code,
        'message': message or reason_code,
        'agent_instructions': [
            'Inspect the source item and target paths.',
            'Prepare source-backed wiki content only when the evidence supports it.',
            'Preserve source_refs with source_id and item_id in any proposed page.',
            'Do not overwrite user-edited content without an explicit patch/apply flow.',
        ],
        'acceptance_checks': [
            'The generated wiki page preserves source_refs for the source item.',
            'The target path remains inside wiki/pages/ and artifacts/objects/wiki_pages/.',
            'Strict object validation passes before the queue entry is completed.',
        ],
        'requires_user': False,
        'status': 'queued',
    }


def _mark_queue_entry(queue: dict, queue_id: str, updates: dict):
    for entry in queue.get('entries', []):
        if entry.get('queue_id') == queue_id:
            entry.update(updates)
            return


def _request_path(root: Path, queue_id: str) -> Path:
    return wikiization_request_dir(root) / f'{queue_id}.json'


def _result_path(root: Path, queue_id: str) -> Path:
    return wikiization_result_dir(root) / f'{queue_id}.json'


def _build_agent_request(root: Path, entry: dict, item: dict, identity: dict, source_refs: list[dict]) -> dict:
    queue_id = entry.get('queue_id')
    source_text = None
    if _is_processable_local_file(item):
        try:
            source_text = _read_source_text(item)
        except WikiizeError:
            source_text = None
    return {
        'schema_version': WIKIIZATION_REQUEST_SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'base': str(root),
        'queue_id': queue_id,
        'source_id': item.get('source_id'),
        'item_id': item.get('item_id'),
        'queue_entry': dict(entry),
        'source_item': dict(item),
        'source_text': source_text,
        'source_refs': source_refs,
        'target_paths': {
            'body_path': identity['body_path'],
            'object_path': identity['object_path'],
        },
        'request_path': _request_path(root, queue_id).relative_to(root).as_posix(),
        'suggested_result_path': _result_path(root, queue_id).relative_to(root).as_posix(),
        'target_object_schema': 'wikify.wiki-page.v1',
        'write_scope': [identity['body_path'], identity['object_path']],
        'acceptance_checks': [
            'Return wikify.wikiization-result.v1 JSON.',
            'Preserve request.source_refs or stricter source refs.',
            'Do not write content files directly.',
            'Keep generated claims tied to the provided source item facts.',
        ],
        'validation': {
            'strict_object_validation_required': True,
            'wikify_finalizes_writes': True,
        },
    }


def _command_args(agent_command: str | list[str]) -> list[str]:
    args = shlex.split(agent_command) if isinstance(agent_command, str) else list(agent_command)
    if not args:
        raise WikiizeError('agent command is empty', code='wikiize_agent_command_invalid')
    return args


def _truncate(text: str) -> str:
    if len(text) <= MAX_CAPTURE_CHARS:
        return text
    return text[:MAX_CAPTURE_CHARS] + '...'


def _run_agent(root: Path, request: dict, agent_command: str | list[str], timeout_seconds: float) -> dict:
    request_file = root / request['request_path']
    result_file = root / request['suggested_result_path']
    _write_json_atomic(request_file, request)
    args = _command_args(agent_command)
    env = dict(os.environ)
    env.update({
        'WIKIFY_BASE': str(root),
        'WIKIFY_WIKIIZATION_REQUEST': str(request_file),
        'WIKIFY_WIKIIZATION_RESULT': str(result_file),
    })
    try:
        completed = subprocess.run(
            args,
            cwd=root,
            env=env,
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WikiizeError(
            f'agent command timed out after {timeout_seconds} seconds',
            code='wikiize_agent_timeout',
            details={'timeout_seconds': timeout_seconds},
        ) from exc
    if completed.returncode != 0:
        raise WikiizeError(
            f'agent command failed with exit code {completed.returncode}',
            code='wikiize_agent_command_failed',
            details={'returncode': completed.returncode, 'stdout': _truncate(completed.stdout), 'stderr': _truncate(completed.stderr)},
        )
    stdout = completed.stdout.strip()
    if stdout:
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise WikiizeError(
                'agent command stdout is not valid wikiization JSON',
                code='wikiize_agent_output_invalid',
                details={'stdout': _truncate(stdout)},
            ) from exc
        _write_json_atomic(result_file, result)
        return result
    if not result_file.exists():
        raise WikiizeError(
            'agent command produced no stdout result and did not write the suggested result path',
            code='wikiize_agent_result_missing',
            details={'suggested_result_path': str(result_file)},
        )
    try:
        return json.loads(result_file.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise WikiizeError(
            'agent result file is not valid JSON',
            code='wikiize_agent_result_invalid',
            details={'path': str(result_file)},
        ) from exc


def _draft_from_agent_result(result: dict, request: dict) -> dict:
    if result.get('schema_version') != WIKIIZATION_RESULT_SCHEMA_VERSION:
        raise WikiizeError(
            'agent wikiization result schema is unsupported',
            code='wikiize_agent_result_schema_invalid',
            details={'schema_version': result.get('schema_version')},
        )
    if result.get('queue_id') != request.get('queue_id'):
        raise WikiizeError(
            'agent wikiization result queue id does not match request',
            code='wikiize_agent_result_queue_mismatch',
            details={'expected': request.get('queue_id'), 'actual': result.get('queue_id')},
        )
    for field in ('title', 'summary', 'body'):
        if not isinstance(result.get(field), str) or not result.get(field).strip():
            raise WikiizeError(
                f'agent wikiization result is missing {field}',
                code='wikiize_agent_result_invalid',
                details={'field': field},
            )
    confidence = float(result.get('confidence', 0.7))
    if confidence < 0.0 or confidence > 1.0:
        raise WikiizeError('agent confidence is invalid', code='wikiize_agent_result_invalid', details={'field': 'confidence'})
    return {
        'title': result['title'].strip(),
        'summary': result['summary'].strip(),
        'body': result['body'].strip() + '\n',
        'source_refs': result.get('source_refs') if isinstance(result.get('source_refs'), list) else request.get('source_refs', []),
        'outbound_links': result.get('outbound_links') if isinstance(result.get('outbound_links'), list) else [],
        'confidence': confidence,
        'review_status': result.get('review_status') or 'needs_review',
        'generator': 'agent',
    }


def _record_blocked_item(root: Path, queue: dict, task_queue: dict, entry: dict, item: dict | None, identity: dict, reason_code: str, now: str, message: str | None = None) -> dict:
    task = _make_task(root, entry, item, identity, reason_code, now, message=message)
    _upsert_task(task_queue, task)
    _mark_queue_entry(queue, entry.get('queue_id'), {
        'status': 'needs_review',
        'reason_code': reason_code,
        'task_id': task['id'],
        'updated_at': now,
    })
    return {
        'queue_id': entry.get('queue_id'),
        'item_id': entry.get('item_id'),
        'source_id': entry.get('source_id'),
        'outcome': 'needs_review',
        'reason_code': reason_code,
        'task_id': task['id'],
        'paths': {
            'body_path': identity.get('body_path'),
            'object_path': identity.get('object_path'),
            'task_queue': wikiization_task_queue_path(root).relative_to(root).as_posix(),
        },
    }


def _process_entry(root: Path, queue: dict, task_queue: dict, entry: dict, item: dict | None, execution: dict, now: str) -> tuple[dict, dict | None]:
    identity = _planned_identity(root, entry, item)
    if item is None:
        return _record_blocked_item(root, queue, task_queue, entry, item, identity, 'source_item_missing', now), None
    source_refs = [_source_ref(item, confidence=0.72 if _is_remote_item(item) else 0.86)]
    request = None
    result_path = None
    try:
        if execution.get('agent_command'):
            request = _build_agent_request(root, entry, item, identity, source_refs)
            agent_result = _run_agent(root, request, execution['agent_command'], execution['producer_timeout_seconds'])
            result_path = request['suggested_result_path']
            draft = _draft_from_agent_result(agent_result, request)
        elif _is_remote_item(item):
            return _record_blocked_item(root, queue, task_queue, entry, item, identity, 'remote_without_content', now), None
        elif not _is_processable_local_file(item):
            return _record_blocked_item(root, queue, task_queue, entry, item, identity, 'unsupported_source_item', now), None
        else:
            draft = _deterministic_draft(item)
    except WikiizeError as exc:
        reason_code = exc.code if exc.code in {'source_text_unreadable', 'unsupported_source_item'} else 'wikiization_failed'
        return _record_blocked_item(root, queue, task_queue, entry, item, identity, reason_code, now, message=str(exc)), None

    existing = _existing_object_for_item(root, item.get('item_id'))
    can_write, drift_reason = _can_overwrite_existing(root, identity, existing)
    if not can_write:
        return _record_blocked_item(root, queue, task_queue, entry, item, identity, drift_reason or 'generated_page_drifted', now), None

    placeholder = make_wiki_page_object(
        object_id=identity['object_id'],
        title=draft['title'],
        summary=draft['summary'],
        body_path=identity['body_path'],
        source_refs=draft['source_refs'],
        outbound_links=draft.get('outbound_links') or [],
        backlinks=[],
        created_at=(existing or {}).get('created_at') or now,
        updated_at=now,
        confidence=float(draft.get('confidence', 0.7)),
        review_status=draft.get('review_status') or 'generated',
        relative_path=identity['body_path'],
    )
    rendered = render_markdown_with_front_matter(_front_matter_for_object(placeholder), draft['body'])
    obj = _object_from_draft(root, entry, item, draft, identity, now, rendered)
    rendered = render_markdown_with_front_matter(_front_matter_for_object(obj), draft['body'])
    obj['generation']['markdown_sha256'] = _sha256(rendered)

    body_path = root / identity['body_path']
    object_path = root / identity['object_path']
    _write_text_atomic(body_path, rendered)
    _write_json_atomic(object_path, obj)
    _mark_queue_entry(queue, entry.get('queue_id'), {
        'status': 'completed',
        'completed_at': now,
        'updated_at': now,
        'object_ids': [obj['id']],
        'paths': {
            'body_path': identity['body_path'],
            'object_path': identity['object_path'],
        },
        'errors': [],
    })
    item_result = {
        'queue_id': entry.get('queue_id'),
        'item_id': entry.get('item_id'),
        'source_id': entry.get('source_id'),
        'outcome': 'completed',
        'object_ids': [obj['id']],
        'paths': {
            'body_path': identity['body_path'],
            'object_path': identity['object_path'],
        },
    }
    if request:
        item_result['paths']['request_path'] = request['request_path']
    if result_path:
        item_result['paths']['result_path'] = result_path
    return item_result, obj


def _planned_item(root: Path, entry: dict, item: dict | None) -> dict:
    identity = _planned_identity(root, entry, item)
    outcome = 'planned'
    reason = None
    if item is None:
        outcome = 'blocked'
        reason = 'source_item_missing'
    elif _is_remote_item(item):
        outcome = 'blocked'
        reason = 'remote_without_content'
    elif not _is_processable_local_file(item):
        outcome = 'blocked'
        reason = 'unsupported_source_item'
    return {
        'queue_id': entry.get('queue_id'),
        'item_id': entry.get('item_id'),
        'source_id': entry.get('source_id'),
        'outcome': outcome,
        'reason_code': reason,
        'planned_object_ids': [identity['object_id']],
        'planned_paths': {
            'body_path': identity['body_path'],
            'object_path': identity['object_path'],
            'request_path': _request_path(root, entry.get('queue_id')).relative_to(root).as_posix(),
            'result_path': _result_path(root, entry.get('queue_id')).relative_to(root).as_posix(),
        },
    }


def _summary(items: list[dict], *, dry_run: bool) -> dict:
    return {
        'selected_count': len(items),
        'planned_count': sum(1 for item in items if item.get('outcome') == 'planned') if dry_run else 0,
        'completed_count': sum(1 for item in items if item.get('outcome') == 'completed'),
        'needs_review_count': sum(1 for item in items if item.get('outcome') == 'needs_review'),
        'failed_count': sum(1 for item in items if item.get('outcome') == 'failed'),
        'skipped_count': sum(1 for item in items if item.get('outcome') == 'skipped'),
    }


def _status_from_summary(summary: dict, dry_run: bool) -> str:
    if dry_run:
        return 'dry_run'
    if summary.get('failed_count'):
        return 'failed'
    if summary.get('completed_count') and summary.get('needs_review_count'):
        return 'partial'
    if summary.get('completed_count'):
        return 'completed'
    if summary.get('needs_review_count'):
        return 'needs_review'
    return 'completed'


def _artifacts(root: Path) -> dict:
    return {
        'wiki_pages': wiki_pages_dir(root).relative_to(root).as_posix(),
        'wiki_page_objects': 'artifacts/objects/wiki_pages',
        'object_index': object_index_path(root).relative_to(root).as_posix(),
        'validation_report': 'artifacts/objects/validation.json',
        'wikiization_report': wikiize_report_path(root).relative_to(root).as_posix(),
        'wikiization_tasks': wikiization_task_queue_path(root).relative_to(root).as_posix(),
        'wikiization_requests': wikiization_request_dir(root).relative_to(root).as_posix(),
        'wikiization_results': wikiization_result_dir(root).relative_to(root).as_posix(),
        'ingest_queue': ingest_queue_path(root).relative_to(root).as_posix(),
    }


def run_wikiization(
    base: Path | str,
    *,
    dry_run: bool = False,
    queue_id: str | None = None,
    item_id: str | None = None,
    source_id: str | None = None,
    limit: int | None = None,
    agent_command: str | list[str] | None = None,
    agent_profile: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    root = _root(base)
    source_items = _load_source_items(root)
    queue = _load_ingest_queue(root)
    execution = resolve_agent_execution(
        root,
        agent_command=agent_command,
        agent_profile=agent_profile,
        producer_timeout_seconds=timeout_seconds,
    )
    selected = _select_entries(queue, queue_id=queue_id, item_id=item_id, source_id=source_id, limit=limit)
    items_by_id = source_items.get('items') or {}
    now = _utc_now()
    selection = {'queue_id': queue_id, 'item_id': item_id, 'source_id': source_id, 'limit': limit}

    if dry_run:
        planned = [_planned_item(root, entry, items_by_id.get(entry.get('item_id'))) for entry in selected]
        summary = _summary(planned, dry_run=True)
        return {
            'schema_version': WIKIIZATION_RUN_SCHEMA_VERSION,
            'base': str(root),
            'workspace_id': _workspace_id(root),
            'generated_at': now,
            'status': 'dry_run',
            'dry_run': True,
            'selection': selection,
            'summary': summary,
            'artifacts': _artifacts(root),
            'items': planned,
            'validation': None,
            'next_actions': [],
        }

    task_queue = _load_task_queue(root)
    item_results = []
    generated_objects = []
    for entry in selected:
        item_result, obj = _process_entry(root, queue, task_queue, entry, items_by_id.get(entry.get('item_id')), execution, now)
        item_results.append(item_result)
        if obj:
            generated_objects.append(obj)

    validation = None
    if generated_objects:
        _write_object_index(root)
        validation = _validate_generated_objects(root)
    if task_queue.get('tasks'):
        _write_task_queue(root, task_queue)
    queue['generated_at'] = now
    queue['summary'] = _queue_summary(queue.get('entries', []))
    _write_json_atomic(ingest_queue_path(root), queue)

    summary = _summary(item_results, dry_run=False)
    status = _status_from_summary(summary, dry_run=False)
    result = {
        'schema_version': WIKIIZATION_RUN_SCHEMA_VERSION,
        'base': str(root),
        'workspace_id': _workspace_id(root),
        'generated_at': now,
        'status': status,
        'dry_run': False,
        'selection': selection,
        'summary': summary,
        'artifacts': _artifacts(root),
        'items': item_results,
        'validation': validation,
        'next_actions': _next_actions(summary),
    }
    _write_json_atomic(wikiize_report_path(root), result)
    return result


def _workspace_id(root: Path) -> str | None:
    try:
        return load_workspace(root).get('manifest', {}).get('workspace_id')
    except Exception:
        return None


def _queue_summary(entries: list[dict]) -> dict:
    by_item_status = {}
    by_status = {}
    for entry in entries:
        item_status = entry.get('item_status') or 'unknown'
        by_item_status[item_status] = by_item_status.get(item_status, 0) + 1
        status = entry.get('status') or 'unknown'
        by_status[status] = by_status.get(status, 0) + 1
    return {
        'queue_count': len(entries),
        'by_item_status': dict(sorted(by_item_status.items())),
        'by_status': dict(sorted(by_status.items())),
    }


def _next_actions(summary: dict) -> list[str]:
    actions = []
    if summary.get('needs_review_count'):
        actions.append('review_wikiization_tasks')
    if summary.get('failed_count'):
        actions.append('inspect_wikiization_report')
    return actions
