import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from wikify.maintenance.proposal import build_patch_proposal
from wikify.maintenance.task_reader import load_task_queue, select_tasks


SCHEMA_VERSION = 'wikify.patch-bundle-request.v1'
REQUEST_DIR_RELATIVE_PATH = Path('sorted') / 'graph-patch-bundle-requests'
BUNDLE_DIR_RELATIVE_PATH = Path('sorted') / 'graph-patch-bundles'
DEFAULT_MAX_TARGET_CHARS = 4000


class BundleRequestError(ValueError):
    def __init__(self, message: str, code: str = 'bundle_request_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BundleRequestError('bundle request path is empty', code='bundle_request_path_invalid')
    raw = value.strip().replace('\\', '/')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts:
        raise BundleRequestError(
            f'bundle request path must be relative and stay inside the wiki: {value}',
            code='bundle_request_path_invalid',
            details={'path': value},
        )
    return str(path)


def _content_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if root not in (path, *path.parents):
        raise BundleRequestError(
            f'bundle request path must stay inside the wiki: {relative_path}',
            code='bundle_request_path_invalid',
            details={'path': relative_path},
        )
    return path


def _target_snapshot(root: Path, relative_path: str, max_chars: int) -> dict:
    normalized = _normalize_relative_path(relative_path)
    path = _content_path(root, normalized)
    try:
        content = path.read_text(encoding='utf-8')
    except FileNotFoundError as exc:
        raise BundleRequestError(
            f'bundle request target file not found: {normalized}',
            code='bundle_request_target_not_found',
            details={'path': normalized},
        ) from exc
    truncated = len(content) > max_chars
    return {
        'path': normalized,
        'absolute_path': str(path),
        'sha256': _sha256(content),
        'content': content[:max_chars],
        'truncated': truncated,
        'content_length': len(content),
    }


def _task_blocked_feedback(root: Path, task_id: str) -> dict | None:
    try:
        queue = load_task_queue(root)
        selected = select_tasks(queue, task_id=task_id)
    except Exception:
        return None
    feedback = selected['tasks'][0].get('blocked_feedback')
    return feedback if isinstance(feedback, dict) else None


def _latest_block_event_feedback(root: Path, task_id: str) -> dict | None:
    from wikify.maintenance.task_lifecycle import events_path

    path = events_path(root)
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    for event in reversed(document.get('events') or []):
        if event.get('task_id') == task_id and event.get('action') == 'block':
            details = event.get('details')
            return details if isinstance(details, dict) else None
    return None


def _repair_context(root: Path, task_id: str, feedback_override: dict | None = None) -> dict:
    if feedback_override:
        return {
            'available': True,
            'source': 'runner_repair_feedback',
            'feedback': feedback_override,
            'instructions': [
                'Address every verifier finding before writing a replacement patch bundle.',
                'Use the verifier summary and verdict to avoid repeating the rejected change.',
                'Overwrite suggested_bundle_path with a fresh wikify.patch-bundle.v1 artifact.',
            ],
        }

    task_feedback = _task_blocked_feedback(root, task_id)
    if task_feedback:
        return {
            'available': True,
            'source': 'task_blocked_feedback',
            'feedback': task_feedback,
            'instructions': [
                'Address every verifier finding before writing a replacement patch bundle.',
                'Use the verifier summary and verdict to avoid repeating the rejected change.',
                'Overwrite suggested_bundle_path with a fresh wikify.patch-bundle.v1 artifact.',
            ],
        }

    event_feedback = _latest_block_event_feedback(root, task_id)
    if event_feedback:
        return {
            'available': True,
            'source': 'latest_block_event',
            'feedback': event_feedback,
            'instructions': [
                'Address every verifier finding before writing a replacement patch bundle.',
                'Use the verifier summary and verdict to avoid repeating the rejected change.',
                'Overwrite suggested_bundle_path with a fresh wikify.patch-bundle.v1 artifact.',
            ],
        }

    return {
        'available': False,
        'source': None,
        'feedback': None,
        'instructions': [],
    }


def request_path(base: Path | str, task_id: str) -> Path:
    return Path(base).expanduser().resolve() / REQUEST_DIR_RELATIVE_PATH / f'{task_id}.json'


def suggested_bundle_path(base: Path | str, task_id: str) -> Path:
    return Path(base).expanduser().resolve() / BUNDLE_DIR_RELATIVE_PATH / f'{task_id}.json'


def build_bundle_request(
    base: Path | str,
    task_id: str,
    *,
    max_target_chars: int = DEFAULT_MAX_TARGET_CHARS,
    repair_feedback: dict | None = None,
) -> dict:
    root = Path(base).expanduser().resolve()
    proposal = build_patch_proposal(root, task_id)
    write_scope = [_normalize_relative_path(path) for path in proposal.get('write_scope') or []]
    targets = [_target_snapshot(root, path, max_target_chars) for path in write_scope]

    return {
        'schema_version': SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'base': str(root),
        'task_id': proposal.get('task_id'),
        'proposal_path': str(root / 'sorted' / 'graph-patch-proposals' / f'{task_id}.json'),
        'request_path': str(request_path(root, task_id)),
        'suggested_bundle_path': str(suggested_bundle_path(root, task_id)),
        'proposal': proposal,
        'targets': targets,
        'repair_context': _repair_context(root, task_id, repair_feedback),
        'allowed_operations': [
            {
                'operation': 'replace_text',
                'constraints': [
                    'path must be inside proposal.write_scope',
                    'find must be non-empty and match exactly once in the current target file',
                    'replace must be a string and must differ from find',
                    'only one operation per path is supported',
                ],
            }
        ],
        'agent_instructions': [
            'Generate a wikify.patch-bundle.v1 JSON artifact at suggested_bundle_path.',
            'Use only replace_text operations over paths listed in proposal.write_scope.',
            'Choose find text from target snapshots so wikify apply can validate exactly one occurrence.',
            'Do not edit content files directly; write the patch bundle artifact only.',
        ],
        'safety': {
            'content_mutation': False,
            'task_status_mutation': False,
            'hidden_llm_call': False,
        },
        'expected_bundle_schema': {
            'schema_version': 'wikify.patch-bundle.v1',
            'proposal_task_id': proposal.get('task_id'),
            'proposal_path': f'sorted/graph-patch-proposals/{task_id}.json',
            'operations': [
                {
                    'operation': 'replace_text',
                    'path': write_scope[0] if write_scope else '<path>',
                    'find': '<exact current text>',
                    'replace': '<replacement text>',
                    'rationale': '<why this change satisfies the proposal>',
                }
            ],
        },
    }


def write_bundle_request(base: Path | str, request: dict) -> Path:
    task_id = request.get('task_id')
    if not task_id:
        raise BundleRequestError('bundle request is missing task id', code='bundle_request_task_id_missing')
    path = request_path(base, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path
