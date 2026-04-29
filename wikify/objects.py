import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSIONS = {
    'object_index': 'wikify.object-index.v1',
    'wiki_page': 'wikify.wiki-page.v1',
    'topic': 'wikify.topic.v1',
    'project': 'wikify.project.v1',
    'person': 'wikify.person.v1',
    'decision': 'wikify.decision.v1',
    'timeline_entry': 'wikify.timeline-entry.v1',
    'citation': 'wikify.citation.v1',
    'graph_edge': 'wikify.graph-edge.v1',
    'context_pack': 'wikify.context-pack.v1',
    'object_validation': 'wikify.object-validation.v1',
}

OBJECT_TYPES = {
    'source',
    'source_item',
    'wiki_page',
    'topic',
    'project',
    'person',
    'decision',
    'timeline_entry',
    'citation',
    'graph_edge',
    'context_pack',
}

REVIEW_STATUSES = {'generated', 'needs_review', 'approved', 'rejected', 'stale'}
GRAPH_PROVENANCE_VALUES = {'EXTRACTED', 'INFERRED', 'AMBIGUOUS'}

OBJECT_ID_PREFIXES = {
    'wiki_page': 'page_',
    'topic': 'topic_',
    'project': 'project_',
    'person': 'person_',
    'decision': 'decision_',
    'timeline_entry': 'timeline_',
    'citation': 'citation_',
    'graph_edge': 'edge_',
    'context_pack': 'ctx_',
}

LEGACY_SCOPE_OBJECT_TYPES = {
    'topics': 'topic',
    'timelines': 'timeline_entry',
    'briefs': 'wiki_page',
    'parsed': 'wiki_page',
    'sorted': 'wiki_page',
    'sources': 'source',
}

REQUIRED_FIELDS = {
    'source': {'schema_version', 'id', 'type', 'source'},
    'source_item': {'schema_version', 'id', 'type', 'source_id', 'source_item'},
    'wiki_page': {
        'schema_version',
        'id',
        'type',
        'title',
        'summary',
        'body_path',
        'source_refs',
        'outbound_links',
        'backlinks',
        'created_at',
        'updated_at',
        'confidence',
        'review_status',
    },
    'topic': {'schema_version', 'id', 'type', 'title', 'summary', 'page_ids', 'source_refs'},
    'project': {'schema_version', 'id', 'type', 'title', 'summary', 'page_ids', 'source_refs'},
    'person': {'schema_version', 'id', 'type', 'title', 'summary', 'page_ids', 'source_refs'},
    'decision': {'schema_version', 'id', 'type', 'title', 'summary', 'status', 'source_refs'},
    'timeline_entry': {'schema_version', 'id', 'type', 'title', 'summary', 'timestamp', 'source_refs'},
    'citation': {'schema_version', 'id', 'type', 'source_id', 'locator', 'confidence'},
    'graph_edge': {'schema_version', 'id', 'source', 'target', 'type', 'provenance', 'confidence', 'source_path', 'line', 'label'},
    'context_pack': {'schema_version', 'id', 'type', 'title', 'summary', 'object_ids', 'source_refs'},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _root(base: Path | str) -> Path:
    return Path(base).expanduser()


def object_artifacts_dir(base: Path | str) -> Path:
    return _root(base) / Path('artifacts') / 'objects'


def object_index_path(base: Path | str) -> Path:
    return object_artifacts_dir(base) / 'object-index.json'


def object_document_path(base: Path | str, object_type: str, object_id: str) -> Path:
    directory = f'{object_type}s'
    if object_type == 'wiki_page':
        directory = 'wiki_pages'
    return object_artifacts_dir(base) / directory / f'{object_id}.json'


def _slug(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_')
    return slug or 'object'


def stable_object_id(object_type: str, locator: str) -> str:
    if object_type not in OBJECT_ID_PREFIXES:
        raise ValueError(f'unsupported generated object type: {object_type}')
    digest = hashlib.sha256(f'{object_type}\0{locator}'.encode('utf-8')).hexdigest()[:16]
    return f'{OBJECT_ID_PREFIXES[object_type]}{_slug(Path(locator).stem or locator)[:32]}_{digest}'


def legacy_scope_to_object_type(scope: str) -> str:
    if scope not in LEGACY_SCOPE_OBJECT_TYPES:
        raise ValueError(f'unsupported legacy scope: {scope}')
    return LEGACY_SCOPE_OBJECT_TYPES[scope]


def is_known_object_type(value) -> bool:
    return value in OBJECT_TYPES


def is_known_review_status(value) -> bool:
    return value in REVIEW_STATUSES


def is_known_graph_provenance(value) -> bool:
    return value in GRAPH_PROVENANCE_VALUES


def _base_object(schema_key: str, object_id: str, object_type: str) -> dict:
    return {
        'schema_version': SCHEMA_VERSIONS[schema_key],
        'id': object_id,
        'type': object_type,
    }


def make_object_index(base: Path | str, objects: list[dict], generated_at: str | None = None) -> dict:
    entries = [
        {
            'id': obj.get('id'),
            'type': obj.get('type') or obj.get('object_type'),
            'schema_version': obj.get('schema_version'),
            'relative_path': obj.get('relative_path'),
            'title': obj.get('title'),
        }
        for obj in objects
    ]
    return {
        'schema_version': SCHEMA_VERSIONS['object_index'],
        'base': str(_root(base)),
        'generated_at': generated_at or _utc_now(),
        'summary': {
            'object_count': len(entries),
            'by_type': _count_by_type(entries),
        },
        'objects': entries,
    }


def _count_by_type(objects: list[dict]) -> dict:
    counts = {}
    for obj in objects:
        object_type = obj.get('type') or obj.get('object_type') or 'unknown'
        counts[object_type] = counts.get(object_type, 0) + 1
    return dict(sorted(counts.items()))


def make_wiki_page_object(
    *,
    object_id: str,
    title: str,
    summary: str,
    body_path: str,
    source_refs: list[dict],
    outbound_links: list,
    backlinks: list,
    created_at: str,
    updated_at: str,
    confidence: float,
    review_status: str,
    relative_path: str | None = None,
) -> dict:
    obj = _base_object('wiki_page', object_id, 'wiki_page')
    obj.update({
        'title': title,
        'summary': summary,
        'body_path': body_path,
        'relative_path': relative_path,
        'source_refs': list(source_refs),
        'outbound_links': list(outbound_links),
        'backlinks': list(backlinks),
        'created_at': created_at,
        'updated_at': updated_at,
        'confidence': float(confidence),
        'review_status': review_status,
    })
    return obj


def _make_collection_object(
    schema_key: str,
    object_type: str,
    *,
    object_id: str,
    title: str,
    summary: str,
    page_ids: list | None = None,
    source_refs: list[dict] | None = None,
    **extra,
) -> dict:
    obj = _base_object(schema_key, object_id, object_type)
    obj.update({
        'title': title,
        'summary': summary,
        'page_ids': list(page_ids or []),
        'source_refs': list(source_refs or []),
    })
    obj.update(extra)
    return obj


def make_topic_object(**kwargs) -> dict:
    return _make_collection_object('topic', 'topic', **kwargs)


def make_project_object(**kwargs) -> dict:
    return _make_collection_object('project', 'project', **kwargs)


def make_person_object(**kwargs) -> dict:
    return _make_collection_object('person', 'person', **kwargs)


def make_decision_object(
    *,
    object_id: str,
    title: str,
    summary: str,
    status: str,
    source_refs: list[dict] | None = None,
    **extra,
) -> dict:
    obj = _base_object('decision', object_id, 'decision')
    obj.update({
        'title': title,
        'summary': summary,
        'status': status,
        'source_refs': list(source_refs or []),
    })
    obj.update(extra)
    return obj


def make_timeline_entry_object(
    *,
    object_id: str,
    title: str,
    summary: str,
    timestamp: str,
    source_refs: list[dict] | None = None,
    **extra,
) -> dict:
    obj = _base_object('timeline_entry', object_id, 'timeline_entry')
    obj.update({
        'title': title,
        'summary': summary,
        'timestamp': timestamp,
        'source_refs': list(source_refs or []),
    })
    obj.update(extra)
    return obj


def make_citation_object(
    *,
    object_id: str,
    source_id: str,
    locator: str,
    confidence: float,
    item_id: str | None = None,
    span: dict | None = None,
    snippet: str | None = None,
) -> dict:
    obj = _base_object('citation', object_id, 'citation')
    obj.update({
        'source_id': source_id,
        'item_id': item_id,
        'locator': locator,
        'span': span or {},
        'confidence': float(confidence),
    })
    if snippet is not None:
        obj['snippet'] = snippet[:500]
    return obj


def make_graph_edge_object(
    *,
    object_id: str,
    source: str,
    target: str,
    edge_type: str,
    provenance: str,
    confidence: float,
    source_path: str,
    line: int,
    label: str,
) -> dict:
    return {
        'schema_version': SCHEMA_VERSIONS['graph_edge'],
        'id': object_id,
        'object_type': 'graph_edge',
        'source': source,
        'target': target,
        'type': edge_type,
        'provenance': provenance,
        'confidence': float(confidence),
        'source_path': source_path,
        'line': int(line),
        'label': label,
    }


def make_context_pack_object(
    *,
    object_id: str,
    title: str,
    summary: str,
    object_ids: list,
    source_refs: list[dict] | None = None,
    **extra,
) -> dict:
    obj = _base_object('context_pack', object_id, 'context_pack')
    obj.update({
        'title': title,
        'summary': summary,
        'object_ids': list(object_ids),
        'source_refs': list(source_refs or []),
    })
    obj.update(extra)
    return obj


def source_record_to_object(source: dict) -> dict:
    source_id = source.get('source_id')
    return {
        'schema_version': source.get('schema_version', 'wikify.source-registry.v1'),
        'id': source_id,
        'type': 'source',
        'title': source.get('title') or source.get('locator') or source_id,
        'source': dict(source),
    }


def source_item_record_to_object(item: dict) -> dict:
    item_id = item.get('item_id')
    return {
        'schema_version': item.get('schema_version', 'wikify.source-items.v1'),
        'id': item_id,
        'type': 'source_item',
        'source_id': item.get('source_id'),
        'relative_path': item.get('relative_path'),
        'source_item': dict(item),
    }
