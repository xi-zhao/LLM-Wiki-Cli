import json
from pathlib import Path


TASK_QUEUE_RELATIVE_PATH = Path('sorted') / 'graph-agent-tasks.json'
SELECTION_SCHEMA_VERSION = 'wikify.agent-task-selection.v1'


class TaskQueueNotFound(FileNotFoundError):
    def __init__(self, path: Path):
        self.path = path
        super().__init__(f'agent task queue not found: {path}')


class TaskNotFound(LookupError):
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f'agent task not found: {task_id}')


def task_queue_path(base: Path | str) -> Path:
    return Path(base).expanduser().resolve() / TASK_QUEUE_RELATIVE_PATH


def load_task_queue(base: Path | str) -> dict:
    path = task_queue_path(base)
    if not path.exists():
        raise TaskQueueNotFound(path)
    return json.loads(path.read_text(encoding='utf-8'))


def select_tasks(
    queue: dict,
    status: str | None = None,
    action: str | None = None,
    task_id: str | None = None,
    limit: int | None = None,
) -> dict:
    if limit is not None and limit < 0:
        raise ValueError('limit must be non-negative')

    tasks = list(queue.get('tasks', []))
    total_task_count = len(tasks)

    if task_id:
        tasks = [task for task in tasks if task.get('id') == task_id]
        if not tasks:
            raise TaskNotFound(task_id)

    if status:
        tasks = [task for task in tasks if task.get('status') == status]

    if action:
        tasks = [task for task in tasks if task.get('action') == action]

    if limit is not None:
        tasks = tasks[:limit]

    return {
        'schema_version': SELECTION_SCHEMA_VERSION,
        'source_schema_version': queue.get('schema_version'),
        'summary': {
            'task_count': len(tasks),
            'total_task_count': total_task_count,
        },
        'tasks': tasks,
    }
