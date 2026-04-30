import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4


TRUSTED_OPERATION_SCHEMA_VERSION = 'wikify.trusted-operation.v1'
TRUSTED_OPERATION_ROLLBACK_SCHEMA_VERSION = 'wikify.trusted-operation-rollback.v1'
OPERATIONS_RELATIVE_PATH = Path('.wikify') / 'trusted-operations'


class TrustedOperationError(ValueError):
    def __init__(self, message: str, code: str = 'trusted_operation_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def begin_trusted_operation(base: Path | str, *, paths: list[str], reason: str, dry_run: bool = False) -> dict:
    root = _root(base)
    normalized_paths = _normalize_paths(paths)
    if not isinstance(reason, str) or not reason.strip():
        raise TrustedOperationError('trusted operation reason is required', code='trusted_operation_reason_required')
    now = _utc_now()
    operation_id = _operation_id()
    operation_path = _operation_path(root, operation_id)
    record = {
        'schema_version': TRUSTED_OPERATION_SCHEMA_VERSION,
        'operation_id': operation_id,
        'status': 'dry_run' if dry_run else 'begun',
        'dry_run': dry_run,
        'base': str(root),
        'reason': reason.strip(),
        'created_at': now,
        'updated_at': now,
        'paths': normalized_paths,
        'snapshots': [_snapshot(root, path, key='before') for path in normalized_paths],
        'after_snapshots': [],
        'rollback': {
            'status': 'dry_run' if dry_run else 'pending_completion',
            'guard': 'complete the operation before rollback is available',
        },
        'artifacts': {
            'operation': str(operation_path),
        },
        'summary': _summary(normalized_paths),
    }
    if not dry_run:
        _write_json(operation_path, record)
    return record


def complete_trusted_operation(base: Path | str, operation_path: Path | str) -> dict:
    root = _root(base)
    resolved_path = _resolve_operation_path(root, operation_path)
    record = _load_operation(resolved_path)
    if record.get('status') not in {'begun', 'completed'}:
        raise TrustedOperationError(
            'trusted operation cannot be completed from current status',
            code='trusted_operation_status_invalid',
            details={'status': record.get('status')},
        )
    paths = [_normalize_relative_path(path) for path in record.get('paths') or []]
    now = _utc_now()
    record['status'] = 'completed'
    record['dry_run'] = False
    record['completed_at'] = now
    record['updated_at'] = now
    record['after_snapshots'] = [_snapshot(root, path, key='after') for path in paths]
    record['rollback'] = {
        'status': 'available',
        'guard': 'current file state must match after snapshots',
    }
    record['summary'] = _summary(paths)
    _write_json(resolved_path, record)
    return record


def rollback_trusted_operation(base: Path | str, operation_path: Path | str, *, dry_run: bool = False) -> dict:
    root = _root(base)
    resolved_path = _resolve_operation_path(root, operation_path)
    record = _load_operation(resolved_path)
    if record.get('status') not in {'completed', 'rolled_back'}:
        raise TrustedOperationError(
            'trusted operation rollback requires a completed operation',
            code='trusted_operation_status_invalid',
            details={'status': record.get('status')},
        )
    before_by_path = {snapshot.get('path'): snapshot.get('before') for snapshot in record.get('snapshots') or []}
    after_by_path = {snapshot.get('path'): snapshot.get('after') for snapshot in record.get('after_snapshots') or []}
    paths = [_normalize_relative_path(path) for path in record.get('paths') or []]
    for relative_path in paths:
        expected_after = after_by_path.get(relative_path)
        if not isinstance(expected_after, dict):
            raise TrustedOperationError(
                'trusted operation is missing after snapshot',
                code='trusted_operation_after_snapshot_missing',
                details={'path': relative_path},
            )
        _validate_current_matches_after(root, relative_path, expected_after)

    if not dry_run:
        for relative_path in reversed(paths):
            before = before_by_path.get(relative_path)
            if not isinstance(before, dict):
                raise TrustedOperationError(
                    'trusted operation is missing before snapshot',
                    code='trusted_operation_before_snapshot_missing',
                    details={'path': relative_path},
                )
            _restore_before(root, relative_path, before)
        now = _utc_now()
        record['status'] = 'rolled_back'
        record['rolled_back_at'] = now
        record['updated_at'] = now
        record['rollback'] = {
            'status': 'completed',
            'completed_at': now,
            'guard': 'current file state matched after snapshots',
        }
        _write_json(resolved_path, record)

    return {
        'schema_version': TRUSTED_OPERATION_ROLLBACK_SCHEMA_VERSION,
        'base': str(root),
        'operation_id': record.get('operation_id'),
        'status': 'dry_run' if dry_run else 'rolled_back',
        'dry_run': dry_run,
        'operation_path': str(resolved_path),
        'summary': _summary(paths),
        'artifacts': {
            'operation': str(resolved_path),
        },
    }


def _root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _operation_id() -> str:
    return f'op_{uuid4().hex[:24]}'


def _operation_path(root: Path, operation_id: str) -> Path:
    return root / OPERATIONS_RELATIVE_PATH / f'{operation_id}.json'


def _normalize_paths(paths: list[str]) -> list[str]:
    if not isinstance(paths, list) or not paths:
        raise TrustedOperationError('trusted operation needs at least one path', code='trusted_operation_paths_required')
    return sorted(dict.fromkeys(_normalize_relative_path(path) for path in paths))


def _normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrustedOperationError('trusted operation path is empty', code='trusted_operation_path_invalid')
    raw = value.strip().replace('\\', '/')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts:
        raise TrustedOperationError(
            f'trusted operation path must be relative and stay inside the wiki: {value}',
            code='trusted_operation_path_invalid',
            details={'path': value},
        )
    return str(path)


def _content_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if root not in (path, *path.parents):
        raise TrustedOperationError(
            f'trusted operation path must stay inside the wiki: {relative_path}',
            code='trusted_operation_path_invalid',
            details={'path': relative_path},
        )
    return path


def _file_state(root: Path, relative_path: str) -> dict:
    path = _content_path(root, relative_path)
    if not path.exists():
        return {'exists': False, 'sha256': None, 'content': None}
    if not path.is_file():
        raise TrustedOperationError(
            'trusted operation can only snapshot files',
            code='trusted_operation_path_invalid',
            details={'path': relative_path},
        )
    content = path.read_text(encoding='utf-8')
    return {'exists': True, 'sha256': _sha256(content), 'content': content}


def _snapshot(root: Path, relative_path: str, *, key: str) -> dict:
    return {'path': relative_path, key: _file_state(root, relative_path)}


def _resolve_operation_path(root: Path, value: Path | str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if root not in (path, *path.parents):
        raise TrustedOperationError(
            'trusted operation record path must stay inside the wiki',
            code='trusted_operation_path_invalid',
            details={'path': str(value)},
        )
    if not path.exists():
        raise TrustedOperationError(
            f'trusted operation record not found: {path}',
            code='trusted_operation_not_found',
            details={'path': str(path)},
        )
    return path


def _load_operation(path: Path) -> dict:
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise TrustedOperationError(
            'trusted operation record is invalid JSON',
            code='trusted_operation_invalid_json',
            details={'path': str(path)},
        ) from exc
    if not isinstance(record, dict) or record.get('schema_version') != TRUSTED_OPERATION_SCHEMA_VERSION:
        raise TrustedOperationError(
            'trusted operation schema is not supported',
            code='trusted_operation_schema_invalid',
            details={'path': str(path), 'schema_version': record.get('schema_version') if isinstance(record, dict) else None},
        )
    return record


def _validate_current_matches_after(root: Path, relative_path: str, expected_after: dict):
    current = _file_state(root, relative_path)
    if bool(current.get('exists')) != bool(expected_after.get('exists')):
        raise TrustedOperationError(
            'current file existence does not match trusted operation after snapshot',
            code='trusted_operation_rollback_hash_mismatch',
            details={'path': relative_path, 'expected_exists': expected_after.get('exists'), 'actual_exists': current.get('exists')},
        )
    if current.get('sha256') != expected_after.get('sha256'):
        raise TrustedOperationError(
            'current file hash does not match trusted operation after snapshot',
            code='trusted_operation_rollback_hash_mismatch',
            details={'path': relative_path, 'expected': expected_after.get('sha256'), 'actual': current.get('sha256')},
        )


def _restore_before(root: Path, relative_path: str, before: dict):
    path = _content_path(root, relative_path)
    if before.get('exists'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(before.get('content') or '', encoding='utf-8')
    elif path.exists():
        if not path.is_file():
            raise TrustedOperationError(
                'trusted operation rollback can only remove files',
                code='trusted_operation_path_invalid',
                details={'path': relative_path},
            )
        path.unlink()


def _summary(paths: list[str]) -> dict:
    return {'path_count': len(paths), 'affected_paths': list(paths)}


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
