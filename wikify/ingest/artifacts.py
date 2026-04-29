import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wikify.ingest.documents import NormalizedDocument
from wikify.sync import INGEST_QUEUE_SCHEMA_VERSION, SOURCE_ITEMS_SCHEMA_VERSION


INGEST_RUN_SCHEMA_VERSION = 'wikify.ingest-run.v1'
INGEST_ITEM_SCHEMA_VERSION = 'wikify.ingest-item.v1'


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


def workspace_root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def ingest_run_path(base: Path | str, run_id: str) -> Path:
    return workspace_root(base) / '.wikify' / 'ingest' / 'runs' / f'{run_id}.json'


def ingest_item_path(base: Path | str, item_id: str) -> Path:
    return workspace_root(base) / '.wikify' / 'ingest' / 'items' / f'{item_id}.json'


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


def source_item_from_normalized(document: NormalizedDocument, status: str) -> dict:
    relative_path = document.raw_paths.get('document')
    absolute_path = document.raw_paths.get('document_path') or relative_path
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
        'source_id': document.source_id,
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
