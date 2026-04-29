from datetime import datetime, timezone
from pathlib import Path

from wikify.graph.builder import build_graph_artifacts
from wikify.maintenance.executor import apply_plan
from wikify.maintenance.findings import build_findings, summarize_findings
from wikify.maintenance.history import append_run, write_json
from wikify.maintenance.planner import build_plan
from wikify.maintenance.task_queue import build_task_queue
from wikify.maintenance.targets import load_maintenance_targets


FINDINGS_SCHEMA_VERSION = 'wikify.graph-findings.v1'


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _next_commands(dry_run: bool) -> list[str]:
    if dry_run:
        return ['wikify maintain', 'wikify graph --no-html']
    return ['wikify maintain --dry-run', 'wikify graph --no-html']


def _target_summary(targets: dict) -> dict:
    return {
        'schema_version': targets.get('schema_version'),
        'summary': dict(targets.get('summary') or {}),
        'warning_count': len(targets.get('warnings') or []),
        'warnings': list(targets.get('warnings') or []),
    }


def _build_findings_document(graph: dict, findings: list[dict], summary: dict, target_summary: dict | None = None) -> dict:
    return {
        'schema_version': FINDINGS_SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'graph_schema_version': graph.get('schema_version'),
        'base': graph.get('base'),
        'target_summary': target_summary,
        'summary': summary,
        'findings': findings,
    }


def run_maintenance(base: Path | str, policy: str = 'balanced', dry_run: bool = False) -> dict:
    root = Path(base).expanduser().resolve()
    graph_result = build_graph_artifacts(root, include_html=False)
    graph = graph_result['graph']
    targets = load_maintenance_targets(root)
    targets_summary = _target_summary(targets)
    findings = build_findings(graph, targets=targets)
    findings_summary = summarize_findings(findings)
    findings_document = _build_findings_document(graph, findings, findings_summary, targets_summary)
    plan = build_plan(findings, policy=policy)
    execution = apply_plan(plan, dry_run=dry_run)
    task_execution = apply_plan(plan, dry_run=False) if dry_run else execution
    task_queue = build_task_queue(plan, task_execution, findings)

    sorted_dir = root / 'sorted'
    findings_path = sorted_dir / 'graph-findings.json'
    plan_path = sorted_dir / 'graph-maintenance-plan.json'
    history_path = sorted_dir / 'graph-maintenance-history.json'
    task_queue_path = sorted_dir / 'graph-agent-tasks.json'
    artifacts = {
        'graph_json': graph_result['artifacts']['json'],
        'graph_report': graph_result['artifacts']['report'],
        'graph_html': graph_result['artifacts']['html'],
        'findings': None if dry_run else str(findings_path),
        'plan': None if dry_run else str(plan_path),
        'history': None if dry_run else str(history_path),
        'agent_tasks': None if dry_run else str(task_queue_path),
    }

    plan_summary = plan.get('summary', {})
    execution_summary = execution.get('summary', {})
    summary = {
        'finding_count': findings_summary.get('finding_count', 0),
        'planned_count': plan_summary.get('planned_count', 0),
        'executed_count': execution_summary.get('executed_count', 0),
        'queued_count': execution_summary.get('queued_count', 0),
        'dry_run_count': execution_summary.get('dry_run_count', 0),
        'skipped_count': execution_summary.get('skipped_count', 0),
        'task_count': task_queue.get('summary', {}).get('task_count', 0),
    }
    generated_at = _utc_now()
    run_record = {
        'generated_at': generated_at,
        'policy': policy,
        'dry_run': dry_run,
        'summary': summary,
        'artifacts': artifacts,
    }

    if not dry_run:
        write_json(findings_path, findings_document)
        write_json(plan_path, plan)
        write_json(task_queue_path, task_queue)
        append_run(root, run_record, dry_run=False)

    return {
        'generated_at': generated_at,
        'base': str(root),
        'policy': policy,
        'dry_run': dry_run,
        'artifacts': artifacts,
        'graph': graph_result['summary'],
        'targets': targets_summary,
        'findings': findings_document,
        'plan': plan,
        'execution': execution,
        'task_queue': task_queue,
        'summary': summary,
        'next_commands': _next_commands(dry_run),
        'completion': {
            'ok': True,
            'message': 'maintenance dry run complete' if dry_run else 'maintenance artifacts written',
        },
    }
