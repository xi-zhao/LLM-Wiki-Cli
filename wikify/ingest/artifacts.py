import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wikify.ingest.documents import NormalizedDocument
from wikify.ingest.errors import IngestError
from wikify.objects import object_document_path, source_item_record_to_object
from wikify.sync import INGEST_QUEUE_SCHEMA_VERSION, SOURCE_ITEMS_SCHEMA_VERSION, ingest_queue_path, source_items_path


INGEST_RUN_SCHEMA_VERSION = 'wikify.ingest-run.v1'
INGEST_ITEM_SCHEMA_VERSION = 'wikify.ingest-item.v1'
TRUSTED_AGENT_INGEST_REQUEST_SCHEMA_VERSION = 'wikify.trusted-agent-ingest-request.v1'


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def stable_digest(*parts) -> str:
    payload = '\0'.join(str(part) for part in parts)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def ingest_item_id(adapter: str, canonical_locator: str) -> str:
    return f'item_{stable_digest(adapter, canonical_locator)[:24]}'


def ingest_queue_id(item_id: str) -> str:
    return f'queue_{stable_digest("wikiize_source_item", item_id)[:24]}'


def ingest_run_id(adapter: str, canonical_locator: str, now: str) -> str:
    return f'run_{stable_digest(adapter, canonical_locator, now)[:24]}'


def unique_ingest_run_id(adapter: str, canonical_locator: str) -> str:
    return f'run_{stable_digest(adapter, canonical_locator, uuid.uuid4().hex)[:24]}'


def workspace_root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def ingest_run_path(base: Path | str, run_id: str) -> Path:
    return workspace_root(base) / '.wikify' / 'ingest' / 'runs' / f'{run_id}.json'


def ingest_item_path(base: Path | str, item_id: str) -> Path:
    return workspace_root(base) / '.wikify' / 'ingest' / 'items' / f'{item_id}.json'


def trusted_agent_request_path(base: Path | str, run_id: str) -> Path:
    return workspace_root(base) / '.wikify' / 'ingest' / 'requests' / f'{run_id}.json'


def raw_item_dir(base: Path | str, adapter: str, item_id: str) -> Path:
    return workspace_root(base) / 'sources' / 'raw' / adapter / item_id


def relative_to_root(base: Path | str, path: Path | str) -> str:
    return Path(path).expanduser().resolve().relative_to(workspace_root(base)).as_posix()


def write_json_atomic(path: Path | str, document: dict):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f'.{target.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp_path.replace(target)


def write_text_atomic(path: Path | str, text: str):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f'.{target.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(text, encoding='utf-8')
    temp_path.replace(target)


def read_json_or_default(path: Path | str, default: dict) -> dict:
    target = Path(path)
    if not target.exists():
        return default
    try:
        document = json.loads(target.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise IngestError(
            'Ingest artifact JSON is invalid',
            code='ingest_artifact_invalid_json',
            details={'path': str(target), 'schema_version': None},
        ) from exc
    if not isinstance(document, dict):
        raise IngestError(
            'Ingest artifact JSON root must be an object',
            code='ingest_artifact_schema_invalid',
            details={'path': str(target), 'schema_version': None},
        )
    return document


def empty_source_items(workspace_id: str, now: str) -> dict:
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'summary': {
            'item_count': 0,
            'item_status_counts': {},
        },
        'items': {},
    }


def empty_ingest_queue(workspace_id: str, now: str) -> dict:
    return {
        'schema_version': INGEST_QUEUE_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'summary': {
            'queue_count': 0,
            'by_item_status': {},
        },
        'entries': [],
    }


def _status_counts(items: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for item in items:
        status = item.get('status')
        if status:
            counts[status] = counts.get(status, 0) + 1
    return counts


def _queue_item_status_counts(entries: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for entry in entries:
        status = entry.get('item_status')
        if status:
            counts[status] = counts.get(status, 0) + 1
    return counts


def _validate_source_items_document(path: Path, document: dict):
    if document.get('schema_version') != SOURCE_ITEMS_SCHEMA_VERSION:
        raise IngestError(
            'Source items artifact schema is invalid',
            code='ingest_artifact_schema_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    if not isinstance(document.get('items'), dict):
        raise IngestError(
            'Source items artifact items field is invalid',
            code='ingest_source_items_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version'), 'field': 'items'},
        )
    for item_id, item in document['items'].items():
        if not isinstance(item, dict):
            raise IngestError(
                'Source items artifact item entry is invalid',
                code='ingest_source_items_invalid',
                details={
                    'path': str(path),
                    'schema_version': document.get('schema_version'),
                    'field': f'items.{item_id}',
                },
            )


def _validate_ingest_queue_document(path: Path, document: dict):
    if document.get('schema_version') != INGEST_QUEUE_SCHEMA_VERSION:
        raise IngestError(
            'Ingest queue artifact schema is invalid',
            code='ingest_artifact_schema_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    if not isinstance(document.get('entries'), list):
        raise IngestError(
            'Ingest queue artifact entries field is invalid',
            code='ingest_queue_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version'), 'field': 'entries'},
        )
    for index, entry in enumerate(document['entries']):
        if not isinstance(entry, dict):
            raise IngestError(
                'Ingest queue artifact entry is invalid',
                code='ingest_queue_invalid',
                details={
                    'path': str(path),
                    'schema_version': document.get('schema_version'),
                    'field': f'entries[{index}]',
                },
            )


def validate_existing_control_artifacts(base: Path | str, workspace_id: str, now: str):
    source_path = source_items_path(base)
    source_items = read_json_or_default(source_path, empty_source_items(workspace_id, now))
    _validate_source_items_document(source_path, source_items)

    queue_path = ingest_queue_path(base)
    queue = read_json_or_default(queue_path, empty_ingest_queue(workspace_id, now))
    _validate_ingest_queue_document(queue_path, queue)


def upsert_source_item(base: Path | str, workspace_id: str, item: dict, now: str) -> dict:
    path = source_items_path(base)
    document = read_json_or_default(path, empty_source_items(workspace_id, now))
    _validate_source_items_document(path, document)
    document['schema_version'] = SOURCE_ITEMS_SCHEMA_VERSION
    document['workspace_id'] = workspace_id
    document['generated_at'] = now
    document['items'][item['item_id']] = dict(item)
    items = list(document['items'].values())
    document['summary'] = {
        'item_count': len(items),
        'item_status_counts': _status_counts(items),
    }
    write_json_atomic(path, document)
    return document


def upsert_ingest_queue_entry(base: Path | str, workspace_id: str, item: dict, now: str) -> dict:
    path = ingest_queue_path(base)
    document = read_json_or_default(path, empty_ingest_queue(workspace_id, now))
    _validate_ingest_queue_document(path, document)
    document['schema_version'] = INGEST_QUEUE_SCHEMA_VERSION
    document['workspace_id'] = workspace_id
    document['generated_at'] = now

    entries = list(document['entries'])
    new_entry = queue_entry_for_source_item(item, now)
    entry = None
    for index, existing in enumerate(entries):
        if existing.get('item_id') == item['item_id']:
            created_at = existing.get('created_at') or now
            entry = dict(existing)
            entry.update(new_entry)
            entry['created_at'] = created_at
            entry['updated_at'] = now
            entries[index] = entry
            break
    if entry is None:
        entry = new_entry
        entries.append(entry)

    entries.sort(key=lambda value: (value.get('source_id') or '', value.get('item_id') or ''))
    document['entries'] = entries
    document['summary'] = {
        'queue_count': len(entries),
        'by_item_status': _queue_item_status_counts(entries),
    }
    write_json_atomic(path, document)
    return entry


def write_source_item_object(base: Path | str, item: dict) -> Path:
    path = object_document_path(base, 'source_item', item['item_id'])
    write_json_atomic(path, source_item_record_to_object(item))
    return path


def source_item_from_normalized(document: NormalizedDocument, status: str) -> dict:
    relative_path = document.raw_paths.get('document')
    absolute_path = document.raw_paths.get('document_path') or relative_path
    source_id = document.source_id or f'ingest:{document.adapter}'
    source_type = 'url' if document.canonical_locator.startswith(('http://', 'https://')) else 'file'
    metadata = dict(document.metadata or {})
    metadata.update({
        'adapter': document.adapter,
        'title': document.title,
        'author': document.author,
        'published_at': document.published_at,
        'captured_at': document.captured_at,
        'raw_paths': dict(document.raw_paths or {}),
        'assets': list(document.assets or []),
        'warnings': list(document.warnings or []),
    })
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'item_id': document.item_id,
        'source_id': source_id,
        'source_type': source_type,
        'item_type': 'file',
        'status': status,
        'locator': document.canonical_locator,
        'locator_key': document.canonical_locator,
        'relative_path': relative_path,
        'path': absolute_path,
        'fingerprint': dict(document.fingerprint or {}),
        'errors': [],
        'discovered_at': document.captured_at,
        'metadata': metadata,
    }


def queue_entry_for_source_item(item: dict, now: str) -> dict:
    return {
        'schema_version': INGEST_QUEUE_SCHEMA_VERSION,
        'queue_id': ingest_queue_id(item['item_id']),
        'action': 'wikiize_source_item',
        'source_id': item.get('source_id'),
        'source_type': item.get('source_type'),
        'item_id': item['item_id'],
        'item_status': item.get('status'),
        'status': 'queued',
        'requires_user': False,
        'evidence': {
            'source_item_id': item['item_id'],
            'source_id': item.get('source_id'),
            'locator': item.get('locator'),
            'relative_path': item.get('relative_path'),
            'fingerprint': item.get('fingerprint'),
        },
        'acceptance_checks': [
            'source item still exists or remains intentionally remote at wikiization time',
            'generated wiki content cites this source item id',
            'no user confirmation is required for queued wikiization',
        ],
        'created_at': now,
        'updated_at': now,
    }
