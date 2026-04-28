import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from wikify.maintenance.task_reader import load_task_queue, select_tasks


SCHEMA_VERSION = 'wikify.patch-proposal.v1'
PROPOSAL_DIR_RELATIVE_PATH = Path('sorted') / 'graph-patch-proposals'


class ProposalError(ValueError):
    def __init__(self, message: str, code: str = 'proposal_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


class OutOfScopeProposal(ProposalError):
    def __init__(self, path: str, write_scope: list[str]):
        self.path = path
        self.write_scope = write_scope
        super().__init__(
            f'proposal path is outside task write scope: {path}',
            code='proposal_out_of_scope',
            details={'path': path, 'write_scope': write_scope},
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProposalError('proposal path is empty', code='proposal_path_invalid')

    raw = value.strip().replace('\\', '/')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts:
        raise ProposalError(
            f'proposal path must be relative and stay inside the wiki: {value}',
            code='proposal_path_invalid',
            details={'path': value},
        )
    return str(path)


def _normalize_write_scope(task: dict) -> list[str]:
    write_scope = task.get('write_scope') or []
    if not isinstance(write_scope, list) or not write_scope:
        raise ProposalError(
            'agent task is missing write scope',
            code='proposal_write_scope_missing',
            details={'task_id': task.get('id')},
        )
    return [_normalize_relative_path(path) for path in write_scope]


def _planned_path(task: dict, write_scope: list[str]) -> str:
    evidence = task.get('evidence') or {}
    candidates = [
        evidence.get('source'),
        task.get('target'),
        write_scope[0],
    ]
    for candidate in candidates:
        if candidate:
            return _normalize_relative_path(candidate)
    return write_scope[0]


def _validate_paths(paths: list[str], write_scope: list[str]):
    allowed = set(write_scope)
    for path in paths:
        if path not in allowed:
            raise OutOfScopeProposal(path, write_scope)


def _risk_for_task(task: dict) -> str:
    if task.get('requires_user'):
        return 'high'
    if task.get('priority') == 'high':
        return 'medium'
    return 'low'


def build_patch_proposal(base: Path | str, task_id: str) -> dict:
    queue = load_task_queue(base)
    selected = select_tasks(queue, task_id=task_id)
    task = selected['tasks'][0]
    write_scope = _normalize_write_scope(task)
    path = _planned_path(task, write_scope)
    _validate_paths([path], write_scope)

    planned_edit = {
        'operation': 'propose_content_patch',
        'path': path,
        'action': task.get('action'),
        'instructions': list(task.get('agent_instructions') or []),
        'evidence': dict(task.get('evidence') or {}),
        'status': 'planned',
    }

    return {
        'schema_version': SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'task_id': task.get('id'),
        'source_finding_id': task.get('source_finding_id'),
        'source_step_id': task.get('source_step_id'),
        'action': task.get('action'),
        'target': task.get('target'),
        'write_scope': write_scope,
        'planned_edits': [planned_edit],
        'acceptance_checks': list(task.get('acceptance_checks') or []),
        'risk': _risk_for_task(task),
        'preflight': {
            'write_scope_valid': True,
            'proposed_path_count': 1,
            'content_mutation': False,
            'task_status_mutation': False,
        },
    }


def proposal_path(base: Path | str, task_id: str) -> Path:
    return Path(base).expanduser().resolve() / PROPOSAL_DIR_RELATIVE_PATH / f'{task_id}.json'


def write_patch_proposal(base: Path | str, proposal: dict) -> Path:
    task_id = proposal.get('task_id')
    if not task_id:
        raise ProposalError('proposal is missing task id', code='proposal_task_id_missing')
    path = proposal_path(base, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path
