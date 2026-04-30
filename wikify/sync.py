import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wikify.workspace import WorkspaceError, load_workspace, registry_path


SOURCE_ITEMS_SCHEMA_VERSION = 'wikify.source-items.v1'
SYNC_RUN_SCHEMA_VERSION = 'wikify.sync-run.v1'
INGEST_QUEUE_SCHEMA_VERSION = 'wikify.ingest-queue.v1'
DEFAULT_HASH_SIZE_LIMIT_BYTES = 5 * 1024 * 1024

ITEM_STATUSES = ('new', 'changed', 'unchanged', 'missing', 'skipped', 'errored')
QUEUEABLE_STATUSES = {'new', 'changed'}
REMOTE_SOURCE_TYPES = {'url'}
LOCAL_FILE_SOURCE_TYPES = {'file', 'note'}
LOCAL_CONTAINER_SOURCE_TYPES = {'directory', 'repository'}
IGNORED_DIRECTORY_NAMES = frozenset({
    '.git',
    '.wikify',
    '__pycache__',
    'node_modules',
    '.venv',
    'venv',
    'dist',
    'build',
})


class SyncError(ValueError):
    def __init__(self, message: str, code: str = 'sync_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _workspace_root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def source_items_path(base: Path | str) -> Path:
    return _workspace_root(base) / '.wikify' / 'sync' / 'source-items.json'


def sync_report_path(base: Path | str) -> Path:
    return _workspace_root(base) / '.wikify' / 'sync' / 'last-sync.json'


def ingest_queue_path(base: Path | str) -> Path:
    return _workspace_root(base) / '.wikify' / 'queues' / 'ingest-items.json'


def _write_json_atomic(path: Path, document: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp_path.replace(path)


def _read_optional_json(path: Path, *, schema_version: str, code: str) -> dict | None:
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise SyncError(
            f'sync JSON is invalid: {path}',
            code=code,
            details={'path': str(path)},
        ) from exc
    if document.get('schema_version') != schema_version:
        raise SyncError(
            f'sync JSON schema is not supported: {path}',
            code=f'{code}_schema_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    return document


def _load_previous_source_items(root: Path, workspace_id: str) -> dict:
    document = _read_optional_json(
        source_items_path(root),
        schema_version=SOURCE_ITEMS_SCHEMA_VERSION,
        code='source_items_invalid_json',
    )
    if document is None:
        return _empty_source_items(workspace_id, _utc_now())
    if not isinstance(document.get('items'), dict):
        raise SyncError(
            'source item index items field is invalid',
            code='source_items_invalid',
            details={'path': str(source_items_path(root))},
        )
    return document


def _load_previous_queue(root: Path, workspace_id: str) -> dict:
    document = _read_optional_json(
        ingest_queue_path(root),
        schema_version=INGEST_QUEUE_SCHEMA_VERSION,
        code='ingest_queue_invalid_json',
    )
    if document is None:
        return _empty_queue(workspace_id, _utc_now())
    if not isinstance(document.get('entries'), list):
        raise SyncError(
            'ingest queue entries field is invalid',
            code='ingest_queue_invalid',
            details={'path': str(ingest_queue_path(root))},
        )
    return document


def _status_counts(items: list[dict]) -> dict:
    counts = {status: 0 for status in ITEM_STATUSES}
    for item in items:
        status = item.get('status')
        if status in counts:
            counts[status] += 1
    return counts


def _empty_source_items(workspace_id: str, now: str) -> dict:
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'summary': {
            'item_count': 0,
            'item_status_counts': _status_counts([]),
        },
        'items': {},
    }


def _empty_queue(workspace_id: str, now: str) -> dict:
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


def _stable_digest(*parts: object) -> str:
    payload = '\0'.join(str(part) for part in parts)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _item_id(source_id: str, item_locator_key: str) -> str:
    return f'item_{_stable_digest(source_id, item_locator_key)[:24]}'


def _queue_id(item_id: str) -> str:
    return f'queue_{_stable_digest("wikiize_source_item", item_id)[:24]}'


def _source_sort_key(source: dict) -> tuple[str, str]:
    return source.get('created_at') or '', source.get('source_id') or ''


def _source_path(source: dict) -> Path:
    return Path(source.get('locator') or '').expanduser().resolve(strict=False)


def _is_remote_repository(source: dict) -> bool:
    return source.get('type') == 'repository' and '://' in (source.get('locator') or '').strip()


def _is_remote_source(source: dict) -> bool:
    return source.get('type') in REMOTE_SOURCE_TYPES or _is_remote_repository(source)


def _hash_file(path: Path, size_bytes: int) -> tuple[dict, list[dict]]:
    if size_bytes > DEFAULT_HASH_SIZE_LIMIT_BYTES:
        return {
            'hash_status': 'too_large',
            'hash_size_limit_bytes': DEFAULT_HASH_SIZE_LIMIT_BYTES,
        }, []
    digest = hashlib.sha256()
    try:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
    except OSError as exc:
        return {
            'hash_status': 'errored',
            'hash_algorithm': 'sha256',
        }, [{'code': 'source_item_hash_failed', 'message': str(exc), 'path': str(path)}]
    return {
        'hash_status': 'hashed',
        'hash_algorithm': 'sha256',
        'sha256': digest.hexdigest(),
    }, []


def _file_fingerprint(path: Path) -> tuple[dict, list[dict]]:
    try:
        stat = path.stat()
    except OSError as exc:
        return {
            'exists': False,
            'kind': 'missing',
        }, [{'code': 'source_item_stat_failed', 'message': str(exc), 'path': str(path)}]
    fingerprint = {
        'exists': True,
        'kind': 'file',
        'size_bytes': stat.st_size,
        'mtime_ns': stat.st_mtime_ns,
    }
    hash_fingerprint, errors = _hash_file(path, stat.st_size)
    fingerprint.update(hash_fingerprint)
    return fingerprint, errors


def _make_file_item(source: dict, path: Path, now: str, *, relative_path: str | None = None) -> dict:
    locator_key = source.get('locator_key') or source.get('locator') or ''
    if relative_path:
        item_locator_key = f'{locator_key}:{relative_path}'
        locator = str(path)
    else:
        item_locator_key = locator_key
        locator = source.get('locator') or str(path)
    fingerprint, errors = _file_fingerprint(path)
    status = 'errored' if errors else 'candidate'
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'item_id': _item_id(source['source_id'], item_locator_key),
        'source_id': source['source_id'],
        'source_type': source.get('type'),
        'item_type': 'file',
        'status': status,
        'locator': locator,
        'locator_key': item_locator_key,
        'relative_path': relative_path,
        'path': str(path),
        'fingerprint': fingerprint,
        'errors': errors,
        'discovered_at': now,
    }


def _make_missing_item(source: dict, now: str, *, expected_type: str, path: Path | None = None) -> dict:
    target_path = path or _source_path(source)
    locator_key = source.get('locator_key') or source.get('locator') or str(target_path)
    errors = [{
        'code': 'source_item_missing',
        'message': 'local source item is missing',
        'path': str(target_path),
    }]
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'item_id': _item_id(source['source_id'], locator_key),
        'source_id': source['source_id'],
        'source_type': source.get('type'),
        'item_type': expected_type,
        'status': 'missing',
        'locator': source.get('locator') or str(target_path),
        'locator_key': locator_key,
        'relative_path': None,
        'path': str(target_path),
        'fingerprint': {
            'exists': False,
            'kind': 'missing',
        },
        'errors': errors,
        'discovered_at': now,
    }


def _make_errored_item(source: dict, now: str, *, code: str, message: str, path: Path | None = None) -> dict:
    target_path = path or _source_path(source)
    locator_key = source.get('locator_key') or source.get('locator') or str(target_path)
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'item_id': _item_id(source['source_id'], f'{locator_key}:error:{code}'),
        'source_id': source['source_id'],
        'source_type': source.get('type'),
        'item_type': 'error',
        'status': 'errored',
        'locator': source.get('locator') or str(target_path),
        'locator_key': locator_key,
        'relative_path': None,
        'path': str(target_path),
        'fingerprint': {
            'exists': target_path.exists(),
            'kind': 'error',
        },
        'errors': [{'code': code, 'message': message, 'path': str(target_path)}],
        'discovered_at': now,
    }


def _make_skipped_item(source: dict, path: Path, root: Path, now: str, reason: str) -> dict:
    relative_path = path.relative_to(root).as_posix()
    locator_key = source.get('locator_key') or source.get('locator') or ''
    item_locator_key = f'{locator_key}:skipped:{relative_path}'
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'item_id': _item_id(source['source_id'], item_locator_key),
        'source_id': source['source_id'],
        'source_type': source.get('type'),
        'item_type': 'skipped',
        'status': 'skipped',
        'locator': str(path),
        'locator_key': item_locator_key,
        'relative_path': relative_path,
        'path': str(path),
        'fingerprint': {
            'exists': path.exists(),
            'kind': 'skipped',
        },
        'errors': [],
        'skip_reason': reason,
        'discovered_at': now,
    }


def _make_remote_item(source: dict, now: str) -> dict:
    locator_key = source.get('locator_key') or source.get('locator') or ''
    fingerprint = {
        'kind': 'remote',
        'network_checked': False,
        'locator_key': locator_key,
    }
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'item_id': _item_id(source['source_id'], locator_key),
        'source_id': source['source_id'],
        'source_type': source.get('type'),
        'item_type': 'remote',
        'status': 'candidate',
        'locator': source.get('locator'),
        'locator_key': locator_key,
        'relative_path': None,
        'path': None,
        'fingerprint': fingerprint,
        'errors': [],
        'discovered_at': now,
    }


def _scan_directory(source: dict, root: Path, now: str) -> list[dict]:
    files: list[dict] = []
    skipped: list[dict] = []

    def walk(current: Path):
        try:
            entries = sorted(current.iterdir(), key=lambda entry: entry.name)
        except OSError as exc:
            skipped.append(_make_errored_item(
                source,
                now,
                code='source_directory_read_failed',
                message=str(exc),
                path=current,
            ))
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in IGNORED_DIRECTORY_NAMES:
                    skipped.append(_make_skipped_item(source, entry, root, now, f'ignored directory: {entry.name}'))
                    continue
                walk(entry)
            elif entry.is_file():
                files.append(_make_file_item(source, entry, now, relative_path=entry.relative_to(root).as_posix()))
            else:
                skipped.append(_make_skipped_item(source, entry, root, now, 'not a regular file'))

    walk(root)
    files.sort(key=lambda item: item.get('relative_path') or '')
    skipped.sort(key=lambda item: item.get('relative_path') or '')
    return files + skipped


def _discover_source(source: dict, now: str) -> list[dict]:
    source_type = source.get('type')
    if _is_remote_source(source):
        return [_make_remote_item(source, now)]
    path = _source_path(source)
    if source_type in LOCAL_FILE_SOURCE_TYPES:
        if not path.exists():
            return [_make_missing_item(source, now, expected_type='file', path=path)]
        if not path.is_file():
            return [_make_errored_item(
                source,
                now,
                code='source_item_type_invalid',
                message='local source item is not a regular file',
                path=path,
            )]
        return [_make_file_item(source, path, now)]
    if source_type in LOCAL_CONTAINER_SOURCE_TYPES:
        if not path.exists():
            return [_make_missing_item(source, now, expected_type=source_type, path=path)]
        if not path.is_dir():
            return [_make_errored_item(
                source,
                now,
                code='source_item_type_invalid',
                message='local source item is not a directory',
                path=path,
            )]
        return _scan_directory(source, path, now)
    return [_make_errored_item(
        source,
        now,
        code='source_type_invalid',
        message=f'unsupported source type: {source_type}',
    )]


def _fingerprint_equal(left: dict | None, right: dict | None) -> bool:
    return json.dumps(left or {}, sort_keys=True, separators=(',', ':')) == json.dumps(right or {}, sort_keys=True, separators=(',', ':'))


def _classify_item(item: dict, previous_items: dict) -> dict:
    if item['status'] in {'missing', 'skipped', 'errored'}:
        return item
    previous = previous_items.get(item['item_id'])
    if previous is None:
        item['status'] = 'new'
    elif _fingerprint_equal(item.get('fingerprint'), previous.get('fingerprint')):
        item['status'] = 'unchanged'
    else:
        item['status'] = 'changed'
    if previous is not None:
        item['previous_status'] = previous.get('status')
    return item


def _trackable_local_item(item: dict) -> bool:
    return item.get('item_type') == 'file' and item.get('path') and item.get('source_type') not in REMOTE_SOURCE_TYPES


def _preservable_fetched_remote_item(item: dict) -> bool:
    metadata = item.get('metadata') or {}
    fingerprint = item.get('fingerprint') or {}
    return (
        item.get('source_type') in REMOTE_SOURCE_TYPES
        and item.get('item_type') == 'file'
        and bool(item.get('path'))
        and (fingerprint.get('kind') == 'fetched' or bool(metadata.get('adapter')))
    )


def _preserve_fetched_remote_item(item: dict, now: str) -> dict:
    preserved = copy.deepcopy(item)
    preserved['previous_status'] = item.get('status')
    preserved['discovered_at'] = preserved.get('discovered_at') or now
    preserved['updated_at'] = now
    path = preserved.get('path')
    exists = bool(path and Path(path).exists())
    preserved['status'] = 'unchanged' if exists else 'missing'
    fingerprint = dict(preserved.get('fingerprint') or {})
    fingerprint['exists'] = exists
    preserved['fingerprint'] = fingerprint
    if exists:
        preserved['errors'] = []
    else:
        preserved['errors'] = [{
            'code': 'source_item_missing',
            'message': 'previously fetched remote source item is missing',
            'path': path,
        }]
    return preserved


def _missing_from_previous(previous: dict, now: str) -> dict:
    item = copy.deepcopy(previous)
    item['status'] = 'missing'
    item['previous_status'] = previous.get('status')
    item['discovered_at'] = now
    fingerprint = dict(item.get('fingerprint') or {})
    fingerprint['exists'] = False
    fingerprint['kind'] = 'missing'
    item['fingerprint'] = fingerprint
    item['errors'] = [{
        'code': 'source_item_missing',
        'message': 'previously indexed source item is missing',
        'path': item.get('path'),
    }]
    return item


def _source_status(items: list[dict]) -> tuple[str, list[dict]]:
    errors = []
    for item in items:
        if item.get('status') in {'missing', 'errored'}:
            errors.extend(item.get('errors') or [])
    if not items:
        return 'synced', errors
    statuses = {item.get('status') for item in items}
    if statuses <= {'missing'}:
        return 'missing', errors
    if 'errored' in statuses or 'missing' in statuses:
        return 'synced_with_errors', errors
    return 'synced', errors


def _queue_entry_for_item(item: dict, now: str, previous: dict | None = None) -> dict:
    entry = copy.deepcopy(previous) if previous else {}
    entry.update({
        'queue_id': entry.get('queue_id') or _queue_id(item['item_id']),
        'action': 'wikiize_source_item',
        'source_id': item['source_id'],
        'source_type': item.get('source_type'),
        'item_id': item['item_id'],
        'item_status': item['status'],
        'status': 'queued',
        'requires_user': False,
        'evidence': {
            'source_item_id': item['item_id'],
            'source_id': item['source_id'],
            'locator': item.get('locator'),
            'relative_path': item.get('relative_path'),
            'fingerprint': item.get('fingerprint'),
        },
        'acceptance_checks': [
            'source item still exists or remains intentionally remote at wikiization time',
            'generated wiki content cites this source item id',
            'no user confirmation is required for queued wikiization',
        ],
        'updated_at': now,
    })
    entry.setdefault('created_at', now)
    return entry


def _build_queue(previous_queue: dict, current_items: list[dict], workspace_id: str, now: str) -> dict:
    entries_by_item = {
        entry.get('item_id'): copy.deepcopy(entry)
        for entry in previous_queue.get('entries', [])
        if entry.get('item_id')
    }
    for item in current_items:
        item_id = item['item_id']
        if item['status'] in QUEUEABLE_STATUSES:
            entries_by_item[item_id] = _queue_entry_for_item(item, now, entries_by_item.get(item_id))
        elif item['status'] in {'missing', 'skipped', 'errored'}:
            entries_by_item.pop(item_id, None)
    entries = sorted(entries_by_item.values(), key=lambda entry: (entry.get('source_id') or '', entry.get('item_id') or ''))
    by_item_status: dict[str, int] = {}
    for entry in entries:
        status = entry.get('item_status') or 'unknown'
        by_item_status[status] = by_item_status.get(status, 0) + 1
    return {
        'schema_version': INGEST_QUEUE_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'summary': {
            'queue_count': len(entries),
            'by_item_status': by_item_status,
        },
        'entries': entries,
    }


def _source_items_document(workspace_id: str, now: str, items_by_id: dict) -> dict:
    items = dict(sorted(items_by_id.items()))
    item_values = list(items.values())
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'summary': {
            'item_count': len(items),
            'item_status_counts': _status_counts(item_values),
        },
        'items': items,
    }


def _sync_artifacts(root: Path) -> dict:
    return {
        'source_items': str(source_items_path(root)),
        'sync_report': str(sync_report_path(root)),
        'ingest_queue': str(ingest_queue_path(root)),
    }


def _report_document(
    root: Path,
    workspace_id: str,
    now: str,
    *,
    dry_run: bool,
    selection: dict,
    sources: list[dict],
    items: list[dict],
    queue: dict,
) -> dict:
    counts = _status_counts(items)
    return {
        'schema_version': SYNC_RUN_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'status': 'dry_run' if dry_run else 'synced',
        'base': str(root),
        'dry_run': dry_run,
        'selection': selection,
        'summary': {
            'source_count': len(sources),
            'item_count': len(items),
            'item_status_counts': counts,
            'queued_count': sum(1 for item in items if item.get('status') in QUEUEABLE_STATUSES),
            'active_queue_count': len(queue.get('entries', [])),
            'skipped_count': counts['skipped'],
            'error_count': counts['missing'] + counts['errored'],
        },
        'artifacts': _sync_artifacts(root),
        'sources': sources,
        'items': items,
        'queue': queue,
    }


def _registry_summary_for_source(items: list[dict]) -> dict:
    counts = _status_counts(items)
    return {
        'item_count': len(items),
        'item_status_counts': counts,
        'queued_count': sum(1 for item in items if item.get('status') in QUEUEABLE_STATUSES),
        'error_count': counts['missing'] + counts['errored'],
    }


def _update_registry(root: Path, registry: dict, source_results: list[dict], now: str):
    for source_result in source_results:
        source_id = source_result['source_id']
        source = registry['sources'].get(source_id)
        if not source:
            continue
        source['last_sync_status'] = source_result['last_sync_status']
        source['last_synced_at'] = now
        source['last_sync_summary'] = source_result['summary']
        source['last_sync_errors'] = source_result['errors']
        source['updated_at'] = now
    registry['updated_at'] = now
    _write_json_atomic(registry_path(root), registry)


def _load_workspace_or_error(root: Path) -> dict:
    try:
        return load_workspace(root)
    except WorkspaceError as exc:
        raise SyncError(str(exc), code=exc.code, details=exc.details) from exc


def sync_workspace(base: Path | str, source_id: str | None = None, dry_run: bool = False) -> dict:
    root = _workspace_root(base)
    now = _utc_now()
    workspace = _load_workspace_or_error(root)
    workspace_id = workspace['workspace']['workspace_id']
    registry = copy.deepcopy(workspace['registry'])
    sources_by_id = registry.get('sources') or {}

    if source_id:
        if source_id not in sources_by_id:
            raise SyncError(
                f'source not found: {source_id}',
                code='sync_source_not_found',
                details={'source_id': source_id, 'path': str(registry_path(root))},
            )
        selected_sources = [sources_by_id[source_id]]
    else:
        selected_sources = sorted(sources_by_id.values(), key=_source_sort_key)
    selected_source_ids = {source['source_id'] for source in selected_sources}
    selection = {
        'source_id': source_id,
        'source_count': len(selected_sources),
    }

    previous_source_items = _load_previous_source_items(root, workspace_id)
    previous_items_by_id = copy.deepcopy(previous_source_items.get('items') or {})
    previous_queue = _load_previous_queue(root, workspace_id)

    retained_items_by_id = {
        item_id: item
        for item_id, item in previous_items_by_id.items()
        if item.get('source_id') not in selected_source_ids
    }
    current_items: list[dict] = []
    source_results: list[dict] = []

    for source in selected_sources:
        discovered_items = [_classify_item(item, previous_items_by_id) for item in _discover_source(source, now)]
        discovered_ids = {item['item_id'] for item in discovered_items}
        previous_for_source = [
            item for item in previous_items_by_id.values()
            if item.get('source_id') == source['source_id']
        ]
        for previous in previous_for_source:
            if previous.get('item_id') in discovered_ids:
                continue
            if _preservable_fetched_remote_item(previous):
                discovered_items.append(_preserve_fetched_remote_item(previous, now))
            elif _trackable_local_item(previous):
                discovered_items.append(_missing_from_previous(previous, now))
        discovered_items.sort(key=lambda item: (
            {'file': '0', 'remote': '0', 'missing': '1', 'skipped': '2', 'error': '3'}.get(item.get('item_type'), '9'),
            item.get('relative_path') or item.get('locator_key') or item.get('item_id') or '',
        ))
        for item in discovered_items:
            retained_items_by_id[item['item_id']] = item
        current_items.extend(discovered_items)
        last_sync_status, errors = _source_status(discovered_items)
        source_results.append({
            'source_id': source['source_id'],
            'type': source.get('type'),
            'locator': source.get('locator'),
            'last_sync_status': last_sync_status,
            'summary': _registry_summary_for_source(discovered_items),
            'errors': errors,
            'source': copy.deepcopy(source),
        })

    queue = _build_queue(previous_queue, current_items, workspace_id, now)
    source_items = _source_items_document(workspace_id, now, retained_items_by_id)
    report = _report_document(
        root,
        workspace_id,
        now,
        dry_run=dry_run,
        selection=selection,
        sources=source_results,
        items=current_items,
        queue=queue,
    )

    if not dry_run:
        _write_json_atomic(source_items_path(root), source_items)
        _write_json_atomic(sync_report_path(root), report)
        _write_json_atomic(ingest_queue_path(root), queue)
        _update_registry(root, registry, source_results, now)

    return report
