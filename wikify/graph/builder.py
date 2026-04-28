import json
from datetime import datetime, timezone
from pathlib import Path

from wikify.graph.analytics import analyze, apply_degrees
from wikify.graph.extractors import extract_edges, extract_nodes
from wikify.graph.html import render_html
from wikify.graph.report import render_report
from wikify.markdown_index import scan_objects


SCHEMA_VERSION = 'wikify.graph.v1'


def assemble_graph(base: Path, nodes, edges, analytics: dict) -> dict:
    nodes_with_degrees = apply_degrees(nodes, analytics)
    return {
        'schema_version': SCHEMA_VERSION,
        'base': str(base.resolve()),
        'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'nodes': [node.to_dict() for node in nodes_with_degrees],
        'edges': [edge.to_dict() for edge in edges],
        'communities': analytics.get('communities', []),
        'analytics': analytics,
    }


def write_artifacts(base: Path, graph: dict, include_html: bool = True) -> dict:
    graph_dir = base / 'graph'
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph_path = graph_dir / 'graph.json'
    report_path = graph_dir / 'GRAPH_REPORT.md'
    html_path = graph_dir / 'graph.html'

    graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report_path.write_text(render_report(graph), encoding='utf-8')
    html_artifact = None
    if include_html:
        html_path.write_text(render_html(graph), encoding='utf-8')
        html_artifact = str(html_path)
    elif html_path.exists():
        html_path.unlink()

    analytics = graph.get('analytics', {})
    return {
        'artifacts': {
            'json': str(graph_path),
            'html': html_artifact,
            'report': str(report_path),
        },
        'summary': {
            'node_count': analytics.get('node_count', 0),
            'edge_count': analytics.get('edge_count', 0),
            'community_count': analytics.get('community_count', 0),
            'orphan_count': analytics.get('orphan_count', 0),
        },
        'graph': graph,
    }


def build_graph_artifacts(base: Path | str, scope: str = 'all', include_html: bool = True) -> dict:
    root = Path(base).expanduser().resolve()
    objects = scan_objects(root, scope=scope)
    nodes = extract_nodes(objects)
    edges = extract_edges(objects, nodes)
    analytics = analyze(nodes, edges)
    graph = assemble_graph(root, nodes, edges, analytics)
    return write_artifacts(root, graph, include_html=include_html)
