import json
import posixpath
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


WORKSPACE_SCHEMA_VERSION = 'wikify.workspace.v1'
SOURCE_REGISTRY_SCHEMA_VERSION = 'wikify.source-registry.v1'
MANIFEST_FILENAME = 'wikify.json'
REGISTRY_PATH = Path('.wikify') / 'registry' / 'sources.json'
DEFAULT_PATHS = {
    'sources': 'sources',
    'wiki': 'wiki',
    'artifacts': 'artifacts',
    'views': 'views',
    'state': '.wikify',
}
SOURCE_TYPES = {'file', 'directory', 'url', 'repository', 'note'}
LOCAL_SOURCE_TYPES = {'file', 'directory', 'note'}


class WorkspaceError(ValueError):
    def __init__(self, message: str, code: str = 'workspace_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _workspace_root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def manifest_path(base: Path | str) -> Path:
    return _workspace_root(base) / MANIFEST_FILENAME


def registry_path(base: Path | str) -> Path:
    return _workspace_root(base) / REGISTRY_PATH


def _write_json_atomic(path: Path, document: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp_path.replace(path)


def _read_json(path: Path, *, code: str):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise WorkspaceError(
            f'workspace JSON is invalid: {path}',
            code=code,
            details={'path': str(path)},
        ) from exc


def _empty_registry(workspace_id: str, now: str) -> dict:
    return {
        'schema_version': SOURCE_REGISTRY_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'updated_at': now,
        'sources': {},
    }


def _resolved_paths(root: Path, manifest: dict) -> dict:
    paths = manifest.get('paths') or DEFAULT_PATHS
    return {key: str((root / value).resolve()) for key, value in paths.items()}


def _load_manifest(root: Path) -> dict:
    path = manifest_path(root)
    if not path.exists():
        raise WorkspaceError(
            f'wikify workspace is not initialized: {root}',
            code='workspace_missing',
            details={'base': str(root), 'manifest': str(path)},
        )
    manifest = _read_json(path, code='workspace_manifest_invalid_json')
    if manifest.get('schema_version') != WORKSPACE_SCHEMA_VERSION:
        raise WorkspaceError(
            'wikify workspace schema is not supported',
            code='workspace_schema_invalid',
            details={'schema_version': manifest.get('schema_version'), 'manifest': str(path)},
        )
    if not manifest.get('workspace_id'):
        raise WorkspaceError(
            'wikify workspace id is missing',
            code='workspace_manifest_invalid',
            details={'manifest': str(path)},
        )
    manifest.setdefault('paths', dict(DEFAULT_PATHS))
    return manifest


def _load_registry(root: Path, manifest: dict) -> dict:
    path = registry_path(root)
    if not path.exists():
        raise WorkspaceError(
            f'wikify source registry not found: {path}',
            code='source_registry_missing',
            details={'path': str(path)},
        )
    registry = _read_json(path, code='source_registry_invalid_json')
    if registry.get('schema_version') != SOURCE_REGISTRY_SCHEMA_VERSION:
        raise WorkspaceError(
            'wikify source registry schema is not supported',
            code='source_registry_schema_invalid',
            details={'schema_version': registry.get('schema_version'), 'path': str(path)},
        )
    if registry.get('workspace_id') != manifest.get('workspace_id'):
        raise WorkspaceError(
            'wikify source registry workspace id does not match manifest',
            code='source_registry_workspace_mismatch',
            details={'path': str(path)},
        )
    if not isinstance(registry.get('sources'), dict):
        raise WorkspaceError(
            'wikify source registry sources field is invalid',
            code='source_registry_invalid',
            details={'path': str(path)},
        )
    return registry


def initialize_workspace(base: Path | str) -> dict:
    root = _workspace_root(base)
    now = _utc_now()
    root.mkdir(parents=True, exist_ok=True)

    existing_manifest = None
    path = manifest_path(root)
    if path.exists():
        existing_manifest = _load_manifest(root)
    workspace_id = (existing_manifest or {}).get('workspace_id') or f'wk_{uuid.uuid4().hex}'
    created_at = (existing_manifest or {}).get('created_at') or now
    manifest = {
        'schema_version': WORKSPACE_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'created_at': created_at,
        'updated_at': now,
        'paths': dict(DEFAULT_PATHS),
    }

    for relative_path in DEFAULT_PATHS.values():
        (root / relative_path).mkdir(parents=True, exist_ok=True)
    (root / REGISTRY_PATH.parent).mkdir(parents=True, exist_ok=True)

    registry_file = registry_path(root)
    if registry_file.exists():
        registry = _load_registry(root, manifest)
        registry.setdefault('sources', {})
        registry['updated_at'] = registry.get('updated_at') or now
    else:
        registry = _empty_registry(workspace_id, now)

    _write_json_atomic(path, manifest)
    _write_json_atomic(registry_file, registry)
    return {
        'schema_version': WORKSPACE_SCHEMA_VERSION,
        'status': 'initialized',
        'base': str(root),
        'workspace': manifest,
        'paths': _resolved_paths(root, manifest),
        'artifacts': {
            'manifest': str(path),
            'source_registry': str(registry_file),
        },
    }


def load_workspace(base: Path | str) -> dict:
    root = _workspace_root(base)
    manifest = _load_manifest(root)
    registry = _load_registry(root, manifest)
    return {
        'schema_version': WORKSPACE_SCHEMA_VERSION,
        'base': str(root),
        'workspace': manifest,
        'registry': registry,
        'paths': _resolved_paths(root, manifest),
        'artifacts': {
            'manifest': str(manifest_path(root)),
            'source_registry': str(registry_path(root)),
        },
    }


def _normalize_url(locator: str) -> str:
    parts = urlsplit(locator.strip())
    if not parts.scheme or not parts.netloc:
        raise WorkspaceError(
            'URL source locator must include scheme and host',
            code='source_locator_invalid',
            details={'locator': locator},
        )
    scheme = parts.scheme.lower()
    hostname = (parts.hostname or '').lower()
    if not hostname:
        raise WorkspaceError(
            'URL source locator host is invalid',
            code='source_locator_invalid',
            details={'locator': locator},
        )
    port = parts.port
    if port and not ((scheme == 'http' and port == 80) or (scheme == 'https' and port == 443)):
        netloc = f'{hostname}:{port}'
    else:
        netloc = hostname
    path = posixpath.normpath(parts.path or '/')
    if parts.path.endswith('/') and not path.endswith('/'):
        path += '/'
    if path == '.':
        path = '/'
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ''))


def _local_locator_key(source_type: str, locator: str) -> str:
    return f'{source_type}:{Path(locator).expanduser().resolve(strict=False).as_posix()}'


def _locator_key(source_type: str, locator: str) -> str:
    if source_type in LOCAL_SOURCE_TYPES:
        return _local_locator_key(source_type, locator)
    if source_type == 'url':
        return f'url:{_normalize_url(locator)}'
    if source_type == 'repository':
        stripped = locator.strip()
        if '://' in stripped:
            return f'repository:{_normalize_url(stripped)}'
        return _local_locator_key(source_type, stripped)
    raise WorkspaceError(
        f'unsupported source type: {source_type}',
        code='source_type_invalid',
        details={'type': source_type, 'supported': sorted(SOURCE_TYPES)},
    )


def _local_fingerprint(source_type: str, locator: str) -> tuple[dict, str, list[dict]]:
    path = Path(locator).expanduser().resolve(strict=False)
    exists = path.exists()
    fingerprint = {
        'exists': exists,
        'kind': 'missing',
    }
    errors: list[dict] = []
    if not exists:
        errors.append({'code': 'source_missing', 'message': 'local source path does not exist'})
        return fingerprint, 'missing', errors
    try:
        stat = path.stat()
    except OSError as exc:
        errors.append({'code': 'source_stat_failed', 'message': str(exc)})
        return fingerprint, 'missing', errors
    if path.is_file():
        kind = 'file'
    elif path.is_dir():
        kind = 'directory'
    else:
        kind = 'other'
    fingerprint.update({
        'kind': kind,
        'mtime_ns': stat.st_mtime_ns,
        'inode': getattr(stat, 'st_ino', None),
        'device': getattr(stat, 'st_dev', None),
    })
    if path.is_file():
        fingerprint['size_bytes'] = stat.st_size
    if source_type == 'repository' and path.is_dir():
        fingerprint['git_dir_exists'] = (path / '.git').exists()
    return fingerprint, 'found', errors


def _remote_fingerprint() -> tuple[dict, str, list[dict]]:
    return {'network_checked': False}, 'unverified', []


def _build_fingerprint(source_type: str, locator: str) -> tuple[dict, str, list[dict]]:
    if source_type in LOCAL_SOURCE_TYPES:
        return _local_fingerprint(source_type, locator)
    if source_type == 'url':
        return _remote_fingerprint()
    if source_type == 'repository':
        if '://' in locator.strip():
            return _remote_fingerprint()
        return _local_fingerprint(source_type, locator)
    raise WorkspaceError(
        f'unsupported source type: {source_type}',
        code='source_type_invalid',
        details={'type': source_type, 'supported': sorted(SOURCE_TYPES)},
    )


def _source_result(root: Path, status: str, source: dict) -> dict:
    return {
        'schema_version': SOURCE_REGISTRY_SCHEMA_VERSION,
        'status': status,
        'base': str(root),
        'source': source,
        'artifacts': {
            'source_registry': str(registry_path(root)),
        },
    }


def _registry_with_workspace(base: Path | str) -> tuple[Path, dict, dict]:
    root = _workspace_root(base)
    manifest = _load_manifest(root)
    registry = _load_registry(root, manifest)
    return root, manifest, registry


def _source_sort_key(source: dict) -> tuple[str, str]:
    return source.get('created_at') or '', source.get('source_id') or ''


def add_source(base: Path | str, locator: str, source_type: str) -> dict:
    root, manifest, registry = _registry_with_workspace(base)
    normalized_type = (source_type or '').strip().lower()
    if normalized_type not in SOURCE_TYPES:
        raise WorkspaceError(
            f'unsupported source type: {source_type}',
            code='source_type_invalid',
            details={'type': source_type, 'supported': sorted(SOURCE_TYPES)},
        )
    locator_value = (locator or '').strip()
    if not locator_value:
        raise WorkspaceError('source locator is required', code='source_locator_invalid')

    key = _locator_key(normalized_type, locator_value)
    for source in registry['sources'].values():
        if source.get('locator_key') == key:
            return _source_result(root, 'existing', source)

    now = _utc_now()
    fingerprint, discovery_status, errors = _build_fingerprint(normalized_type, locator_value)
    source_id = f'src_{uuid.uuid4().hex}'
    source = {
        'source_id': source_id,
        'type': normalized_type,
        'locator': locator_value,
        'locator_key': key,
        'fingerprint': fingerprint,
        'discovery_status': discovery_status,
        'last_sync_status': 'never_synced',
        'created_at': now,
        'updated_at': now,
        'errors': errors,
    }
    registry['sources'][source_id] = source
    registry['workspace_id'] = manifest['workspace_id']
    registry['updated_at'] = now
    _write_json_atomic(registry_path(root), registry)
    return _source_result(root, 'added', source)


def list_sources(base: Path | str) -> dict:
    root, _, registry = _registry_with_workspace(base)
    sources = sorted(registry['sources'].values(), key=_source_sort_key)
    return {
        'schema_version': SOURCE_REGISTRY_SCHEMA_VERSION,
        'status': 'listed',
        'base': str(root),
        'sources': sources,
        'summary': {
            'source_count': len(sources),
        },
        'artifacts': {
            'source_registry': str(registry_path(root)),
        },
    }


def show_source(base: Path | str, source_id_or_locator: str) -> dict:
    root, _, registry = _registry_with_workspace(base)
    target = (source_id_or_locator or '').strip()
    source = registry['sources'].get(target)
    if source is None:
        for candidate in registry['sources'].values():
            if candidate.get('locator') == target or candidate.get('locator_key') == target:
                source = candidate
                break
    if source is None:
        raise WorkspaceError(
            f'source not found: {target}',
            code='source_not_found',
            details={'target': target, 'path': str(registry_path(root))},
        )
    return _source_result(root, 'shown', source)
