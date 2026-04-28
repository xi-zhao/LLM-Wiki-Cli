def _line_items(items: list[dict], formatter) -> list[str]:
    if not items:
        return ['- None']
    return [formatter(item) for item in items]


def render_report(graph: dict) -> str:
    analytics = graph.get('analytics', {})
    lines = [
        '# Wikify Graph Report',
        '',
        '## Summary',
        '',
        f"- Nodes: {analytics.get('node_count', 0)}",
        f"- Edges: {analytics.get('edge_count', 0)}",
        f"- Communities: {analytics.get('community_count', 0)}",
        f"- Orphans: {analytics.get('orphan_count', 0)}",
        '',
        '## God Nodes',
        '',
    ]
    lines.extend(_line_items(
        analytics.get('central_nodes', []),
        lambda item: f"- {item['title']} (`{item['id']}`) degree={item['degree']}",
    ))
    lines.extend(['', '## Communities', ''])
    lines.extend(_line_items(
        analytics.get('communities', []),
        lambda item: f"- {item['id']}: {item['size']} node(s) - {', '.join(item['nodes'][:5])}",
    ))
    lines.extend(['', '## Orphans', ''])
    lines.extend(_line_items(
        analytics.get('orphans', []),
        lambda item: f"- {item['title']} (`{item['id']}`)",
    ))
    lines.extend(['', '## Broken Or Ambiguous Links', ''])
    lines.extend(_line_items(
        analytics.get('broken_links', []),
        lambda item: f"- {item['source']}:{item['line']} -> `{item['target']}` ({item['label']})",
    ))
    lines.extend(['', '## Suggested Questions', ''])
    suggestions = analytics.get('suggested_questions', [])
    lines.extend([f'- {question}' for question in suggestions] if suggestions else ['- None'])
    return '\n'.join(lines).strip() + '\n'
