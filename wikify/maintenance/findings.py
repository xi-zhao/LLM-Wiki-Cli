from collections import Counter


TARGET_METADATA_KEYS = (
    'target_kind',
    'target_family',
    'object_id',
    'object_type',
    'body_path',
    'object_path',
    'view_path',
    'agent_artifact_path',
    'source_refs',
    'review_status',
    'write_scope',
    'regeneration_command',
)


def _finding(
    finding_id: str,
    finding_type: str,
    severity: str,
    title: str,
    subject: str,
    evidence: dict,
    recommended_action: str,
    can_auto_apply: bool,
    policy_minimum: str = 'conservative',
) -> dict:
    return {
        'id': finding_id,
        'type': finding_type,
        'severity': severity,
        'title': title,
        'subject': subject,
        'evidence': evidence,
        'recommended_action': recommended_action,
        'can_auto_apply': can_auto_apply,
        'policy_minimum': policy_minimum,
    }


def _relevance_for_subject(analytics: dict, subject: str) -> dict | None:
    node_relevance = analytics.get('relevance', {}).get('by_node', {}).get(subject)
    if not node_relevance:
        return None
    confidence = node_relevance.get('max_confidence', 'low')
    return {
        'schema_version': analytics.get('relevance', {}).get('schema_version'),
        'max_score': node_relevance.get('max_score', 0),
        'max_confidence': confidence,
        'priority_signal': confidence in {'medium', 'high'},
        'top_related': list(node_relevance.get('top_related', [])),
    }


def _attach_relevance(finding: dict, analytics: dict) -> dict:
    relevance = _relevance_for_subject(analytics, finding.get('subject'))
    if relevance:
        finding = dict(finding)
        finding['relevance'] = relevance
    return finding


def _attach_target_metadata(finding: dict, targets: dict | None) -> dict:
    if not targets:
        return finding
    from wikify.maintenance.targets import resolve_target

    target = resolve_target(targets, finding.get('subject'))
    metadata = {
        key: target[key]
        for key in TARGET_METADATA_KEYS
        if key in target and target[key] is not None
    }
    if not metadata:
        return finding
    enriched = dict(finding)
    for key, value in metadata.items():
        enriched.setdefault(key, value)
    return enriched


def _record_severity(record: dict) -> str:
    if record.get('severity') == 'error':
        return 'warning'
    return 'info'


def _validation_findings(targets: dict) -> list[dict]:
    validation = targets.get('object_validation') or {}
    findings = []
    for record in validation.get('records') or []:
        if not isinstance(record, dict):
            continue
        if record.get('severity') not in {'warning', 'error'}:
            continue
        subject = record.get('path') or record.get('object_id') or 'artifacts/objects/validation.json'
        finding = _finding(
            'object-validation:{}:{}:{}:{}'.format(
                record.get('code') or 'record',
                record.get('path') or 'unknown-path',
                record.get('object_id') or 'unknown-object',
                record.get('field') or 'unknown-field',
            ),
            'object_validation_record',
            _record_severity(record),
            'Object validation record',
            subject,
            dict(record),
            'queue_object_validation_repair',
            False,
        )
        findings.append(_attach_target_metadata(finding, targets))
    return findings


def _task_body_path(task: dict) -> str | None:
    target_paths = task.get('target_paths') if isinstance(task.get('target_paths'), dict) else {}
    planned_paths = task.get('planned_paths') if isinstance(task.get('planned_paths'), dict) else {}
    return target_paths.get('body_path') or task.get('body_path') or planned_paths.get('body_path')


def _wikiization_task_findings(targets: dict) -> list[dict]:
    queue = targets.get('wikiization_tasks') or {}
    findings = []
    for task in queue.get('tasks') or []:
        if not isinstance(task, dict):
            continue
        if task.get('status', 'queued') != 'queued':
            continue
        if task.get('reason_code') != 'generated_page_drifted':
            continue
        body_path = _task_body_path(task) or 'wiki/pages'
        finding = _finding(
            f'wikiization-task:{task.get("id") or body_path}',
            'generated_page_drift',
            'warning',
            'Generated page drift',
            body_path,
            dict(task),
            'queue_generated_page_repair',
            False,
        )
        findings.append(_attach_target_metadata(finding, targets))
    return findings


def _task_view_path(task: dict) -> str | None:
    target_paths = task.get('target_paths') if isinstance(task.get('target_paths'), dict) else {}
    evidence = task.get('evidence') if isinstance(task.get('evidence'), dict) else {}
    return target_paths.get('view_path') or task.get('view_path') or evidence.get('path')


def _view_task_findings(targets: dict) -> list[dict]:
    queue = targets.get('view_tasks') or {}
    findings = []
    for task in queue.get('tasks') or []:
        if not isinstance(task, dict):
            continue
        if task.get('status', 'queued') != 'queued':
            continue
        view_path = _task_view_path(task) or 'views'
        finding = _finding(
            f'view-task:{task.get("id") or view_path}',
            'view_task',
            'info',
            'Generated view task',
            view_path,
            dict(task),
            'queue_view_regeneration',
            False,
        )
        finding.update({
            'target_kind': 'view',
            'target_family': 'human_view',
            'view_path': view_path,
            'write_scope': [view_path],
            'regeneration_command': 'wikify views',
        })
        findings.append(_attach_target_metadata(finding, targets))
    return findings


def _agent_export_findings(targets: dict) -> list[dict]:
    if targets.get('summary', {}).get('object_count', 0) <= 0:
        return []
    findings = []
    for path in targets.get('missing_agent_artifacts') or []:
        finding = _finding(
            f'agent-export-missing:{path}',
            'agent_export_missing',
            'info',
            'Agent export artifact missing',
            path,
            {'path': path},
            'queue_agent_export_refresh',
            False,
        )
        finding.update({
            'target_kind': 'agent_artifact',
            'target_family': 'agent_export',
            'agent_artifact_path': path,
            'write_scope': [path],
            'regeneration_command': 'wikify agent export',
        })
        findings.append(_attach_target_metadata(finding, targets))
    return findings


def _artifact_findings(targets: dict | None) -> list[dict]:
    if not targets:
        return []
    return (
        _validation_findings(targets)
        + _wikiization_task_findings(targets)
        + _view_task_findings(targets)
        + _agent_export_findings(targets)
    )


def _dedupe_findings(findings: list[dict]) -> list[dict]:
    deduped = []
    seen = set()
    for finding in findings:
        finding_id = finding.get('id')
        if finding_id in seen:
            continue
        seen.add(finding_id)
        deduped.append(finding)
    return deduped


def build_findings(graph: dict, targets: dict | None = None) -> list[dict]:
    analytics = graph.get('analytics', {})
    findings = []

    for link in analytics.get('broken_links', []):
        source = link.get('source') or link.get('id') or 'unknown'
        target = link.get('target') or link.get('label') or 'unknown'
        line = link.get('line', 0)
        findings.append(
            _attach_relevance(
                _finding(
                    f'broken-link:{source}:{line}:{target}',
                    'broken_link',
                    'warning',
                    'Broken link',
                    source,
                    dict(link),
                    'queue_link_repair',
                    False,
                ),
                analytics,
            )
        )

    for orphan in analytics.get('orphans', []):
        subject = orphan.get('id') or orphan.get('path') or 'unknown'
        title = orphan.get('title') or subject
        findings.append(
            _attach_relevance(
                _finding(
                    f'orphan-node:{subject}',
                    'orphan_node',
                    'info',
                    f'Orphan wiki object: {title}',
                    subject,
                    dict(orphan),
                    'queue_orphan_attachment',
                    False,
                ),
                analytics,
            )
        )

    node_count = analytics.get('node_count', 0)
    central_threshold = max(8, node_count)
    for node in analytics.get('central_nodes', []):
        degree = node.get('degree', 0)
        if degree < central_threshold:
            continue
        subject = node.get('id') or 'unknown'
        findings.append(
            _attach_relevance(
                _finding(
                    f'god-node:{subject}',
                    'god_node',
                    'info',
                    'High-degree central node',
                    subject,
                    dict(node),
                    'queue_digest_refresh',
                    False,
                ),
                analytics,
            )
        )

    for community in analytics.get('communities', []):
        size = community.get('size', 0)
        if size < 3:
            continue
        subject = community.get('id') or 'community'
        findings.append(
            _attach_relevance(
                _finding(
                    f'mature-community:{subject}',
                    'mature_community',
                    'info',
                    'Community ready for synthesis',
                    subject,
                    dict(community),
                    'queue_community_synthesis',
                    False,
                ),
                analytics,
            )
        )

    edge_count = analytics.get('edge_count', 0)
    if node_count == 0 or edge_count == 0:
        findings.append(
            _finding(
                'thin-graph',
                'thin_graph',
                'warning',
                'Thin graph',
                'graph',
                {'node_count': node_count, 'edge_count': edge_count},
                'record_graph_health_snapshot',
                True,
            )
        )

    graph_findings = [_attach_target_metadata(finding, targets) for finding in findings]
    return _dedupe_findings(graph_findings + _artifact_findings(targets))


def summarize_findings(findings: list[dict]) -> dict:
    by_type = Counter(finding.get('type', 'unknown') for finding in findings)
    by_severity = Counter(finding.get('severity', 'unknown') for finding in findings)
    return {
        'finding_count': len(findings),
        'by_type': dict(sorted(by_type.items())),
        'by_severity': dict(sorted(by_severity.items())),
    }
