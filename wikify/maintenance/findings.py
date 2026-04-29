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
    enriched.update(metadata)
    return enriched


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

    return [_attach_target_metadata(finding, targets) for finding in findings]


def summarize_findings(findings: list[dict]) -> dict:
    by_type = Counter(finding.get('type', 'unknown') for finding in findings)
    by_severity = Counter(finding.get('severity', 'unknown') for finding in findings)
    return {
        'finding_count': len(findings),
        'by_type': dict(sorted(by_type.items())),
        'by_severity': dict(sorted(by_severity.items())),
    }
