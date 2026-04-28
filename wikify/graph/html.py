import html
import json


def render_html(graph: dict) -> str:
    graph_json = html.escape(json.dumps(graph, ensure_ascii=False, indent=2))
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    node_items = '\n'.join(
        f"<li><strong>{html.escape(node['label'])}</strong> <code>{html.escape(node['id'])}</code> degree={node.get('degree', 0)}</li>"
        for node in nodes
    )
    edge_items = '\n'.join(
        f"<li><code>{html.escape(edge['source'])}</code> -> <code>{html.escape(edge['target'])}</code> ({html.escape(edge['type'])})</li>"
        for edge in edges
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Wikify Graph</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; line-height: 1.45; }}
    code, pre {{ background: #f4f4f4; padding: 0.15rem 0.3rem; border-radius: 4px; }}
    pre {{ padding: 1rem; overflow: auto; }}
  </style>
</head>
<body>
  <h1>Wikify Graph</h1>
  <p>{len(nodes)} nodes, {len(edges)} edges.</p>
  <h2>Nodes</h2>
  <ul>{node_items}</ul>
  <h2>Edges</h2>
  <ul>{edge_items}</ul>
  <h2>Raw Graph JSON</h2>
  <pre>{graph_json}</pre>
</body>
</html>
"""
