import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wikify.frontmatter import split_front_matter
from wikify.object_validation import validate_workspace_objects, validation_report_path
from wikify.objects import SCHEMA_VERSIONS, object_artifacts_dir, object_index_path
from wikify.sync import SOURCE_ITEMS_SCHEMA_VERSION, source_items_path
from wikify.views import views_manifest_path, views_report_path
from wikify.workspace import load_workspace


AGENT_EXPORT_SCHEMA_VERSION = 'wikify.agent-export.v1'
PAGE_INDEX_SCHEMA_VERSION = 'wikify.page-index.v1'
CITATION_INDEX_SCHEMA_VERSION = 'wikify.citation-index.v1'
RELATED_INDEX_SCHEMA_VERSION = 'wikify.related-index.v1'
AGENT_GRAPH_SCHEMA_VERSION = 'wikify.agent-graph.v1'

RELATED_WEIGHTS = {
    'direct_object_link': 4.0,
    'graph_edge': 3.5,
    'shared_source': 3.0,
    'citation_overlap': 2.5,
    'common_neighbor': 1.5,
    'type_affinity': 1.0,
    'text_match': 1.0,
}


class AgentInterfaceError(ValueError):
    def __init__(self, message: str, code: str = 'agent_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _stable_digest(*parts: object) -> str:
    payload = '\0'.join(str(part) for part in parts)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def agent_artifact_dir(base: Path | str) -> Path:
    return _root(base) / 'artifacts' / 'agent'


def agent_report_path(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'agent' / 'last-agent-export.json'


def page_index_path(base: Path | str) -> Path:
    return agent_artifact_dir(base) / 'page-index.json'


def citation_index_path(base: Path | str) -> Path:
    return agent_artifact_dir(base) / 'citation-index.json'


def related_index_path(base: Path | str) -> Path:
    return agent_artifact_dir(base) / 'related-index.json'


def agent_graph_path(base: Path | str) -> Path:
    return agent_artifact_dir(base) / 'graph.json'


def _llms_path(base: Path | str) -> Path:
    return _root(base) / 'llms.txt'


def _llms_full_path(base: Path | str) -> Path:
    return _root(base) / 'llms-full.txt'


def _write_json_atomic(path: Path, document: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp_path.replace(path)


def _write_text_atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(text, encoding='utf-8')
    temp_path.replace(path)


def _read_json(path: Path, *, schema_version: str | None = None, code: str = 'agent_json_invalid') -> dict:
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise AgentInterfaceError(
            f'agent input artifact is invalid JSON: {path}',
            code=code,
            details={'path': str(path)},
        ) from exc
    except OSError as exc:
        raise AgentInterfaceError(
            f'agent input artifact cannot be read: {path}',
            code=code,
            details={'path': str(path), 'error': str(exc)},
        ) from exc
    if schema_version is not None and document.get('schema_version') != schema_version:
        raise AgentInterfaceError(
            f'agent input artifact schema is unsupported: {path}',
            code=f'{code}_schema_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    return document


def _read_optional_json(path: Path, *, schema_version: str | None = None, code: str = 'agent_json_invalid') -> dict | None:
    if not path.exists():
        return None
    return _read_json(path, schema_version=schema_version, code=code)


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _object_type(obj: dict) -> str:
    return obj.get('type') or obj.get('object_type') or 'unknown'


def _object_sort_key(obj: dict) -> tuple[str, str, str]:
    return (str(obj.get('title') or ''), str(obj.get('updated_at') or obj.get('timestamp') or ''), str(obj.get('id') or ''))


def _load_object_documents(root: Path) -> list[dict]:
    directory = object_artifacts_dir(root)
    if not directory.exists():
        return []
    objects = []
    for path in sorted(directory.rglob('*.json')):
        if path.name in {'object-index.json', 'validation.json'}:
            continue
        document = _read_json(path, code='agent_object_invalid')
        if isinstance(document, dict):
            document.setdefault('_artifact_path', _relative(root, path))
            objects.append(document)
    return objects


def _load_snapshot(root: Path) -> dict:
    warnings: list[dict] = []
    workspace = load_workspace(root)
    object_index = _read_optional_json(object_index_path(root), schema_version=SCHEMA_VERSIONS['object_index'], code='agent_object_index_invalid')
    if object_index is None:
        warnings.append(_warning('object_index_missing', 'object index is missing; scanning object documents instead', 'artifacts/objects/object-index.json'))
    source_items = _read_optional_json(source_items_path(root), schema_version=SOURCE_ITEMS_SCHEMA_VERSION, code='agent_source_items_invalid')
    if source_items is None:
        warnings.append(_warning('source_items_missing', 'source item index is missing; source item metadata will be limited', '.wikify/sync/source-items.json'))
    validation = _read_optional_json(validation_report_path(root), schema_version=SCHEMA_VERSIONS['object_validation'], code='agent_validation_report_invalid')
    view_manifest = _read_optional_json(views_manifest_path(root), code='agent_view_manifest_invalid')
    if view_manifest is None:
        warnings.append(_warning('views_missing', 'view manifest is missing; human view paths may be omitted', '.wikify/views/view-manifest.json'))
    view_report = _read_optional_json(views_report_path(root), code='agent_views_report_invalid')
    legacy_graph = _read_optional_json(root / 'graph' / 'graph.json', code='agent_legacy_graph_invalid')
    if legacy_graph is None:
        warnings.append(_warning('graph_missing', 'legacy graph artifact is missing; graph-edge object signals still apply', 'graph/graph.json'))
    objects = _load_object_documents(root)
    if not objects:
        warnings.append(_warning('objects_missing', 'no object documents were found', 'artifacts/objects/'))
    return {
        'root': root,
        'workspace': workspace,
        'registry': workspace.get('registry') or {},
        'object_index': object_index,
        'objects': sorted(objects, key=_object_sort_key),
        'source_items': source_items,
        'validation_report': validation,
        'view_manifest': view_manifest,
        'view_report': view_report,
        'legacy_graph': legacy_graph,
        'warnings': warnings,
    }


def _warning(code: str, message: str, path: str | None = None) -> dict:
    return {'code': code, 'message': message, 'path': path}


def _validate_before_write(root: Path) -> dict:
    result = validate_workspace_objects(root, path=object_artifacts_dir(root), strict=True, write_report=True)
    if result.get('summary', {}).get('error_count', 0):
        raise AgentInterfaceError(
            'object validation failed before agent artifact generation',
            code='agent_validation_failed',
            details={'validation': result},
        )
    return result


def _sources(snapshot: dict) -> list[dict]:
    sources = list((snapshot.get('registry') or {}).get('sources', {}).values())
    return sorted(sources, key=lambda source: source.get('source_id') or '')


def _objects_by_id(snapshot: dict) -> dict[str, dict]:
    return {obj.get('id'): obj for obj in snapshot.get('objects', []) if obj.get('id')}


def _objects_by_type(snapshot: dict, object_type: str) -> list[dict]:
    return [obj for obj in snapshot.get('objects', []) if _object_type(obj) == object_type]


def _source_ref_key(ref: dict) -> tuple[str, str, str]:
    return (str(ref.get('source_id') or ''), str(ref.get('item_id') or ''), str(ref.get('locator') or ref.get('relative_path') or ''))


def _source_ref_text(ref: dict) -> str:
    pieces = []
    for key in ('source_id', 'item_id', 'locator', 'relative_path'):
        value = ref.get(key)
        if key == 'locator' and value and Path(str(value)).is_absolute():
            continue
        if value:
            pieces.append(f'{key}={value}')
    confidence = ref.get('confidence')
    if confidence is not None:
        pieces.append(f'confidence={confidence}')
    return ', '.join(pieces) or 'source reference'


def _text_terms(value: str | None) -> set[str]:
    return {part for part in re.findall(r'[a-z0-9]+', (value or '').lower()) if len(part) > 1}


def _object_terms(obj: dict) -> set[str]:
    fields = [obj.get('id'), obj.get('title'), obj.get('summary'), _object_type(obj)]
    return set().union(*(_text_terms(str(field)) for field in fields if field))


def _human_view_path(root: Path, page: dict) -> str | None:
    if (root / 'views' / 'pages.md').exists():
        return 'views/pages.md'
    return None


def _build_page_index(snapshot: dict) -> dict:
    root = snapshot['root']
    pages = []
    for page in _objects_by_type(snapshot, 'wiki_page'):
        pages.append({
            'id': page.get('id'),
            'type': 'wiki_page',
            'title': page.get('title'),
            'summary': page.get('summary'),
            'body_path': page.get('body_path'),
            'review_status': page.get('review_status'),
            'confidence': page.get('confidence'),
            'updated_at': page.get('updated_at'),
            'source_refs': list(page.get('source_refs') or []),
            'outbound_links': list(page.get('outbound_links') or []),
            'backlinks': list(page.get('backlinks') or []),
            'human_view_path': _human_view_path(root, page),
            'object_path': page.get('_artifact_path'),
        })
    pages.sort(key=lambda page: (page.get('title') or '', page.get('id') or ''))
    return {
        'schema_version': PAGE_INDEX_SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'summary': {'page_count': len(pages)},
        'pages': pages,
    }


def _citation_linked_pages(snapshot: dict, citation: dict) -> list[str]:
    linked = []
    for page in _objects_by_type(snapshot, 'wiki_page'):
        for ref in page.get('source_refs') or []:
            if not isinstance(ref, dict):
                continue
            same_source = ref.get('source_id') == citation.get('source_id')
            same_item = citation.get('item_id') is None or ref.get('item_id') == citation.get('item_id')
            if same_source and same_item:
                linked.append(page.get('id'))
    return sorted({item for item in linked if item})


def _build_citation_index(snapshot: dict) -> dict:
    evidence = []
    for citation in _objects_by_type(snapshot, 'citation'):
        evidence.append({
            'id': citation.get('id'),
            'evidence_type': 'explicit_citation',
            'source_id': citation.get('source_id'),
            'item_id': citation.get('item_id'),
            'locator': citation.get('locator'),
            'confidence': citation.get('confidence'),
            'snippet': citation.get('snippet'),
            'span': citation.get('span') or {},
            'linked_object_ids': _citation_linked_pages(snapshot, citation),
            'object_id': citation.get('id'),
        })
    for page in _objects_by_type(snapshot, 'wiki_page'):
        for index, ref in enumerate(page.get('source_refs') or []):
            if not isinstance(ref, dict):
                continue
            evidence.append({
                'id': f'{page.get("id")}:source-ref:{index}',
                'evidence_type': 'page_source_ref',
                'source_id': ref.get('source_id'),
                'item_id': ref.get('item_id'),
                'locator': ref.get('locator') or ref.get('relative_path') or ref.get('path'),
                'confidence': ref.get('confidence'),
                'snippet': None,
                'span': ref.get('span') or {},
                'linked_object_ids': [page.get('id')] if page.get('id') else [],
                'object_id': page.get('id'),
            })
    evidence.sort(key=lambda item: (0 if item.get('evidence_type') == 'explicit_citation' else 1, item.get('source_id') or '', item.get('id') or ''))
    by_type = {}
    for item in evidence:
        evidence_type = item.get('evidence_type') or 'unknown'
        by_type[evidence_type] = by_type.get(evidence_type, 0) + 1
    return {
        'schema_version': CITATION_INDEX_SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'summary': {
            'evidence_count': len(evidence),
            'by_evidence_type': dict(sorted(by_type.items())),
        },
        'evidence': evidence,
    }


def _edge(source: str, target: str, edge_type: str, provenance: str, confidence: float, label: str, source_path: str | None = None) -> dict:
    return {
        'id': f'agent-edge-{_stable_digest(source, target, edge_type, label)[:16]}',
        'source': source,
        'target': target,
        'type': edge_type,
        'provenance': provenance,
        'confidence': float(confidence),
        'label': label,
        'source_path': source_path,
    }


def _agent_edges(snapshot: dict) -> list[dict]:
    object_ids = set(_objects_by_id(snapshot))
    edges = []
    for obj in snapshot.get('objects', []):
        object_type = _object_type(obj)
        obj_id = obj.get('id')
        if object_type == 'graph_edge':
            source = obj.get('source')
            target = obj.get('target')
            if source and target:
                edges.append({
                    'id': obj.get('id') or f'agent-edge-{_stable_digest(source, target)[:16]}',
                    'source': source,
                    'target': target,
                    'type': obj.get('type') or obj.get('edge_type') or 'related',
                    'provenance': obj.get('provenance') or 'EXTRACTED',
                    'confidence': obj.get('confidence'),
                    'label': obj.get('label'),
                    'source_path': obj.get('source_path'),
                })
            continue
        if not obj_id:
            continue
        for target in obj.get('outbound_links') or []:
            if target in object_ids:
                edges.append(_edge(obj_id, target, 'object_link', 'EXTRACTED', 1.0, 'outbound_link', obj.get('body_path')))
        for target in obj.get('backlinks') or []:
            if target in object_ids:
                edges.append(_edge(target, obj_id, 'object_link', 'EXTRACTED', 1.0, 'backlink', obj.get('body_path')))
        for target in obj.get('page_ids') or []:
            if target in object_ids:
                edges.append(_edge(obj_id, target, 'collection_page', 'EXTRACTED', 1.0, 'page_id', obj.get('_artifact_path')))
    unique = {edge['id']: edge for edge in edges}
    return sorted(unique.values(), key=lambda edge: (edge.get('source') or '', edge.get('target') or '', edge.get('id') or ''))


def _build_agent_graph(snapshot: dict) -> dict:
    nodes = []
    for obj in snapshot.get('objects', []):
        object_type = _object_type(obj)
        if object_type == 'graph_edge':
            continue
        nodes.append({
            'id': obj.get('id'),
            'type': object_type,
            'title': obj.get('title') or obj.get('id'),
            'summary': obj.get('summary'),
            'source_refs': list(obj.get('source_refs') or []),
            'object_path': obj.get('_artifact_path'),
        })
    nodes.sort(key=lambda node: (node.get('type') or '', node.get('title') or '', node.get('id') or ''))
    edges = _agent_edges(snapshot)
    return {
        'schema_version': AGENT_GRAPH_SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'summary': {'node_count': len(nodes), 'edge_count': len(edges)},
        'nodes': nodes,
        'edges': edges,
        'legacy_graph': {
            'path': 'graph/graph.json' if snapshot.get('legacy_graph') is not None else None,
            'present': snapshot.get('legacy_graph') is not None,
        },
    }


def _neighbors(edges: list[dict]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for edge in edges:
        source = edge.get('source')
        target = edge.get('target')
        if not source or not target:
            continue
        result.setdefault(source, set()).add(target)
        result.setdefault(target, set()).add(source)
    return result


def _direct_link_signal(source: dict, target: dict) -> int:
    source_id = source.get('id')
    target_id = target.get('id')
    if not source_id or not target_id:
        return 0
    count = 0
    if target_id in (source.get('outbound_links') or []):
        count += 1
    if target_id in (source.get('backlinks') or []):
        count += 1
    if source_id in (target.get('outbound_links') or []):
        count += 1
    if source_id in (target.get('backlinks') or []):
        count += 1
    if target_id in (source.get('page_ids') or []):
        count += 1
    if source_id in (target.get('page_ids') or []):
        count += 1
    return count


def _graph_edge_signal(source_id: str, target_id: str, edges: list[dict]) -> int:
    return sum(1 for edge in edges if {edge.get('source'), edge.get('target')} == {source_id, target_id})


def _source_keys(obj: dict) -> set[tuple[str, str, str]]:
    return {_source_ref_key(ref) for ref in obj.get('source_refs') or [] if isinstance(ref, dict)}


def _type_affinity(source: dict, target: dict) -> float:
    source_type = _object_type(source)
    target_type = _object_type(target)
    if source_type == target_type and source_type != 'wiki_page':
        return 0.5
    if 'wiki_page' in {source_type, target_type}:
        return 0.8
    return 0.2


def _confidence(score: float) -> str:
    if score >= 6:
        return 'high'
    if score >= 2:
        return 'medium'
    return 'low'


def _related_pair(source: dict, target: dict, edges: list[dict], adjacency: dict[str, set[str]]) -> dict | None:
    source_id = source.get('id')
    target_id = target.get('id')
    if not source_id or not target_id:
        return None
    direct = _direct_link_signal(source, target)
    graph_edge = _graph_edge_signal(source_id, target_id, edges)
    shared_sources = sorted(_source_keys(source) & _source_keys(target))
    citation_overlap = len({key for key in shared_sources if key[0] or key[1]})
    common_neighbors = sorted(adjacency.get(source_id, set()) & adjacency.get(target_id, set()))
    type_affinity = _type_affinity(source, target)
    text_matches = sorted(_object_terms(source) & _object_terms(target))
    text_match = len(text_matches)
    signals = {
        'direct_object_link': {'count': direct, 'score': round(direct * RELATED_WEIGHTS['direct_object_link'], 4)},
        'graph_edge': {'count': graph_edge, 'score': round(graph_edge * RELATED_WEIGHTS['graph_edge'], 4)},
        'shared_source': {
            'count': len(shared_sources),
            'source_refs': [{'source_id': item[0], 'item_id': item[1], 'locator': item[2]} for item in shared_sources],
            'score': round(len(shared_sources) * RELATED_WEIGHTS['shared_source'], 4),
        },
        'citation_overlap': {'count': citation_overlap, 'score': round(citation_overlap * RELATED_WEIGHTS['citation_overlap'], 4)},
        'common_neighbor': {
            'count': len(common_neighbors),
            'object_ids': common_neighbors,
            'score': round(len(common_neighbors) * RELATED_WEIGHTS['common_neighbor'], 4),
        },
        'type_affinity': {'value': type_affinity, 'score': round(type_affinity * RELATED_WEIGHTS['type_affinity'], 4)},
        'text_match': {'count': text_match, 'terms': text_matches[:20], 'score': round(text_match * RELATED_WEIGHTS['text_match'], 4)},
    }
    score = round(sum(signal['score'] for signal in signals.values()), 4)
    if score <= 0:
        return None
    return {
        'source_id': source_id,
        'target_id': target_id,
        'score': score,
        'confidence': _confidence(score),
        'signals': signals,
    }


def _build_related_index(snapshot: dict) -> dict:
    objects = [obj for obj in snapshot.get('objects', []) if obj.get('id') and _object_type(obj) != 'graph_edge']
    edges = _agent_edges(snapshot)
    adjacency = _neighbors(edges)
    related = []
    for source_index, source in enumerate(objects):
        for target in objects[source_index + 1:]:
            pair = _related_pair(source, target, edges, adjacency)
            if pair:
                related.append(pair)
    related.sort(key=lambda item: (-item['score'], item['source_id'], item['target_id']))
    by_object: dict[str, list[dict]] = {}
    for pair in related:
        by_object.setdefault(pair['source_id'], []).append({
            'id': pair['target_id'],
            'score': pair['score'],
            'confidence': pair['confidence'],
            'signals': pair['signals'],
        })
        by_object.setdefault(pair['target_id'], []).append({
            'id': pair['source_id'],
            'score': pair['score'],
            'confidence': pair['confidence'],
            'signals': pair['signals'],
        })
    for values in by_object.values():
        values.sort(key=lambda item: (-item['score'], item['id']))
    return {
        'schema_version': RELATED_INDEX_SCHEMA_VERSION,
        'generated_at': _utc_now(),
        'summary': {'related_pair_count': len(related), 'object_count': len(by_object)},
        'weights': dict(RELATED_WEIGHTS),
        'related': related,
        'by_object': dict(sorted(by_object.items())),
    }


def _render_llms_txt(snapshot: dict, indexes: dict) -> str:
    page_count = len(indexes['page_index']['pages'])
    evidence_count = len(indexes['citation_index']['evidence'])
    related_count = len(indexes['related_index']['related'])
    source_count = len(_sources(snapshot))
    lines = [
        '# Wikify Agent Context',
        '',
        'This workspace exposes a source-backed local wiki for agents. Use the generated artifacts below before rereading raw source material.',
        '',
        '## Entry Points',
        '',
        '- `artifacts/agent/page-index.json` - generated wiki pages, source refs, review status, and human view paths.',
        '- `artifacts/agent/citation-index.json` - explicit citations and page source-ref fallback evidence.',
        '- `artifacts/agent/related-index.json` - ranked object/page relationships with explanation signals.',
        '- `artifacts/agent/graph.json` - object-model-first graph export.',
        '- `llms-full.txt` - richer bounded page excerpts and metadata.',
        '',
        '## Counts',
        '',
        f'- Sources: {source_count}',
        f'- Wiki pages: {page_count}',
        f'- Citation evidence entries: {evidence_count}',
        f'- Related pairs: {related_count}',
        '',
        '## Commands',
        '',
        '- `wikify agent export` regenerates durable agent artifacts.',
        '- `wikify agent context "<task>"` builds a task-specific context pack.',
        '- `wikify agent cite "<claim or topic>"` returns source-backed evidence.',
        '- `wikify agent related "<object id or query>"` returns relationship explanations.',
        '',
        'Agents should cite source refs or explicit citation ids from these artifacts when using wiki claims.',
    ]
    return '\n'.join(lines) + '\n'


def _read_page_body(root: Path, body_path: str | None) -> str:
    if not body_path:
        return ''
    path = root / body_path
    if not path.exists():
        return ''
    try:
        metadata, body = split_front_matter(path.read_text(encoding='utf-8'))
    except Exception:
        del metadata
        return path.read_text(encoding='utf-8')
    return body


def _bounded(text: str, limit: int) -> tuple[str, bool]:
    if limit < 0:
        limit = 0
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip() + '\n[truncated]\n', True


def _render_llms_full(snapshot: dict, indexes: dict, max_full_chars: int = 60000, max_page_chars: int = 4000) -> tuple[str, dict]:
    root = snapshot['root']
    lines = [
        '# Wikify Agent Context - Full',
        '',
        '## Truncation',
        '',
        f'- max_full_chars: {max_full_chars}',
        f'- max_page_chars: {max_page_chars}',
        '- truncated: false',
        '',
        '## Artifacts',
        '',
        '- `artifacts/agent/page-index.json`',
        '- `artifacts/agent/citation-index.json`',
        '- `artifacts/agent/related-index.json`',
        '- `artifacts/agent/graph.json`',
        '',
        '## Pages',
        '',
    ]
    included_chars = len('\n'.join(lines))
    omitted_count = 0
    page_truncations = []
    truncated = False
    for page in indexes['page_index']['pages']:
        body = _read_page_body(root, page.get('body_path'))
        excerpt, page_truncated = _bounded(body, max_page_chars)
        block = '\n'.join([
            f'### {page.get("title") or page.get("id")}',
            '',
            f'- Object id: `{page.get("id")}`',
            f'- Body path: `{page.get("body_path")}`',
            f'- Review status: `{page.get("review_status")}`',
            f'- Confidence: `{page.get("confidence")}`',
            '- Source refs:',
            *[f'  - {_source_ref_text(ref)}' for ref in page.get('source_refs') or []],
            '',
            excerpt.strip(),
            '',
        ])
        if included_chars + len(block) > max_full_chars:
            omitted_count += 1
            truncated = True
            continue
        lines.append(block)
        included_chars += len(block)
        if page_truncated:
            truncated = True
            page_truncations.append(page.get('id'))
    text = '\n'.join(lines).replace('- truncated: false', f'- truncated: {str(truncated).lower()}', 1)
    truncation = {
        'max_full_chars': max_full_chars,
        'max_page_chars': max_page_chars,
        'included_chars': len(text),
        'omitted_page_count': omitted_count,
        'truncated': truncated,
        'page_truncations': page_truncations,
    }
    return text.rstrip() + '\n', truncation


def _planned_artifacts(include_full: bool = True) -> list[dict]:
    artifacts = [
        {'path': 'llms.txt', 'kind': 'text'},
        {'path': 'artifacts/agent/page-index.json', 'kind': 'json'},
        {'path': 'artifacts/agent/citation-index.json', 'kind': 'json'},
        {'path': 'artifacts/agent/related-index.json', 'kind': 'json'},
        {'path': 'artifacts/agent/graph.json', 'kind': 'json'},
        {'path': '.wikify/agent/last-agent-export.json', 'kind': 'json'},
    ]
    if include_full:
        artifacts.insert(1, {'path': 'llms-full.txt', 'kind': 'text'})
    return artifacts


def _completion(status: str, artifacts: list[dict], next_actions: list[str]) -> dict:
    artifact_paths = [item['path'] for item in artifacts if item.get('path')]
    return {
        'status': status,
        'summary': 'agent export dry run completed' if status == 'dry_run' else 'agent export completed',
        'artifacts': artifact_paths,
        'next_actions': next_actions,
        'user_message': 'agent export dry run completed' if status == 'dry_run' else 'agent export completed',
    }


def _next_actions(warnings: list[dict]) -> list[str]:
    actions = []
    if any(warning.get('code') == 'objects_missing' for warning in warnings):
        actions.append('run_wikify_wikiize')
    if any(warning.get('code') == 'views_missing' for warning in warnings):
        actions.append('run_wikify_views')
    return actions


def _summary(indexes: dict, warnings: list[dict], truncation: dict | None = None) -> dict:
    return {
        'page_count': len(indexes['page_index']['pages']),
        'citation_evidence_count': len(indexes['citation_index']['evidence']),
        'related_pair_count': len(indexes['related_index']['related']),
        'graph_node_count': len(indexes['agent_graph']['nodes']),
        'graph_edge_count': len(indexes['agent_graph']['edges']),
        'warning_count': len(warnings),
        'truncation': truncation or {},
    }


def _build_indexes(snapshot: dict) -> dict:
    page_index = _build_page_index(snapshot)
    citation_index = _build_citation_index(snapshot)
    agent_graph = _build_agent_graph(snapshot)
    related_index = _build_related_index(snapshot)
    return {
        'page_index': page_index,
        'citation_index': citation_index,
        'related_index': related_index,
        'agent_graph': agent_graph,
    }


def run_agent_export(
    base: Path | str,
    dry_run: bool = False,
    include_full: bool = True,
    max_full_chars: int = 60000,
    max_page_chars: int = 4000,
) -> dict:
    root = _root(base)
    snapshot = _load_snapshot(root)
    if not dry_run:
        _validate_before_write(root)
    indexes = _build_indexes(snapshot)
    llms = _render_llms_txt(snapshot, indexes)
    llms_full, truncation = _render_llms_full(snapshot, indexes, max_full_chars=max_full_chars, max_page_chars=max_page_chars)
    planned = _planned_artifacts(include_full=include_full)
    warnings = list(snapshot.get('warnings') or [])
    next_actions = _next_actions(warnings)
    result = {
        'schema_version': AGENT_EXPORT_SCHEMA_VERSION,
        'status': 'dry_run' if dry_run else 'completed',
        'dry_run': dry_run,
        'base': str(root),
        'planned': planned,
        'generated': [],
        'summary': _summary(indexes, warnings, truncation),
        'warnings': warnings,
        'next_actions': next_actions,
    }
    result['completion'] = _completion(result['status'], planned, next_actions)
    if dry_run:
        return result

    generated = []
    _write_text_atomic(_llms_path(root), llms)
    generated.append({'path': 'llms.txt', 'kind': 'text'})
    if include_full:
        _write_text_atomic(_llms_full_path(root), llms_full)
        generated.append({'path': 'llms-full.txt', 'kind': 'text'})
    _write_json_atomic(page_index_path(root), indexes['page_index'])
    generated.append({'path': 'artifacts/agent/page-index.json', 'kind': 'json'})
    _write_json_atomic(citation_index_path(root), indexes['citation_index'])
    generated.append({'path': 'artifacts/agent/citation-index.json', 'kind': 'json'})
    _write_json_atomic(related_index_path(root), indexes['related_index'])
    generated.append({'path': 'artifacts/agent/related-index.json', 'kind': 'json'})
    _write_json_atomic(agent_graph_path(root), indexes['agent_graph'])
    generated.append({'path': 'artifacts/agent/graph.json', 'kind': 'json'})
    result['generated'] = generated
    result['completion'] = _completion(result['status'], generated, next_actions)
    report = dict(result)
    report['artifacts'] = {item['path']: item['kind'] for item in generated}
    _write_json_atomic(agent_report_path(root), report)
    result['generated'].append({'path': '.wikify/agent/last-agent-export.json', 'kind': 'json'})
    result['completion'] = _completion(result['status'], result['generated'], next_actions)
    return result
