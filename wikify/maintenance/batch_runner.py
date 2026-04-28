from pathlib import Path

from wikify.maintenance.bundle_producer import DEFAULT_TIMEOUT_SECONDS
from wikify.maintenance.task_reader import (
    TaskNotFound,
    TaskQueueNotFound,
    load_task_queue,
    select_tasks,
    task_queue_path,
)
from wikify.maintenance.task_runner import TaskRunError, run_agent_task


SCHEMA_VERSION = 'wikify.agent-task-batch-run.v1'
DEFAULT_STATUS = 'queued'
DEFAULT_LIMIT = 5


class BatchTaskRunError(ValueError):
    def __init__(self, message: str, code: str = 'agent_task_batch_run_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _wrap_selection_error(exc: Exception) -> BatchTaskRunError:
    if isinstance(exc, TaskQueueNotFound):
        return BatchTaskRunError(
            'agent task queue not found',
            code='agent_task_queue_missing',
            details={'path': str(exc.path)},
        )
    if isinstance(exc, TaskNotFound):
        return BatchTaskRunError(
            'agent task not found',
            code='agent_task_not_found',
            details={'id': exc.task_id},
        )
    return BatchTaskRunError(str(exc), details={})


def _base_result(
    root: Path,
    *,
    status: str | None,
    action: str | None,
    task_id: str | None,
    limit: int | None,
    dry_run: bool,
    continue_on_error: bool,
) -> dict:
    return {
        'schema_version': SCHEMA_VERSION,
        'base': str(root),
        'dry_run': dry_run,
        'status': 'running',
        'selection': {
            'status': status,
            'action': action,
            'id': task_id,
            'limit': limit,
        },
        'execution': {
            'mode': 'sequential',
            'continue_on_error': continue_on_error,
            'stop_on_error': not continue_on_error,
        },
        'artifacts': {
            'agent_tasks': str(task_queue_path(root)),
        },
        'items': [],
        'summary': {
            'selected_count': 0,
            'completed_count': 0,
            'waiting_count': 0,
            'failed_count': 0,
            'stopped': False,
        },
        'next_actions': [],
    }


def _success_item(task_id: str, result: dict) -> dict:
    return {
        'task_id': task_id,
        'ok': True,
        'status': result.get('status'),
        'result': result,
    }


def _error_item(task_id: str, exc: TaskRunError) -> dict:
    return {
        'task_id': task_id,
        'ok': False,
        'status': 'failed',
        'error': {
            'code': exc.code,
            'message': str(exc),
            'details': exc.details,
        },
    }


def _final_status(result: dict) -> str:
    summary = result['summary']
    if summary['selected_count'] == 0:
        return 'no_tasks'
    if result['dry_run']:
        return 'dry_run'
    if summary['failed_count']:
        return 'completed_with_errors' if not summary['stopped'] else 'stopped_on_error'
    if summary['waiting_count']:
        return 'waiting_for_patch_bundle'
    return 'completed'


def run_agent_tasks(
    base: Path | str,
    *,
    status: str | None = DEFAULT_STATUS,
    action: str | None = None,
    task_id: str | None = None,
    limit: int | None = DEFAULT_LIMIT,
    dry_run: bool = False,
    agent_command: str | list[str] | None = None,
    producer_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    continue_on_error: bool = False,
) -> dict:
    root = Path(base).expanduser().resolve()
    result = _base_result(
        root,
        status=status,
        action=action,
        task_id=task_id,
        limit=limit,
        dry_run=dry_run,
        continue_on_error=continue_on_error,
    )
    try:
        queue = load_task_queue(root)
        selection = select_tasks(queue, status=status, action=action, task_id=task_id, limit=limit)
    except (TaskQueueNotFound, TaskNotFound, ValueError) as exc:
        raise _wrap_selection_error(exc) from exc

    tasks = selection.get('tasks', [])
    result['summary']['selected_count'] = len(tasks)
    result['selection']['source_schema_version'] = selection.get('source_schema_version')
    result['selection']['total_task_count'] = selection.get('summary', {}).get('total_task_count')

    for task in tasks:
        selected_task_id = task.get('id')
        try:
            task_result = run_agent_task(
                root,
                selected_task_id,
                dry_run=dry_run,
                agent_command=agent_command,
                producer_timeout_seconds=producer_timeout_seconds,
            )
        except TaskRunError as exc:
            result['items'].append(_error_item(selected_task_id, exc))
            result['summary']['failed_count'] += 1
            if not continue_on_error:
                result['summary']['stopped'] = True
                break
            continue

        result['items'].append(_success_item(selected_task_id, task_result))
        if task_result.get('status') == 'completed':
            result['summary']['completed_count'] += 1
        elif task_result.get('status') == 'waiting_for_patch_bundle':
            result['summary']['waiting_count'] += 1

    result['status'] = _final_status(result)
    if result['summary']['waiting_count']:
        result['next_actions'].append('generate_patch_bundle')
    if result['summary']['failed_count']:
        result['next_actions'].append('inspect_failed_tasks')
    return result
