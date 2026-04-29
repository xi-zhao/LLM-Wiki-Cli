import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from wikify.maintenance.bundle_producer import DEFAULT_TIMEOUT_SECONDS
from wikify.maintenance.patch_apply import PatchApplyError, preflight_patch_bundle


SCHEMA_VERSION = 'wikify.patch-bundle-verification.v1'
REQUEST_SCHEMA_VERSION = 'wikify.patch-bundle-verification-request.v1'
VERDICT_SCHEMA_VERSION = 'wikify.patch-bundle-verdict.v1'
VERIFICATIONS_RELATIVE_PATH = Path('sorted') / 'graph-patch-verifications'
MAX_CAPTURE_CHARS = 4000


class BundleVerifierError(ValueError):
    def __init__(self, message: str, code: str = 'bundle_verifier_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _truncate(text: str) -> str:
    if len(text) <= MAX_CAPTURE_CHARS:
        return text
    return text[:MAX_CAPTURE_CHARS] + '...'


def _command_args(verifier_command: str | list[str]) -> list[str]:
    if isinstance(verifier_command, str):
        args = shlex.split(verifier_command)
    else:
        args = list(verifier_command)
    if not args:
        raise BundleVerifierError('verifier command is empty', code='bundle_verifier_command_invalid')
    return args


def _load_json(path: Path, code: str) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise BundleVerifierError(f'patch artifact not found: {path}', code=code, details={'path': str(path)}) from exc
    except json.JSONDecodeError as exc:
        raise BundleVerifierError(
            f'patch artifact is not valid JSON: {path}',
            code='bundle_verifier_artifact_invalid_json',
            details={'path': str(path)},
        ) from exc


def _resolve_existing_path(base: Path, value: Path | str, code: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.exists():
        raise BundleVerifierError(f'patch artifact not found: {path}', code=code, details={'path': str(path)})
    return path


def verification_path(base: Path | str, task_id: str) -> Path:
    return Path(base).expanduser().resolve() / VERIFICATIONS_RELATIVE_PATH / f'{task_id}.json'


def _build_request(root: Path, proposal_path: Path, bundle_path: Path, proposal: dict, bundle: dict, preflight: dict) -> dict:
    return {
        'schema_version': REQUEST_SCHEMA_VERSION,
        'base': str(root),
        'task_id': proposal.get('task_id'),
        'proposal_path': str(proposal_path),
        'bundle_path': str(bundle_path),
        'proposal': proposal,
        'bundle': bundle,
        'preservation': proposal.get('preservation'),
        'preflight': preflight,
        'instructions': [
            'Review whether the patch bundle should be applied.',
            'Reject if the bundle does not satisfy task instructions, evidence, or acceptance checks.',
            'Reject if the replacement is semantically risky even when deterministic preflight passes.',
            'Return only wikify.patch-bundle-verdict.v1 JSON on stdout.',
        ],
        'response_schema': {
            'schema_version': VERDICT_SCHEMA_VERSION,
            'accepted': True,
            'summary': 'short rationale',
            'findings': [],
        },
    }


def _parse_verdict(stdout: str) -> dict:
    try:
        verdict = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise BundleVerifierError(
            'verifier command stdout is not valid verdict JSON',
            code='bundle_verifier_invalid_output',
            details={'stdout': _truncate(stdout)},
        ) from exc
    if verdict.get('schema_version') != VERDICT_SCHEMA_VERSION:
        raise BundleVerifierError(
            'verifier verdict schema is not supported',
            code='bundle_verifier_verdict_schema_invalid',
            details={'schema_version': verdict.get('schema_version')},
        )
    if not isinstance(verdict.get('accepted'), bool):
        raise BundleVerifierError(
            'verifier verdict must include boolean accepted',
            code='bundle_verifier_verdict_invalid',
        )
    verdict.setdefault('findings', [])
    verdict.setdefault('summary', '')
    return verdict


def _write_verification(path: Path, result: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def verify_patch_bundle(
    base: Path | str,
    proposal_path: Path | str,
    bundle_path: Path | str,
    verifier_command: str | list[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    dry_run: bool = False,
) -> dict:
    root = Path(base).expanduser().resolve()
    resolved_proposal = _resolve_existing_path(root, proposal_path, 'bundle_verifier_proposal_not_found')
    resolved_bundle = _resolve_existing_path(root, bundle_path, 'bundle_verifier_bundle_not_found')
    args = _command_args(verifier_command)

    try:
        preflight = preflight_patch_bundle(root, resolved_proposal, resolved_bundle)
    except PatchApplyError as exc:
        details = dict(exc.details or {})
        details['phase'] = 'preflight'
        raise BundleVerifierError(str(exc), code=exc.code, details=details) from exc

    proposal = _load_json(resolved_proposal, 'bundle_verifier_proposal_not_found')
    bundle = _load_json(resolved_bundle, 'bundle_verifier_bundle_not_found')
    request = _build_request(root, resolved_proposal, resolved_bundle, proposal, bundle, preflight)
    task_id = request.get('task_id')
    artifact_path = verification_path(root, task_id)
    result = {
        'schema_version': SCHEMA_VERSION,
        'base': str(root),
        'created_at': _utc_now(),
        'dry_run': dry_run,
        'executed': False,
        'status': 'running',
        'task_id': task_id,
        'proposal_path': str(resolved_proposal),
        'bundle_path': str(resolved_bundle),
        'verifier_command': args,
        'invocation': {
            'stdin': REQUEST_SCHEMA_VERSION,
            'env': {
                'WIKIFY_BASE': str(root),
                'WIKIFY_PATCH_PROPOSAL': str(resolved_proposal),
                'WIKIFY_PATCH_BUNDLE': str(resolved_bundle),
                'WIKIFY_PATCH_BUNDLE_VERIFICATION': str(artifact_path),
            },
            'shell': False,
        },
        'request': request,
        'preflight': preflight,
        'verdict': None,
        'artifacts': {
            'verification': None,
        },
        'summary': {
            'task_id': task_id,
            'accepted': None,
            'verification_path': str(artifact_path),
        },
    }
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
        raise BundleVerifierError(
            f'verifier command timed out after {timeout_seconds} seconds',
            code='bundle_verifier_timeout',
            details={'timeout_seconds': timeout_seconds},
        ) from exc

    result['executed'] = True
    result['command'] = {
        'returncode': completed.returncode,
        'stdout': _truncate(completed.stdout),
        'stderr': _truncate(completed.stderr),
    }
    if completed.returncode != 0:
        raise BundleVerifierError(
            f'verifier command failed with exit code {completed.returncode}',
            code='bundle_verifier_command_failed',
            details=result['command'],
        )

    verdict = _parse_verdict(completed.stdout.strip())
    accepted = verdict['accepted']
    result['verdict'] = verdict
    result['status'] = 'accepted' if accepted else 'rejected'
    result['artifacts']['verification'] = str(artifact_path)
    result['summary']['accepted'] = accepted
    _write_verification(artifact_path, result)

    if not accepted:
        raise BundleVerifierError(
            'patch bundle rejected by verifier',
            code='patch_bundle_verification_rejected',
            details={
                'task_id': task_id,
                'verification_path': str(artifact_path),
                'verdict': verdict,
            },
        )
    return result
