import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from wikify.maintenance.preservation import GeneratedPagePreservationError, validate_patch_bundle_preservation


BUNDLE_SCHEMA_VERSION = 'wikify.patch-bundle.v1'
PREFLIGHT_SCHEMA_VERSION = 'wikify.patch-application-preflight.v1'
APPLICATION_SCHEMA_VERSION = 'wikify.patch-application.v1'
ROLLBACK_SCHEMA_VERSION = 'wikify.patch-rollback.v1'
APPLICATIONS_RELATIVE_PATH = Path('sorted') / 'graph-patch-applications'


class PatchApplyError(ValueError):
    def __init__(self, message: str, code: str = 'patch_apply_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


class PatchRollbackError(PatchApplyError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _load_json(path: Path, code: str) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise PatchApplyError(f'patch artifact not found: {path}', code=code, details={'path': str(path)}) from exc
    except json.JSONDecodeError as exc:
        raise PatchApplyError(
            f'patch artifact is not valid JSON: {path}',
            code='patch_artifact_invalid_json',
            details={'path': str(path)},
        ) from exc


def _resolve_existing_path(base: Path, value: Path | str, missing_code: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.exists():
        raise PatchApplyError(f'patch artifact not found: {path}', code=missing_code, details={'path': str(path)})
    return path


def _normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PatchApplyError('patch operation path is empty', code='patch_path_invalid')
    raw = value.strip().replace('\\', '/')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts:
        raise PatchApplyError(
            f'patch operation path must be relative and stay inside the wiki: {value}',
            code='patch_path_invalid',
            details={'path': value},
        )
    return str(path)


def _content_path(base: Path, relative_path: str) -> Path:
    path = (base / relative_path).resolve()
    if base not in (path, *path.parents):
        raise PatchApplyError(
            f'patch operation path must stay inside the wiki: {relative_path}',
            code='patch_path_invalid',
            details={'path': relative_path},
        )
    return path


def _application_id(task_id: str, created_at: str) -> str:
    stamp = created_at.replace('-', '').replace(':', '').replace('Z', 'Z')
    return f'{task_id}-{stamp}'


def _application_path(base: Path, application_id: str) -> Path:
    return base / APPLICATIONS_RELATIVE_PATH / f'{application_id}.json'


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _validate_proposal_and_bundle(base: Path, proposal_path: Path | str, bundle_path: Path | str) -> tuple[Path, Path, dict, dict]:
    resolved_proposal = _resolve_existing_path(base, proposal_path, 'patch_proposal_not_found')
    resolved_bundle = _resolve_existing_path(base, bundle_path, 'patch_bundle_not_found')
    proposal = _load_json(resolved_proposal, 'patch_proposal_not_found')
    bundle = _load_json(resolved_bundle, 'patch_bundle_not_found')

    if proposal.get('schema_version') != 'wikify.patch-proposal.v1':
        raise PatchApplyError(
            'patch proposal schema is not supported',
            code='patch_proposal_schema_invalid',
            details={'schema_version': proposal.get('schema_version')},
        )
    if bundle.get('schema_version') != BUNDLE_SCHEMA_VERSION:
        raise PatchApplyError(
            'patch bundle schema is not supported',
            code='patch_bundle_schema_invalid',
            details={'schema_version': bundle.get('schema_version')},
        )

    task_id = proposal.get('task_id')
    if bundle.get('proposal_task_id') != task_id:
        raise PatchApplyError(
            'patch bundle task id does not match proposal',
            code='patch_bundle_task_mismatch',
            details={'proposal_task_id': task_id, 'bundle_task_id': bundle.get('proposal_task_id')},
        )
    operations = bundle.get('operations')
    if not isinstance(operations, list) or not operations:
        raise PatchApplyError('patch bundle has no operations', code='patch_bundle_empty')

    return resolved_proposal, resolved_bundle, proposal, bundle


def _validated_operations(base: Path, proposal: dict, bundle: dict) -> list[dict]:
    write_scope = {_normalize_relative_path(path) for path in proposal.get('write_scope') or []}
    if not write_scope:
        raise PatchApplyError('patch proposal is missing write scope', code='patch_write_scope_missing')

    result = []
    seen_paths = set()
    for index, operation in enumerate(bundle.get('operations') or []):
        op_type = operation.get('operation')
        if op_type != 'replace_text':
            raise PatchApplyError(
                f'unsupported patch operation: {op_type}',
                code='patch_operation_unsupported',
                details={'index': index, 'operation': op_type},
            )

        relative_path = _normalize_relative_path(operation.get('path'))
        if relative_path not in write_scope:
            raise PatchApplyError(
                f'patch operation path is outside proposal write scope: {relative_path}',
                code='patch_operation_out_of_scope',
                details={'index': index, 'path': relative_path, 'write_scope': sorted(write_scope)},
            )
        if relative_path in seen_paths:
            raise PatchApplyError(
                f'only one patch operation per path is supported in this phase: {relative_path}',
                code='patch_operation_conflict',
                details={'index': index, 'path': relative_path},
            )
        seen_paths.add(relative_path)

        find = operation.get('find')
        replace = operation.get('replace')
        if not isinstance(find, str) or find == '':
            raise PatchApplyError('replace_text operation requires non-empty find text', code='patch_operation_invalid')
        if not isinstance(replace, str):
            raise PatchApplyError('replace_text operation requires replacement text', code='patch_operation_invalid')
        if find == replace:
            raise PatchApplyError('replace_text operation must change text', code='patch_operation_noop')

        path = _content_path(base, relative_path)
        try:
            before = path.read_text(encoding='utf-8')
        except FileNotFoundError as exc:
            raise PatchApplyError(
                f'patch target file not found: {relative_path}',
                code='patch_target_not_found',
                details={'index': index, 'path': relative_path},
            ) from exc

        occurrences = before.count(find)
        if occurrences != 1:
            raise PatchApplyError(
                f'expected exactly one occurrence for replace_text in {relative_path}',
                code='patch_preflight_failed',
                details={'index': index, 'path': relative_path, 'occurrences': occurrences},
            )

        after = before.replace(find, replace, 1)
        result.append(
            {
                'index': index,
                'operation': 'replace_text',
                'path': relative_path,
                'absolute_path': str(path),
                'find': find,
                'replace': replace,
                'rationale': operation.get('rationale'),
                'before_hash': _sha256(before),
                'after_hash': _sha256(after),
                'occurrences': occurrences,
            }
        )

    return result


def _validate_preservation(base: Path, proposal: dict, bundle: dict) -> dict:
    try:
        return validate_patch_bundle_preservation(base, proposal, bundle)
    except GeneratedPagePreservationError as exc:
        raise PatchApplyError(str(exc), code=exc.code, details=dict(exc.details or {})) from exc


def preflight_patch_bundle(base: Path | str, proposal_path: Path | str, bundle_path: Path | str) -> dict:
    root = Path(base).expanduser().resolve()
    resolved_proposal, resolved_bundle, proposal, bundle = _validate_proposal_and_bundle(root, proposal_path, bundle_path)
    operations = _validated_operations(root, proposal, bundle)
    preservation = _validate_preservation(root, proposal, bundle)
    return {
        'schema_version': PREFLIGHT_SCHEMA_VERSION,
        'base': str(root),
        'ready': True,
        'writes_content': False,
        'proposal_path': str(resolved_proposal),
        'bundle_path': str(resolved_bundle),
        'task_id': proposal.get('task_id'),
        'operations': [
            {
                'operation': op['operation'],
                'path': op['path'],
                'before_hash': op['before_hash'],
                'after_hash': op['after_hash'],
            }
            for op in operations
        ],
        'preservation': preservation,
        'summary': {
            'task_id': proposal.get('task_id'),
            'operation_count': len(operations),
            'affected_paths': sorted({op['path'] for op in operations}),
        },
    }


def apply_patch_bundle(base: Path | str, proposal_path: Path | str, bundle_path: Path | str) -> dict:
    root = Path(base).expanduser().resolve()
    resolved_proposal, resolved_bundle, proposal, bundle = _validate_proposal_and_bundle(root, proposal_path, bundle_path)
    operations = _validated_operations(root, proposal, bundle)
    preservation = _validate_preservation(root, proposal, bundle)

    applied_operations = []
    for op in operations:
        path = Path(op['absolute_path'])
        before = path.read_text(encoding='utf-8')
        if _sha256(before) != op['before_hash']:
            raise PatchApplyError(
                f'patch target changed during apply: {op["path"]}',
                code='patch_target_changed',
                details={'path': op['path']},
            )
        after = before.replace(op['find'], op['replace'], 1)
        path.write_text(after, encoding='utf-8')
        applied_operations.append({key: value for key, value in op.items() if key != 'absolute_path'})

    now = _utc_now()
    task_id = proposal.get('task_id')
    application_id = _application_id(task_id, now)
    path = _application_path(root, application_id)
    record = {
        'schema_version': APPLICATION_SCHEMA_VERSION,
        'application_id': application_id,
        'created_at': now,
        'status': 'applied',
        'base': str(root),
        'task_id': task_id,
        'proposal_path': str(resolved_proposal),
        'bundle_path': str(resolved_bundle),
        'affected_paths': sorted({op['path'] for op in applied_operations}),
        'operations': applied_operations,
        'preservation': preservation,
        'rollback': {
            'status': 'available',
            'guard': 'current file hash must match operation after_hash',
        },
        'artifacts': {
            'application': str(path),
        },
        'summary': {
            'task_id': task_id,
            'operation_count': len(applied_operations),
            'affected_paths': sorted({op['path'] for op in applied_operations}),
        },
    }
    _write_json(path, record)
    return record


def rollback_application(base: Path | str, application_path: Path | str, dry_run: bool = False) -> dict:
    root = Path(base).expanduser().resolve()
    resolved_application = _resolve_existing_path(root, application_path, 'patch_application_not_found')
    record = _load_json(resolved_application, 'patch_application_not_found')
    if record.get('schema_version') != APPLICATION_SCHEMA_VERSION:
        raise PatchRollbackError(
            'patch application schema is not supported',
            code='patch_application_schema_invalid',
            details={'schema_version': record.get('schema_version')},
        )

    operations = list(record.get('operations') or [])
    if not operations:
        raise PatchRollbackError('patch application has no operations', code='patch_application_empty')

    for op in reversed(operations):
        relative_path = _normalize_relative_path(op.get('path'))
        path = _content_path(root, relative_path)
        current = path.read_text(encoding='utf-8')
        current_hash = _sha256(current)
        if current_hash != op.get('after_hash'):
            raise PatchRollbackError(
                f'current content does not match applied hash for rollback: {relative_path}',
                code='patch_rollback_hash_mismatch',
                details={'path': relative_path, 'expected': op.get('after_hash'), 'actual': current_hash},
            )
        if current.count(op.get('replace')) != 1:
            raise PatchRollbackError(
                f'expected exactly one replacement occurrence for rollback: {relative_path}',
                code='patch_rollback_preflight_failed',
                details={'path': relative_path, 'occurrences': current.count(op.get('replace'))},
            )

    if not dry_run:
        for op in reversed(operations):
            path = _content_path(root, _normalize_relative_path(op.get('path')))
            current = path.read_text(encoding='utf-8')
            restored = current.replace(op.get('replace'), op.get('find'), 1)
            path.write_text(restored, encoding='utf-8')

        now = _utc_now()
        record['status'] = 'rolled_back'
        record['rolled_back_at'] = now
        record['rollback'] = {
            'status': 'completed',
            'completed_at': now,
            'guard': 'current file hash matched operation after_hash',
        }
        _write_json(resolved_application, record)

    status = 'dry_run' if dry_run else 'rolled_back'
    return {
        'schema_version': ROLLBACK_SCHEMA_VERSION,
        'base': str(root),
        'application_id': record.get('application_id'),
        'status': status,
        'dry_run': dry_run,
        'application_path': str(resolved_application),
        'summary': {
            'task_id': record.get('task_id'),
            'operation_count': len(operations),
            'affected_paths': sorted({op.get('path') for op in operations}),
        },
        'artifacts': {
            'application': str(resolved_application),
        },
    }
