from collections import Counter
from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _status_for_step(step: dict, dry_run: bool) -> str:
    if dry_run:
        return 'dry_run'
    if not step.get('policy_allowed', False):
        return 'skipped_policy'
    if step.get('executable_in_v1', False):
        return 'executed'
    return 'queued'


def apply_plan(plan: dict, dry_run: bool = False) -> dict:
    results = []
    for step in plan.get('steps', []):
        status = _status_for_step(step, dry_run=dry_run)
        results.append(
            {
                'step_id': step.get('id'),
                'finding_id': step.get('finding_id'),
                'action': step.get('action'),
                'risk': step.get('risk'),
                'status': status,
                'reason': _reason(step, status),
            }
        )

    counts = Counter(result['status'] for result in results)
    return {
        'executed_at': _utc_now(),
        'dry_run': dry_run,
        'results': results,
        'summary': {
            'executed_count': counts.get('executed', 0),
            'queued_count': counts.get('queued', 0),
            'dry_run_count': counts.get('dry_run', 0),
            'skipped_count': counts.get('skipped_policy', 0),
        },
    }


def _reason(step: dict, status: str) -> str:
    if status == 'dry_run':
        return 'dry run requested'
    if status == 'skipped_policy':
        return f"requires {step.get('policy_minimum', 'conservative')} policy"
    if status == 'executed':
        return 'deterministic action is safe to apply in v1'
    return 'semantic or generated-content action is queued for agent review'
