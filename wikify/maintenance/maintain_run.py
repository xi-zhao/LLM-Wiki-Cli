from pathlib import Path

from wikify.maintenance.batch_runner import (
    DEFAULT_LIMIT,
    DEFAULT_STATUS,
    SCHEMA_VERSION as BATCH_SCHEMA_VERSION,
    BatchTaskRunError,
    run_agent_tasks,
)
from wikify.maintenance.bundle_producer import DEFAULT_TIMEOUT_SECONDS
from wikify.maintenance.runner import run_maintenance
from wikify.maintenance.task_reader import select_tasks, task_queue_path


SCHEMA_VERSION = 'wikify.maintenance-run.v1'
DEFAULT_POLICY = 'balanced'


class MaintenanceRunError(ValueError):
    def __init__(self, message: str, code: str = 'maintenance_run_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _with_phase(details: dict | None, phase: str) -> dict:
    enriched = dict(details or {})
    enriched['phase'] = phase
    return enriched


def _status_from_batch(batch: dict, dry_run: bool) -> str:
    if dry_run:
        return 'dry_run'
    status = batch.get('status')
    if status == 'no_tasks':
        return 'maintenance_completed_no_tasks'
    return status or 'completed'


def _preview_batch(
    root: Path,
    queue: dict,
    *,
    status: str | None,
    action: str | None,
    task_id: str | None,
    limit: int | None,
    continue_on_error: bool,
) -> dict:
    selection = select_tasks(queue, status=status, action=action, task_id=task_id, limit=limit)
    tasks = selection.get('tasks', [])
    return {
        'schema_version': BATCH_SCHEMA_VERSION,
        'base': str(root),
        'dry_run': True,
        'status': 'dry_run' if tasks else 'no_tasks',
        'selection': {
            'status': status,
            'action': action,
            'id': task_id,
            'limit': limit,
            'source_schema_version': selection.get('source_schema_version'),
            'total_task_count': selection.get('summary', {}).get('total_task_count'),
        },
        'execution': {
            'mode': 'sequential',
            'continue_on_error': continue_on_error,
            'stop_on_error': not continue_on_error,
        },
        'artifacts': {
            'agent_tasks': None,
        },
        'items': [
            {
                'task_id': task.get('id'),
                'ok': True,
                'status': 'preview',
                'task': task,
            }
            for task in tasks
        ],
        'summary': {
            'selected_count': len(tasks),
            'completed_count': 0,
            'waiting_count': 0,
            'failed_count': 0,
            'stopped': False,
        },
        'next_actions': ['wikify maintain-run'],
    }


def _summary(maintenance: dict, batch: dict) -> dict:
    maintenance_summary = maintenance.get('summary', {})
    batch_summary = batch.get('summary', {})
    return {
        'finding_count': maintenance_summary.get('finding_count', 0),
        'planned_count': maintenance_summary.get('planned_count', 0),
        'maintenance_task_count': maintenance_summary.get('task_count', 0),
        'selected_count': batch_summary.get('selected_count', 0),
        'completed_count': batch_summary.get('completed_count', 0),
        'waiting_count': batch_summary.get('waiting_count', 0),
        'failed_count': batch_summary.get('failed_count', 0),
        'stopped': batch_summary.get('stopped', False),
    }


def _artifacts(maintenance: dict, batch: dict) -> dict:
    return {
        'maintenance': maintenance.get('artifacts', {}),
        'batch': batch.get('artifacts', {}),
        'agent_tasks': str(task_queue_path(maintenance['base'])) if not maintenance.get('dry_run') else None,
    }


def run_maintenance_workflow(
    base: Path | str,
    *,
    policy: str = DEFAULT_POLICY,
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
    try:
        maintenance = run_maintenance(root, policy=policy, dry_run=dry_run)
    except Exception as exc:
        raise MaintenanceRunError(
            str(exc),
            code='maintenance_refresh_failed',
            details=_with_phase({}, 'maintenance'),
        ) from exc

    if dry_run:
        try:
            batch = _preview_batch(
                root,
                maintenance['task_queue'],
                status=status,
                action=action,
                task_id=task_id,
                limit=limit,
                continue_on_error=continue_on_error,
            )
        except Exception as exc:
            raise MaintenanceRunError(
                str(exc),
                code='maintenance_run_preview_failed',
                details=_with_phase({}, 'batch_preview'),
            ) from exc
    else:
        try:
            batch = run_agent_tasks(
                root,
                status=status,
                action=action,
                task_id=task_id,
                limit=limit,
                dry_run=False,
                agent_command=agent_command,
                producer_timeout_seconds=producer_timeout_seconds,
                continue_on_error=continue_on_error,
            )
        except BatchTaskRunError as exc:
            raise MaintenanceRunError(
                str(exc),
                code=exc.code,
                details=_with_phase(exc.details, 'batch_execution'),
            ) from exc

    next_actions = list(batch.get('next_actions', []))
    if dry_run:
        next_actions = ['wikify maintain-run']

    return {
        'schema_version': SCHEMA_VERSION,
        'base': str(root),
        'policy': policy,
        'dry_run': dry_run,
        'status': _status_from_batch(batch, dry_run),
        'selection': {
            'status': status,
            'action': action,
            'id': task_id,
            'limit': limit,
        },
        'execution': {
            'mode': 'maintenance_then_batch',
            'continue_on_error': continue_on_error,
            'stop_on_error': not continue_on_error,
            'agent_command_explicit': agent_command is not None,
        },
        'artifacts': _artifacts(maintenance, batch),
        'maintenance': {
            'summary': maintenance.get('summary', {}),
            'artifacts': maintenance.get('artifacts', {}),
            'graph': maintenance.get('graph', {}),
            'completion': maintenance.get('completion', {}),
        },
        'batch': batch,
        'summary': _summary(maintenance, batch),
        'next_actions': next_actions,
    }
