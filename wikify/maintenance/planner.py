from datetime import datetime, timezone


SCHEMA_VERSION = 'wikify.maintenance-plan.v1'
POLICIES = ('conservative', 'balanced', 'aggressive')
ACTION_RISKS = {
    'queue_link_repair': 'semantic',
    'queue_orphan_attachment': 'semantic',
    'queue_digest_refresh': 'generated_content',
    'queue_community_synthesis': 'generated_content',
    'queue_object_validation_repair': 'semantic',
    'queue_generated_page_repair': 'semantic',
    'queue_view_regeneration': 'generated_content',
    'queue_agent_export_refresh': 'deterministic',
    'queue_source_traceability_repair': 'semantic',
    'record_graph_health_snapshot': 'deterministic',
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _policy_allows(policy: str, minimum: str) -> bool:
    return POLICIES.index(policy) >= POLICIES.index(minimum)


def build_plan(findings: list[dict], policy: str = 'balanced') -> dict:
    if policy not in POLICIES:
        raise ValueError(f'Unknown maintenance policy: {policy}')

    steps = []
    for index, finding in enumerate(findings, start=1):
        action = finding.get('recommended_action', 'review_manually')
        policy_minimum = finding.get('policy_minimum', 'conservative')
        if policy_minimum not in POLICIES:
            policy_minimum = 'conservative'
        risk = ACTION_RISKS.get(action, 'semantic')
        can_auto_apply = bool(finding.get('can_auto_apply', False))
        steps.append(
            {
                'id': f'step-{index}',
                'finding_id': finding.get('id'),
                'finding_type': finding.get('type'),
                'severity': finding.get('severity'),
                'title': finding.get('title'),
                'subject': finding.get('subject'),
                'action': action,
                'risk': risk,
                'can_auto_apply': can_auto_apply,
                'policy_minimum': policy_minimum,
                'policy_allowed': _policy_allows(policy, policy_minimum),
                'executable_in_v1': risk == 'deterministic' and can_auto_apply,
            }
        )

    return {
        'schema_version': SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'policy': policy,
        'steps': steps,
        'summary': {
            'planned_count': len(steps),
            'executable_count': sum(
                1
                for step in steps
                if step['policy_allowed'] and step['executable_in_v1']
            ),
            'queued_count': sum(
                1
                for step in steps
                if step['policy_allowed'] and not step['executable_in_v1']
            ),
        },
    }
