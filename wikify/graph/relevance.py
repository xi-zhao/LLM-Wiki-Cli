import math
from itertools import combinations

from wikify.graph.model import GraphEdge, GraphNode


SCHEMA_VERSION = 'wikify.graph-relevance.v1'

WEIGHTS = {
    'direct_link': 4.0,
    'source_overlap': 3.0,
    'common_neighbors': 1.5,
    'type_affinity': 1.0,
}

TYPE_AFFINITY = {
    frozenset({'topics', 'parsed'}): 1.0,
    frozenset({'topics', 'briefs'}): 0.8,
    frozenset({'topics', 'sorted'}): 0.7,
    frozenset({'topics', 'timelines'}): 0.6,
    frozenset({'sources', 'parsed'}): 0.6,
}


def _extracted_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    return [edge for edge in edges if edge.provenance == 'EXTRACTED']


def _adjacency(node_ids: set[str], edges: list[GraphEdge]) -> dict[str, set[str]]:
    adjacency = {node_id: set() for node_id in node_ids}
    for edge in _extracted_edges(edges):
        if edge.source not in node_ids or edge.target not in node_ids:
            continue
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)
    return adjacency


def _source_paths_by_node(node_ids: set[str], edges: list[GraphEdge]) -> dict[str, set[str]]:
    source_paths = {node_id: set() for node_id in node_ids}
    for edge in _extracted_edges(edges):
        if not edge.source_path:
            continue
        if edge.source in node_ids:
            source_paths[edge.source].add(edge.source_path)
    return source_paths


def _direct_link_count(source: str, target: str, edges: list[GraphEdge]) -> int:
    count = 0
    for edge in _extracted_edges(edges):
        if {edge.source, edge.target} == {source, target}:
            count += 1
    return count


def _type_affinity(source: GraphNode, target: GraphNode) -> float:
    if source.type == target.type and source.type == 'topics':
        return 0.3
    return TYPE_AFFINITY.get(frozenset({source.type, target.type}), 0.0)


def _common_neighbor_score(
    source: str,
    target: str,
    adjacency: dict[str, set[str]],
) -> tuple[float, list[str]]:
    common = sorted(adjacency.get(source, set()) & adjacency.get(target, set()))
    score = 0.0
    for neighbor in common:
        degree = len(adjacency.get(neighbor, set()))
        if degree <= 1:
            continue
        score += 1.0 / math.log(degree + 1)
    return score, common


def _confidence(score: float) -> str:
    if score >= 6.0:
        return 'high'
    if score >= 2.0:
        return 'medium'
    return 'low'


def _pair_score(
    source: GraphNode,
    target: GraphNode,
    edges: list[GraphEdge],
    adjacency: dict[str, set[str]],
    source_paths: dict[str, set[str]],
) -> dict:
    direct_count = _direct_link_count(source.id, target.id, edges)
    shared_sources = sorted(source_paths.get(source.id, set()) & source_paths.get(target.id, set()))
    common_score, common_neighbors = _common_neighbor_score(source.id, target.id, adjacency)
    type_score = _type_affinity(source, target)

    score = (
        direct_count * WEIGHTS['direct_link']
        + len(shared_sources) * WEIGHTS['source_overlap']
        + common_score * WEIGHTS['common_neighbors']
        + type_score * WEIGHTS['type_affinity']
    )
    return {
        'source': source.id,
        'target': target.id,
        'score': round(score, 4),
        'confidence': _confidence(score),
        'signals': {
            'direct_link': {
                'count': direct_count,
                'score': round(direct_count * WEIGHTS['direct_link'], 4),
            },
            'source_overlap': {
                'shared_count': len(shared_sources),
                'shared_sources': shared_sources,
                'score': round(len(shared_sources) * WEIGHTS['source_overlap'], 4),
            },
            'common_neighbors': {
                'count': len(common_neighbors),
                'neighbors': common_neighbors,
                'score': round(common_score * WEIGHTS['common_neighbors'], 4),
            },
            'type_affinity': {
                'source_type': source.type,
                'target_type': target.type,
                'score': round(type_score * WEIGHTS['type_affinity'], 4),
            },
        },
    }


def _by_node(pairs: list[dict], per_node_limit: int) -> dict:
    related: dict[str, list[dict]] = {}
    for pair in pairs:
        source = pair['source']
        target = pair['target']
        source_entry = _related_entry(pair, target)
        target_entry = _related_entry(pair, source)
        related.setdefault(source, []).append(source_entry)
        related.setdefault(target, []).append(target_entry)

    by_node = {}
    for node_id, entries in related.items():
        entries.sort(key=lambda item: (-item['score'], item['id']))
        top_related = entries[:per_node_limit]
        by_node[node_id] = {
            'max_score': top_related[0]['score'],
            'max_confidence': top_related[0]['confidence'],
            'top_related': top_related,
        }
    return dict(sorted(by_node.items()))


def _related_entry(pair: dict, node_id: str) -> dict:
    return {
        'id': node_id,
        'score': pair['score'],
        'confidence': pair['confidence'],
        'signals': {
            'direct_link': pair['signals']['direct_link']['count'],
            'source_overlap': pair['signals']['source_overlap']['shared_count'],
            'common_neighbors': pair['signals']['common_neighbors']['count'],
            'type_affinity': pair['signals']['type_affinity']['score'],
        },
    }


def compute_relevance(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    limit: int = 50,
    per_node_limit: int = 5,
) -> dict:
    node_ids = {node.id for node in nodes}
    adjacency = _adjacency(node_ids, edges)
    source_paths = _source_paths_by_node(node_ids, edges)
    pairs = []

    for source, target in combinations(nodes, 2):
        pair = _pair_score(source, target, edges, adjacency, source_paths)
        if pair['score'] <= 0:
            continue
        pairs.append(pair)

    pairs.sort(key=lambda item: (-item['score'], item['source'], item['target']))
    pairs = pairs[:limit]
    by_node = _by_node(pairs, per_node_limit)
    confidence_counts = {}
    for pair in pairs:
        confidence = pair['confidence']
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

    return {
        'schema_version': SCHEMA_VERSION,
        'summary': {
            'pair_count': len(pairs),
            'by_confidence': dict(sorted(confidence_counts.items())),
        },
        'pairs': pairs,
        'by_node': by_node,
        'weights': dict(WEIGHTS),
    }
