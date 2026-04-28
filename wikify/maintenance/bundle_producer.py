import json
import os
import shlex
import subprocess
from pathlib import Path

from wikify.maintenance.patch_apply import PatchApplyError, preflight_patch_bundle


SCHEMA_VERSION = 'wikify.patch-bundle-production.v1'
REQUEST_SCHEMA_VERSION = 'wikify.patch-bundle-request.v1'
DEFAULT_TIMEOUT_SECONDS = 120.0
MAX_CAPTURE_CHARS = 4000


class BundleProducerError(ValueError):
    def __init__(self, message: str, code: str = 'bundle_producer_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _truncate(text: str) -> str:
    if len(text) <= MAX_CAPTURE_CHARS:
        return text
    return text[:MAX_CAPTURE_CHARS] + '...'


def _load_request(root: Path, request_path: Path | str) -> tuple[Path, dict]:
    path = Path(request_path).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        request = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise BundleProducerError(
            f'patch bundle request not found: {path}',
            code='bundle_producer_request_not_found',
            details={'path': str(path)},
        ) from exc
    except json.JSONDecodeError as exc:
        raise BundleProducerError(
            f'patch bundle request is not valid JSON: {path}',
            code='bundle_producer_request_invalid_json',
            details={'path': str(path)},
        ) from exc
    if request.get('schema_version') != REQUEST_SCHEMA_VERSION:
        raise BundleProducerError(
            'patch bundle request schema is not supported',
            code='bundle_producer_request_schema_invalid',
            details={'schema_version': request.get('schema_version')},
        )
    return path, request


def _command_args(agent_command: str | list[str]) -> list[str]:
    if isinstance(agent_command, str):
        args = shlex.split(agent_command)
    else:
        args = list(agent_command)
    if not args:
        raise BundleProducerError('agent command is empty', code='bundle_producer_command_invalid')
    return args


def _path_from_request(root: Path, request: dict, key: str, code: str) -> Path:
    value = request.get(key)
    if not isinstance(value, str) or not value:
        raise BundleProducerError(f'patch bundle request is missing {key}', code=code)
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _base_result(root: Path, request_path: Path, request: dict, args: list[str], dry_run: bool) -> dict:
    bundle_path = _path_from_request(root, request, 'suggested_bundle_path', 'bundle_producer_bundle_path_missing')
    return {
        'schema_version': SCHEMA_VERSION,
        'base': str(root),
        'dry_run': dry_run,
        'executed': False,
        'status': 'running',
        'request_path': str(request_path),
        'suggested_bundle_path': str(bundle_path),
        'task_id': request.get('task_id'),
        'agent_command': args,
        'invocation': {
            'stdin': 'wikify.patch-bundle-request.v1 JSON',
            'env': {
                'WIKIFY_BASE': str(root),
                'WIKIFY_PATCH_BUNDLE_REQUEST': str(request_path),
                'WIKIFY_PATCH_BUNDLE': str(bundle_path),
            },
            'shell': False,
        },
        'artifacts': {
            'patch_bundle': None,
        },
        'summary': {
            'task_id': request.get('task_id'),
            'suggested_bundle_path': str(bundle_path),
        },
    }


def _write_stdout_bundle(bundle_path: Path, stdout: str):
    try:
        bundle = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise BundleProducerError(
            'agent command stdout is not valid patch bundle JSON',
            code='bundle_producer_invalid_output',
            details={'stdout': _truncate(stdout)},
        ) from exc
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def produce_patch_bundle(
    base: Path | str,
    request_path: Path | str,
    agent_command: str | list[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    dry_run: bool = False,
) -> dict:
    root = Path(base).expanduser().resolve()
    resolved_request_path, request = _load_request(root, request_path)
    args = _command_args(agent_command)
    result = _base_result(root, resolved_request_path, request, args, dry_run)
    bundle_path = Path(result['suggested_bundle_path'])

    if dry_run:
        result['status'] = 'dry_run'
        return result

    env = dict(os.environ)
    env.update(result['invocation']['env'])
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
        raise BundleProducerError(
            f'agent command timed out after {timeout_seconds} seconds',
            code='bundle_producer_timeout',
            details={'timeout_seconds': timeout_seconds},
        ) from exc

    result['executed'] = True
    result['command'] = {
        'returncode': completed.returncode,
        'stdout': _truncate(completed.stdout),
        'stderr': _truncate(completed.stderr),
    }
    if completed.returncode != 0:
        raise BundleProducerError(
            f'agent command failed with exit code {completed.returncode}',
            code='bundle_producer_command_failed',
            details=result['command'],
        )

    stdout = completed.stdout.strip()
    output_mode = 'file'
    if stdout:
        _write_stdout_bundle(bundle_path, stdout)
        output_mode = 'stdout'
    elif not bundle_path.exists():
        raise BundleProducerError(
            'agent command produced no stdout bundle and did not write the suggested bundle path',
            code='bundle_producer_no_bundle_output',
            details={'suggested_bundle_path': str(bundle_path)},
        )

    try:
        preflight = preflight_patch_bundle(root, request.get('proposal_path'), bundle_path)
    except PatchApplyError as exc:
        details = dict(exc.details or {})
        details['phase'] = 'preflight'
        raise BundleProducerError(str(exc), code=exc.code, details=details) from exc

    result['status'] = 'bundle_ready'
    result['output_mode'] = output_mode
    result['artifacts']['patch_bundle'] = str(bundle_path)
    result['preflight'] = preflight
    result['summary']['operation_count'] = preflight.get('summary', {}).get('operation_count')
    result['summary']['affected_paths'] = preflight.get('summary', {}).get('affected_paths')
    return result
