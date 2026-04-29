import json
from datetime import datetime, timezone
from pathlib import Path

from wikify.maintenance.task_reader import load_task_queue, task_queue_path


LIFECYCLE_SCHEMA_VERSION = 'wikify.agent-task-lifecycle.v1'
EVENTS_SCHEMA_VERSION = 'wikify.graph-agent-task-events.v1'
EVENTS_RELATIVE_PATH = Path('sorted') / 'graph-agent-task-events.json'


ACTION_TARGET_STATUS = {
    'mark_proposed': 'proposed',
    'start': 'in_progress',
    'mark_done': 'done',
    'mark_failed': 'failed',
    'block': 'blocked',
    'cancel': 'rejected',
    'retry': 'queued',
    'restore': 'queued',
}


ALLOWED_TRANSITIONS = {
    'queued': {'proposed', 'in_progress', 'blocked', 'rejected'},
    'proposed': {'in_progress', 'done', 'failed', 'blocked', 'rejected'},
    'in_progress': {'done', 'failed', 'blocked', 'rejected'},
    'failed': {'queued', 'blocked', 'rejected'},
    'blocked': {'queued', 'rejected'},
    'rejected': {'queued'},
    'done': set(),
}


class TaskLifecycleError(ValueError):
    def __init__(self, message: str, code: str = 'task_lifecycle_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


class InvalidTaskTransition(TaskLifecycleError):
    def __init__(self, task_id: str, action: str, from_status: str, to_status: str):
        self.task_id = task_id
        self.action = action
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f'invalid task transition: {from_status} -> {to_status}',
            code='invalid_agent_task_transition',
            details={
                'id': task_id,
                'action': action,
                'from_status': from_status,
                'to_status': to_status,
            },
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def events_path(base: Path | str) -> Path:
    return Path(base).expanduser().resolve() / EVENTS_RELATIVE_PATH


def _load_events(base: Path | str) -> dict:
    path = events_path(base)
    if not path.exists():
        return {
            'schema_version': EVENTS_SCHEMA_VERSION,
            'events': [],
        }
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _find_task(queue: dict, task_id: str) -> dict:
    for task in queue.get('tasks', []):
        if task.get('id') == task_id:
            return task
    from wikify.maintenance.task_reader import TaskNotFound

    raise TaskNotFound(task_id)


def _event_id(events: list[dict]) -> str:
    return f'event-{len(events) + 1}'


def _validate_action(action: str) -> str:
    if action not in ACTION_TARGET_STATUS:
        raise TaskLifecycleError(
            f'unknown lifecycle action: {action}',
            code='unknown_agent_task_lifecycle_action',
            details={'action': action},
        )
    return ACTION_TARGET_STATUS[action]


def apply_lifecycle_action(
    base: Path | str,
    task_id: str,
    action: str,
    note: str | None = None,
    proposal_path: str | None = None,
    details: dict | None = None,
) -> dict:
    root = Path(base).expanduser().resolve()
    queue = load_task_queue(root)
    task = _find_task(queue, task_id)
    from_status = task.get('status') or 'queued'
    to_status = _validate_action(action)

    if to_status not in ALLOWED_TRANSITIONS.get(from_status, set()):
        raise InvalidTaskTransition(task_id, action, from_status, to_status)

    now = _utc_now()
    task['status'] = to_status
    task['updated_at'] = now
    task['status_changed_at'] = now

    if action == 'mark_proposed' and proposal_path:
        task['proposal_path'] = proposal_path
    if action == 'retry':
        task['attempts'] = int(task.get('attempts') or 0) + 1
    if action == 'block' and details is not None:
        task['blocked_feedback'] = details
    if action in {'retry', 'restore'}:
        task.pop('blocked_feedback', None)

    events_document = _load_events(root)
    events = events_document.setdefault('events', [])
    event = {
        'id': _event_id(events),
        'task_id': task_id,
        'action': action,
        'from_status': from_status,
        'to_status': to_status,
        'created_at': now,
    }
    if note:
        event['note'] = note
    if proposal_path:
        event['proposal_path'] = proposal_path
    if details is not None:
        event['details'] = details
    events.append(event)

    queue.setdefault('summary', {})['task_count'] = len(queue.get('tasks', []))
    _write_json(task_queue_path(root), queue)
    _write_json(events_path(root), events_document)

    return {
        'schema_version': LIFECYCLE_SCHEMA_VERSION,
        'base': str(root),
        'task': dict(task),
        'event': event,
        'artifacts': {
            'agent_tasks': str(task_queue_path(root)),
            'task_events': str(events_path(root)),
        },
        'summary': {
            'task_id': task_id,
            'action': action,
            'from_status': from_status,
            'to_status': to_status,
        },
    }
