from pathlib import Path

from wikify.maintenance.batch_runner import DEFAULT_LIMIT, DEFAULT_STATUS
from wikify.maintenance.bundle_producer import DEFAULT_TIMEOUT_SECONDS
from wikify.maintenance.maintain_run import (
    DEFAULT_POLICY,
    MaintenanceRunError,
    run_maintenance_workflow,
)


SCHEMA_VERSION = 'wikify.maintenance-loop.v1'
DEFAULT_MAX_ROUNDS = 3
DEFAULT_TASK_BUDGET = 15


class MaintenanceLoopError(ValueError):
    def __init__(self, message: str, code: str = 'maintenance_loop_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _validate_positive(value: int | None, field: str):
    if value is None:
        return
    if not isinstance(value, int) or value < 1:
        raise MaintenanceLoopError(
            f'{field} must be a positive integer',
            code='maintenance_loop_invalid_bounds',
            details={'field': field, 'value': value},
        )


def _summary_base() -> dict:
    return {
        'round_count': 0,
        'selected_count': 0,
        'completed_count': 0,
        'waiting_count': 0,
        'failed_count': 0,
        'stopped': False,
    }


def _add_round_summary(summary: dict, round_result: dict):
    round_summary = round_result.get('summary', {})
    summary['round_count'] += 1
    summary['selected_count'] += round_summary.get('selected_count', 0)
    summary['completed_count'] += round_summary.get('completed_count', 0)
    summary['waiting_count'] += round_summary.get('waiting_count', 0)
    summary['failed_count'] += round_summary.get('failed_count', 0)


def _round_entry(round_number: int, limit: int, result: dict) -> dict:
    return {
        'round': round_number,
        'limit': limit,
        'status': result.get('status'),
        'summary': result.get('summary', {}),
        'artifacts': result.get('artifacts', {}),
        'next_actions': result.get('next_actions', []),
        'result': result,
    }


def _stop_reason_for_round(
    result: dict,
    *,
    dry_run: bool,
    remaining_budget: int,
    round_number: int,
    max_rounds: int,
) -> str | None:
    summary = result.get('summary', {})
    selected_count = summary.get('selected_count', 0)
    if dry_run:
        return 'dry_run_preview'
    if result.get('status') == 'maintenance_completed_no_tasks' or selected_count == 0:
        return 'no_tasks'
    if summary.get('failed_count', 0):
        return 'failed_tasks'
    if summary.get('waiting_count', 0) or result.get('status') == 'waiting_for_patch_bundle':
        return 'waiting_for_patch_bundle'
    if remaining_budget <= 0:
        return 'task_budget_exhausted'
    if round_number >= max_rounds:
        return 'max_rounds_reached'
    return None


def _status_from_stop_reason(stop_reason: str | None, last_round: dict | None) -> str:
    if stop_reason == 'no_tasks':
        return 'completed'
    if stop_reason == 'dry_run_preview':
        return 'dry_run'
    if stop_reason == 'failed_tasks':
        return (last_round or {}).get('status') or 'completed_with_errors'
    if stop_reason in {'waiting_for_patch_bundle', 'task_budget_exhausted', 'max_rounds_reached'}:
        return stop_reason
    return (last_round or {}).get('status') or 'completed'


def _collect_paths(value, paths: list[str]):
    if isinstance(value, dict):
        for item in value.values():
            _collect_paths(item, paths)
    elif isinstance(value, list):
        for item in value:
            _collect_paths(item, paths)
    elif value:
        path = str(value)
        if path not in paths:
            paths.append(path)


def _artifacts(rounds: list[dict]) -> dict:
    paths: list[str] = []
    for round_result in rounds:
        _collect_paths(round_result.get('artifacts', {}), paths)
    return {
        'last_round': rounds[-1].get('artifacts', {}) if rounds else {},
        'paths': paths,
    }


def _next_actions(stop_reason: str | None, last_round: dict | None) -> list[str]:
    if stop_reason == 'no_tasks':
        return []
    if stop_reason in {'dry_run_preview', 'task_budget_exhausted', 'max_rounds_reached'}:
        return ['wikify maintain-loop']
    return list((last_round or {}).get('next_actions', []))


def run_maintenance_loop(
    base: Path | str,
    *,
    policy: str = DEFAULT_POLICY,
    status: str | None = DEFAULT_STATUS,
    action: str | None = None,
    task_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    task_budget: int = DEFAULT_TASK_BUDGET,
    dry_run: bool = False,
    agent_command: str | list[str] | None = None,
    producer_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    continue_on_error: bool = False,
) -> dict:
    _validate_positive(limit, 'limit')
    _validate_positive(max_rounds, 'max_rounds')
    _validate_positive(task_budget, 'task_budget')

    root = Path(base).expanduser().resolve()
    remaining_budget = task_budget
    rounds: list[dict] = []
    summary = _summary_base()
    stop_reason: str | None = None

    for round_number in range(1, max_rounds + 1):
        round_limit = min(limit, remaining_budget)
        try:
            round_result = run_maintenance_workflow(
                root,
                policy=policy,
                status=status,
                action=action,
                task_id=task_id,
                limit=round_limit,
                dry_run=dry_run,
                agent_command=agent_command,
                producer_timeout_seconds=producer_timeout_seconds,
                continue_on_error=continue_on_error,
            )
        except MaintenanceRunError as exc:
            details = dict(exc.details)
            details['round'] = round_number
            details['phase'] = details.get('phase', 'maintenance_run')
            raise MaintenanceLoopError(str(exc), code=exc.code, details=details) from exc

        selected_count = round_result.get('summary', {}).get('selected_count', 0)
        remaining_budget -= selected_count
        entry = _round_entry(round_number, round_limit, round_result)
        rounds.append(entry)
        _add_round_summary(summary, round_result)

        stop_reason = _stop_reason_for_round(
            round_result,
            dry_run=dry_run,
            remaining_budget=remaining_budget,
            round_number=round_number,
            max_rounds=max_rounds,
        )
        if stop_reason:
            break

    last_round = rounds[-1] if rounds else None
    status_value = _status_from_stop_reason(stop_reason, last_round)
    summary['stopped'] = stop_reason not in {None, 'no_tasks', 'dry_run_preview'}

    return {
        'schema_version': SCHEMA_VERSION,
        'base': str(root),
        'policy': policy,
        'dry_run': dry_run,
        'status': status_value,
        'stop_reason': stop_reason,
        'selection': {
            'status': status,
            'action': action,
            'id': task_id,
            'limit': limit,
            'max_rounds': max_rounds,
            'task_budget': task_budget,
        },
        'execution': {
            'mode': 'maintenance_loop',
            'continue_on_error': continue_on_error,
            'stop_on_error': not continue_on_error,
            'agent_command_explicit': agent_command is not None,
        },
        'artifacts': _artifacts(rounds),
        'rounds': rounds,
        'summary': summary,
        'next_actions': _next_actions(stop_reason, last_round),
    }
