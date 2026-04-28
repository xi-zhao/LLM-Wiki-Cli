from datetime import datetime, timezone


SCHEMA_VERSION = 'wikify.graph-agent-tasks.v1'


INSTRUCTIONS = {
    'queue_link_repair': [
        'Inspect the source file and the unresolved link evidence.',
        'Choose an existing wiki object as the target only if the evidence is clear.',
        'Prepare a minimal patch proposal; do not invent a target when ambiguous.',
    ],
    'queue_orphan_attachment': [
        'Inspect the orphan wiki object and nearby topic candidates.',
        'Propose the smallest link or navigation update that connects the object.',
        'Keep the object content unchanged unless a later task explicitly asks for edits.',
    ],
    'queue_digest_refresh': [
        'Inspect the central node and its linked neighborhood.',
        'Propose whether a digest refresh is useful based on graph evidence.',
        'Keep generated content changes separate from structural link repairs.',
    ],
    'queue_community_synthesis': [
        'Inspect the community node list and identify the shared theme.',
        'Propose a synthesis page or topic update only if the cluster is coherent.',
        'Include source links for every proposed synthesis claim.',
    ],
}


ACCEPTANCE_CHECKS = {
    'queue_link_repair': [
        'The proposed patch resolves the broken link without introducing a new unresolved link.',
        'The chosen target exists in the wiki graph or the task is left queued with an ambiguity note.',
    ],
    'queue_orphan_attachment': [
        'The orphan object has at least one meaningful incoming or outgoing wiki relationship after the proposed patch.',
        'The proposed link is justified by existing content, not only by filename similarity.',
    ],
    'queue_digest_refresh': [
        'The digest proposal references the central node and preserves existing source attribution.',
        'The task remains queued if the refresh would require unsupported content generation.',
    ],
    'queue_community_synthesis': [
        'The synthesis proposal covers the community nodes listed in the evidence.',
        'The task remains queued if the community does not have a coherent shared theme.',
    ],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _priority(finding: dict) -> str:
    severity = finding.get('severity')
    if severity in {'critical', 'warning'}:
        return 'high'
    return 'normal'


def _step_by_id(plan: dict) -> dict[str, dict]:
    return {
        step.get('id'): step
        for step in plan.get('steps', [])
        if step.get('id')
    }


def _finding_by_id(findings: list[dict]) -> dict[str, dict]:
    return {
        finding.get('id'): finding
        for finding in findings
        if finding.get('id')
    }


def build_task_queue(plan: dict, execution: dict, findings: list[dict]) -> dict:
    steps = _step_by_id(plan)
    finding_lookup = _finding_by_id(findings)
    tasks = []

    for result in execution.get('results', []):
        if result.get('status') != 'queued':
            continue
        step = steps.get(result.get('step_id'), {})
        finding_id = result.get('finding_id')
        finding = finding_lookup.get(finding_id, {})
        action = result.get('action') or step.get('action')
        target = finding.get('subject') or step.get('subject')
        write_scope = [target] if target else []
        task_index = len(tasks) + 1
        tasks.append(
            {
                'id': f'agent-task-{task_index}',
                'source_finding_id': finding_id,
                'source_step_id': result.get('step_id'),
                'action': action,
                'priority': _priority(finding),
                'target': target,
                'evidence': dict(finding.get('evidence', {})),
                'write_scope': write_scope,
                'agent_instructions': INSTRUCTIONS.get(action, ['Review the finding and propose a safe next action.']),
                'acceptance_checks': ACCEPTANCE_CHECKS.get(action, ['The proposed action is justified by the finding evidence.']),
                'requires_user': False,
                'status': 'queued',
            }
        )

    return {
        'schema_version': SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'policy': plan.get('policy'),
        'summary': {
            'task_count': len(tasks),
            'by_action': _count_by_action(tasks),
        },
        'tasks': tasks,
    }


def _count_by_action(tasks: list[dict]) -> dict:
    counts = {}
    for task in tasks:
        action = task.get('action', 'unknown')
        counts[action] = counts.get(action, 0) + 1
    return dict(sorted(counts.items()))
