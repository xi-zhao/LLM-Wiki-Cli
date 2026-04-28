import json
from datetime import datetime, timezone
from pathlib import Path

from wikify.maintenance.bundle_producer import DEFAULT_TIMEOUT_SECONDS


SCHEMA_VERSION = 'wikify.agent-profiles.v1'
PROFILE_FILENAME = 'wikify-agent-profiles.json'
DEFAULT_PROFILE_SENTINEL = '@default'


class AgentProfileError(ValueError):
    def __init__(self, message: str, code: str = 'agent_profile_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def agent_profile_path(base: Path | str) -> Path:
    return Path(base).expanduser().resolve() / PROFILE_FILENAME


def _empty_document() -> dict:
    return {
        'schema_version': SCHEMA_VERSION,
        'default_profile': None,
        'profiles': {},
    }


def _validate_name(name: str) -> str:
    value = (name or '').strip()
    if not value:
        raise AgentProfileError('agent profile name is required', code='agent_profile_name_invalid')
    if '/' in value or '\\' in value:
        raise AgentProfileError('agent profile name must not contain path separators', code='agent_profile_name_invalid')
    return value


def _load_document(root: Path, *, missing_ok: bool = False) -> dict:
    path = agent_profile_path(root)
    if not path.exists():
        if missing_ok:
            return _empty_document()
        raise AgentProfileError(
            f'agent profile config not found: {path}',
            code='agent_profile_config_missing',
            details={'path': str(path)},
        )
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise AgentProfileError(
            f'agent profile config is not valid JSON: {path}',
            code='agent_profile_config_invalid_json',
            details={'path': str(path)},
        ) from exc
    if document.get('schema_version') != SCHEMA_VERSION:
        raise AgentProfileError(
            'agent profile config schema is not supported',
            code='agent_profile_config_schema_invalid',
            details={'schema_version': document.get('schema_version')},
        )
    if not isinstance(document.get('profiles'), dict):
        raise AgentProfileError(
            'agent profile config profiles field is invalid',
            code='agent_profile_config_invalid',
            details={'path': str(path)},
        )
    document.setdefault('default_profile', None)
    return document


def _write_document(root: Path, document: dict) -> Path | None:
    path = agent_profile_path(root)
    document.setdefault('schema_version', SCHEMA_VERSION)
    document.setdefault('default_profile', None)
    document.setdefault('profiles', {})
    if document.get('profiles'):
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return path
    if path.exists():
        path.unlink()
    return None


def _profile_result(root: Path, status: str, profile: dict | None = None) -> dict:
    path = agent_profile_path(root)
    result = {
        'schema_version': SCHEMA_VERSION,
        'base': str(root),
        'status': status,
        'artifacts': {
            'agent_profiles': str(path) if path.exists() else None,
        },
        'default_profile': None,
    }
    if profile is not None:
        result['profile'] = profile
    return result


def set_agent_profile(
    base: Path | str,
    name: str,
    agent_command: str,
    *,
    producer_timeout_seconds: float | None = None,
    description: str | None = None,
) -> dict:
    root = Path(base).expanduser().resolve()
    profile_name = _validate_name(name)
    command = (agent_command or '').strip()
    if not command:
        raise AgentProfileError('agent command is required for profile', code='agent_profile_command_required')

    document = _load_document(root, missing_ok=True)
    existing = document['profiles'].get(profile_name, {})
    now = _utc_now()
    timeout = DEFAULT_TIMEOUT_SECONDS if producer_timeout_seconds is None else float(producer_timeout_seconds)
    profile = {
        'name': profile_name,
        'agent_command': command,
        'producer_timeout_seconds': timeout,
        'description': description,
        'created_at': existing.get('created_at') or now,
        'updated_at': now,
    }
    document['profiles'][profile_name] = profile
    _write_document(root, document)
    return _profile_result(root, 'saved', profile)


def list_agent_profiles(base: Path | str) -> dict:
    root = Path(base).expanduser().resolve()
    document = _load_document(root, missing_ok=True)
    profiles = [document['profiles'][key] for key in sorted(document['profiles'])]
    result = _profile_result(root, 'listed')
    result['default_profile'] = document.get('default_profile')
    result['profiles'] = profiles
    result['summary'] = {
        'profile_count': len(profiles),
        'default_profile': document.get('default_profile'),
    }
    return result


def show_agent_profile(base: Path | str, name: str) -> dict:
    root = Path(base).expanduser().resolve()
    profile_name = _validate_name(name)
    document = _load_document(root)
    profile = document['profiles'].get(profile_name)
    if profile is None:
        raise AgentProfileError(
            f'agent profile not found: {profile_name}',
            code='agent_profile_missing',
            details={'profile': profile_name, 'path': str(agent_profile_path(root))},
        )
    return _profile_result(root, 'shown', profile)


def unset_agent_profile(base: Path | str, name: str) -> dict:
    root = Path(base).expanduser().resolve()
    profile_name = _validate_name(name)
    document = _load_document(root)
    profile = document['profiles'].pop(profile_name, None)
    if profile is None:
        raise AgentProfileError(
            f'agent profile not found: {profile_name}',
            code='agent_profile_missing',
            details={'profile': profile_name, 'path': str(agent_profile_path(root))},
        )
    if document.get('default_profile') == profile_name:
        document['default_profile'] = None
    _write_document(root, document)
    return _profile_result(root, 'removed', profile)


def set_default_agent_profile(base: Path | str, name: str) -> dict:
    root = Path(base).expanduser().resolve()
    profile_name = _validate_name(name)
    document = _load_document(root)
    profile = document['profiles'].get(profile_name)
    if profile is None:
        raise AgentProfileError(
            f'agent profile not found: {profile_name}',
            code='agent_profile_missing',
            details={'profile': profile_name, 'path': str(agent_profile_path(root))},
        )
    document['default_profile'] = profile_name
    _write_document(root, document)
    result = _profile_result(root, 'default_set', profile)
    result['default_profile'] = profile_name
    return result


def show_default_agent_profile(base: Path | str) -> dict:
    root = Path(base).expanduser().resolve()
    document = _load_document(root)
    default_profile = document.get('default_profile')
    if not default_profile:
        raise AgentProfileError(
            'default agent profile is not configured',
            code='agent_profile_default_missing',
            details={'path': str(agent_profile_path(root))},
        )
    profile = document['profiles'].get(default_profile)
    if profile is None:
        raise AgentProfileError(
            f'default agent profile not found: {default_profile}',
            code='agent_profile_missing',
            details={'profile': default_profile, 'path': str(agent_profile_path(root))},
        )
    result = _profile_result(root, 'default_shown', profile)
    result['default_profile'] = default_profile
    return result


def clear_default_agent_profile(base: Path | str) -> dict:
    root = Path(base).expanduser().resolve()
    document = _load_document(root)
    default_profile = document.get('default_profile')
    if not default_profile:
        raise AgentProfileError(
            'default agent profile is not configured',
            code='agent_profile_default_missing',
            details={'path': str(agent_profile_path(root))},
        )
    document['default_profile'] = None
    profile = document['profiles'].get(default_profile)
    _write_document(root, document)
    result = _profile_result(root, 'default_cleared', profile)
    result['default_profile'] = None
    result['cleared_default_profile'] = default_profile
    return result


def resolve_agent_profile(base: Path | str, name: str) -> dict:
    if name == DEFAULT_PROFILE_SENTINEL:
        return show_default_agent_profile(base)['profile']
    return show_agent_profile(base, name)['profile']


def resolve_agent_execution(
    base: Path | str,
    *,
    agent_command: str | list[str] | None = None,
    agent_profile: str | None = None,
    producer_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    if agent_command and agent_profile:
        raise AgentProfileError(
            'use either --agent-command or --agent-profile, not both',
            code='agent_profile_ambiguous',
            details={'profile': agent_profile},
        )
    if agent_profile:
        profile = resolve_agent_profile(base, agent_profile)
        return {
            'agent_command': profile['agent_command'],
            'producer_timeout_seconds': float(profile.get('producer_timeout_seconds', producer_timeout_seconds)),
            'source': 'profile',
            'profile': profile['name'],
            'profile_path': str(agent_profile_path(base)),
        }
    if agent_command:
        return {
            'agent_command': agent_command,
            'producer_timeout_seconds': float(producer_timeout_seconds),
            'source': 'command',
            'profile': None,
            'profile_path': None,
        }
    return {
        'agent_command': None,
        'producer_timeout_seconds': float(producer_timeout_seconds),
        'source': None,
        'profile': None,
        'profile_path': None,
    }
