import re
from pathlib import Path

from wikify.graph.model import GraphEdge, GraphNode
from wikify.markdown_index import WikiObject


MARKDOWN_LINK_RE = re.compile(r'(?<!!)\[[^\]]+\]\(([^)]+)\)')
WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')


def extract_nodes(objects: list[WikiObject]) -> list[GraphNode]:
    nodes = []
    for obj in objects:
        nodes.append(GraphNode(
            id=obj.relative_path,
            path=str(obj.path),
            relative_path=obj.relative_path,
            type=obj.type,
            title=obj.title,
            label=obj.title,
            object_id=obj.object_id,
            canonical_type=obj.canonical_type,
        ))
    return nodes


def _node_lookup(nodes: list[GraphNode]) -> dict[str, GraphNode]:
    lookup = {}
    for node in nodes:
        lookup[node.id] = node
        lookup[Path(node.relative_path).stem] = node
        lookup[node.title] = node
    return lookup


def _resolve_markdown_target(obj: WikiObject, href: str, node_by_id: dict[str, GraphNode]) -> str | None:
    if '://' in href or href.startswith('#'):
        return None
    clean_href = href.split('#', 1)[0]
    if not clean_href:
        return None
    target_path = (obj.path.parent / clean_href).resolve()
    for node in node_by_id.values():
        if Path(node.path) == target_path:
            return node.id
    return None


def _resolve_wikilink_target(raw_target: str, node_by_id: dict[str, GraphNode]) -> str | None:
    normalized = raw_target.strip()
    candidates = [
        normalized,
        normalized.replace(' ', '-'),
        normalized.lower().replace(' ', '-'),
    ]
    for candidate in candidates:
        if candidate in node_by_id:
            return node_by_id[candidate].id
    return None


def extract_edges(objects: list[WikiObject], nodes: list[GraphNode]) -> list[GraphEdge]:
    node_by_id = {node.id: node for node in nodes}
    node_lookup = _node_lookup(nodes)
    edges = []
    seen = set()

    def add_edge(edge: GraphEdge):
        key = (edge.source, edge.target, edge.type, edge.line)
        if key in seen:
            return
        seen.add(key)
        edges.append(edge)

    for obj in objects:
        for line_number, line in obj.lines:
            for href in MARKDOWN_LINK_RE.findall(line):
                target = _resolve_markdown_target(obj, href, node_by_id)
                if target:
                    add_edge(GraphEdge(
                        source=obj.relative_path,
                        target=target,
                        type='markdown_link',
                        provenance='EXTRACTED',
                        confidence=1.0,
                        source_path=str(obj.path),
                        line=line_number,
                        label='links_to',
                    ))
                else:
                    add_edge(GraphEdge(
                        source=obj.relative_path,
                        target=href,
                        type='broken_link',
                        provenance='AMBIGUOUS',
                        confidence=0.0,
                        source_path=str(obj.path),
                        line=line_number,
                        label='unresolved_markdown_link',
                    ))

            for raw_target in WIKILINK_RE.findall(line):
                target = _resolve_wikilink_target(raw_target, node_lookup)
                if target:
                    add_edge(GraphEdge(
                        source=obj.relative_path,
                        target=target,
                        type='wikilink',
                        provenance='EXTRACTED',
                        confidence=1.0,
                        source_path=str(obj.path),
                        line=line_number,
                        label='wikilinks_to',
                    ))
                else:
                    add_edge(GraphEdge(
                        source=obj.relative_path,
                        target=raw_target.strip(),
                        type='broken_link',
                        provenance='AMBIGUOUS',
                        confidence=0.0,
                        source_path=str(obj.path),
                        line=line_number,
                        label='unresolved_wikilink',
                    ))

    return edges
