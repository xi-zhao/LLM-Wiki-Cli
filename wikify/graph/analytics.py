from collections import Counter, defaultdict, deque

from wikify.graph.relevance import compute_relevance
from wikify.graph.model import GraphEdge, GraphNode


def _extracted_adjacency(nodes: list[GraphNode], edges: list[GraphEdge]) -> dict[str, set[str]]:
    node_ids = {node.id for node in nodes}
    adjacency = {node_id: set() for node_id in node_ids}
    for edge in edges:
        if edge.provenance != 'EXTRACTED':
            continue
        if edge.source not in node_ids or edge.target not in node_ids:
            continue
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)
    return adjacency


def connected_components(nodes: list[GraphNode], edges: list[GraphEdge]) -> list[list[str]]:
    adjacency = _extracted_adjacency(nodes, edges)
    seen = set()
    components = []
    for node_id in sorted(adjacency):
        if node_id in seen:
            continue
        queue = deque([node_id])
        component = []
        seen.add(node_id)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
        components.append(sorted(component))
    components.sort(key=lambda item: (-len(item), item[0] if item else ''))
    return components


def analyze(nodes: list[GraphNode], edges: list[GraphEdge]) -> dict:
    degree = Counter()
    node_ids = {node.id for node in nodes}
    for edge in edges:
        if edge.provenance != 'EXTRACTED':
            continue
        if edge.source in node_ids:
            degree[edge.source] += 1
        if edge.target in node_ids:
            degree[edge.target] += 1

    components = connected_components(nodes, edges)
    relation_counts = Counter(edge.type for edge in edges)
    provenance_counts = Counter(edge.provenance for edge in edges)
    central_nodes = [
        {'id': node.id, 'title': node.title, 'type': node.type, 'degree': degree[node.id]}
        for node in nodes
        if degree[node.id] > 0
    ]
    central_nodes.sort(key=lambda item: (-item['degree'], item['id']))
    orphans = [
        {'id': node.id, 'title': node.title, 'type': node.type}
        for node in nodes
        if degree[node.id] == 0
    ]
    broken_links = [
        edge.to_dict()
        for edge in edges
        if edge.provenance == 'AMBIGUOUS'
    ]
    communities = [
        {'id': f'community-{index + 1}', 'nodes': component, 'size': len(component)}
        for index, component in enumerate(components)
    ]
    suggestions = suggested_questions(central_nodes, orphans, broken_links)
    relevance = compute_relevance(nodes, edges)
    return {
        'node_count': len(nodes),
        'edge_count': len(edges),
        'community_count': len(communities),
        'orphan_count': len(orphans),
        'central_nodes': central_nodes[:10],
        'orphans': orphans,
        'broken_links': broken_links,
        'relation_counts': dict(sorted(relation_counts.items())),
        'provenance_counts': dict(sorted(provenance_counts.items())),
        'suggested_questions': suggestions,
        'communities': communities,
        'degree_by_node': dict(sorted(degree.items())),
        'relevance': relevance,
    }


def suggested_questions(central_nodes: list[dict], orphans: list[dict], broken_links: list[dict]) -> list[str]:
    questions = []
    if central_nodes:
        questions.append(f"What maintenance would improve the central topic `{central_nodes[0]['title']}`?")
    if orphans:
        questions.append('Which orphan wiki objects should be linked into an existing topic?')
    if broken_links:
        questions.append('Which ambiguous or broken links should be repaired before the next digest?')
    questions.append('Which graph community is ready to become a higher-level synthesis page?')
    return questions[:5]


def apply_degrees(nodes: list[GraphNode], analytics: dict) -> list[GraphNode]:
    degree_by_node = defaultdict(int, analytics.get('degree_by_node', {}))
    return [
        GraphNode(
            id=node.id,
            path=node.path,
            relative_path=node.relative_path,
            type=node.type,
            title=node.title,
            label=node.label,
            tags=list(node.tags),
            degree=degree_by_node[node.id],
        )
        for node in nodes
    ]
