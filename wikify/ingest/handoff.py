import json
from pathlib import Path

from wikify.ingest.artifacts import (
    TRUSTED_AGENT_INGEST_REQUEST_SCHEMA_VERSION,
    relative_to_root,
    trusted_agent_request_path,
    write_json_atomic,
)
from wikify.ingest.documents import NormalizedDocument
from wikify.objects import object_index_path


def build_trusted_agent_ingest_request(
    root: Path,
    *,
    workspace_id: str,
    run_id: str,
    document: NormalizedDocument,
    item: dict,
    queue_entry: dict,
    artifacts: dict,
    human_path: dict,
    human_entry: dict,
    created_at: str,
    status: str = 'ready_for_agent',
) -> dict:
    request_path = trusted_agent_request_path(root, run_id)
    return {
        'schema_version': TRUSTED_AGENT_INGEST_REQUEST_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'run_id': run_id,
        'status': status,
        'created_at': created_at,
        'updated_at': created_at,
        'request_path': relative_to_root(root, request_path),
        'source': _source_section(document, item),
        'content': _content_section(document),
        'workspace_context': _workspace_context(root),
        'task': _task_section(document),
        'trusted_agent': _trusted_agent_section(),
        'recovery': _recovery_section(root),
        'page_quality': _page_quality_section(),
        'completion_summary_contract': _completion_summary_contract(),
        'queue_entry': {
            'queue_id': queue_entry.get('queue_id'),
            'status': queue_entry.get('status'),
            'action': queue_entry.get('action'),
            'item_id': queue_entry.get('item_id'),
        },
        'artifacts': dict(artifacts),
        'human_path': dict(human_path or {}),
        'human_entry': dict(human_entry or {}),
        'agent_next_actions': trusted_agent_next_actions(),
    }


def write_trusted_agent_ingest_request(root: Path, request: dict) -> Path:
    path = trusted_agent_request_path(root, request['run_id'])
    write_json_atomic(path, request)
    return path


def trusted_agent_next_actions() -> list[str]:
    return [
        'read_trusted_agent_request',
        'organize_source_into_personal_wiki',
        'run_wikify_validate',
        'refresh_wikify_views',
        'report_human_summary',
    ]


def build_completion_summary(
    *,
    status: str,
    document: NormalizedDocument | None,
    item: dict,
    request_path: str,
    human_entry: dict,
    human_path: dict,
) -> dict:
    page_path = human_entry.get('body_path') if human_entry else None
    source_title = document.title if document else item.get('metadata', {}).get('title')
    source_status = 'preserved' if status == 'completed' else status
    if status == 'planned':
        source_status = 'planned'
    human_summary = {
        'source_status': source_status,
        'source_title': source_title,
        'wiki_entry_path': page_path,
        'trusted_agent_request': request_path,
        'message': _human_message(status, page_path),
        'source_preserved': status != 'failed',
    }
    return {
        'human_summary': human_summary,
        'agent_next_actions': trusted_agent_next_actions(),
        'human_path': dict(human_path or {}),
        'human_entry': dict(human_entry or {}),
    }


def _source_section(document: NormalizedDocument, item: dict) -> dict:
    return {
        'source_id': item.get('source_id'),
        'item_id': item.get('item_id'),
        'adapter': document.adapter,
        'original_locator': document.original_locator,
        'canonical_locator': document.canonical_locator,
        'title': document.title,
        'author': document.author,
        'published_at': document.published_at,
        'captured_at': document.captured_at,
        'fingerprint': dict(document.fingerprint or {}),
        'raw_paths': dict(document.raw_paths or {}),
        'warnings': list(document.warnings or []),
        'metadata': dict(document.metadata or {}),
    }


def _content_section(document: NormalizedDocument) -> dict:
    body_text = document.body_text or ''
    return {
        'title_candidates': [document.title] if document.title else [],
        'author_candidates': [document.author] if document.author else [],
        'published_time_candidates': [document.published_at] if document.published_at else [],
        'cleaned_markdown_path': document.raw_paths.get('document'),
        'text_path': document.raw_paths.get('text'),
        'metadata_path': document.raw_paths.get('metadata'),
        'body_char_count': len(body_text),
        'has_body_text': bool(body_text.strip()),
        'extraction_quality': {
            'status': 'warning' if document.warnings else 'ok',
            'warnings': list(document.warnings or []),
        },
    }


def _workspace_context(root: Path) -> dict:
    object_index = _read_optional_json(object_index_path(root))
    objects = list((object_index or {}).get('objects') or [])
    topics = [entry for entry in objects if entry.get('type') == 'topic']
    pages = [entry for entry in objects if entry.get('type') == 'wiki_page']
    return {
        'object_index_path': _optional_relative(root, object_index_path(root)),
        'existing_topic_index': _compact_objects(topics, limit=25),
        'recent_pages': _compact_objects(pages, limit=25),
        'likely_related_pages': [],
        'graph_summary': _graph_summary(root),
        'notes': [
            'Use existing topics and pages as context, but decide structure autonomously.',
            'Create, update, merge, split, or delete wiki pages when that improves the knowledge base.',
        ],
    }


def _task_section(document: NormalizedDocument) -> dict:
    return {
        'user_intent': 'save_and_organize_personal_wiki',
        'expected_outcome': 'source_backed_knowledge_page_or_ingest_plan',
        'source_complexity': _source_complexity(document),
        'instructions': [
            'Turn the source into a durable personal wiki entry when the source is focused enough.',
            'For complex sources, create an ingest plan and split work into batches.',
            'Prefer structure, reusable insight, topic placement, and relationships to existing knowledge over generic summary.',
        ],
    }


def _trusted_agent_section() -> dict:
    return {
        'autonomy': 'full_control',
        'permissions': {
            'read': 'all_wiki_source_artifacts_context',
            'write': 'wiki_pages_topics_views_graph_objects_agent_exports',
            'reorganize': 'allowed',
            'delete_merge': 'allowed_with_snapshot',
            'repair': 'allowed',
        },
        'principle': 'Trusted agents may reorganize the wiki; Wikify preserves traceability and recovery records.',
    }


def _recovery_section(root: Path) -> dict:
    return {
        'snapshot_policy': 'snapshot_before_broad_rewrite_merge_split_delete',
        'operation_record_policy': 'record_what_changed_and_why',
        'validation_commands': [
            'wikify validate --strict --write-report',
            'wikify views',
            'wikify agent export',
        ],
        'rollback_guidance': [
            'Use existing wikify rollback for patch-bundle applications.',
            'For broad trusted-agent rewrites, create snapshots before mutation until dedicated trusted operation records are implemented.',
        ],
        'workspace_root': str(root),
    }


def _page_quality_section() -> dict:
    return {
        'type': 'personal_wiki_entry',
        'required_sections': [
            '一句话结论',
            '为什么值得保存',
            '核心观点',
            '可复用洞察',
            '相关主题',
            '和已有知识的关系',
            '来源依据',
        ],
        'emphasis': [
            'conclusion',
            'why_worth_saving',
            'reusable_insights',
            'topic_placement',
            'relationship_to_existing_knowledge',
        ],
        'source_evidence_required': True,
        'metadata_should_not_dominate_first_read': True,
    }


def _completion_summary_contract() -> dict:
    return {
        'audience': 'human',
        'style': 'knowledge_base_change_summary',
        'human_summary_fields': [
            'added pages',
            'updated pages',
            'related topics',
            'extracted long-term value',
            'source preservation status',
            'warnings and next steps',
        ],
        'avoid_exposing_by_default': [
            'source_id',
            'queue_id',
            'raw artifact internals',
            'validation report internals',
        ],
    }


def _source_complexity(document: NormalizedDocument) -> str:
    body_len = len(document.body_text or '')
    if document.adapter in {'wechat_url', 'web_url'} and body_len < 50000:
        return 'simple_article'
    if body_len > 100000:
        return 'complex_large_source'
    return 'focused_document'


def _human_message(status: str, page_path: str | None) -> str:
    if status == 'planned':
        return 'ingest dry run completed; trusted agent request is planned'
    if page_path:
        return 'source saved and organized into the wiki'
    if status == 'completed':
        return 'source saved; trusted agent should organize it into the wiki'
    return 'ingest did not complete'


def _compact_objects(entries: list[dict], *, limit: int) -> list[dict]:
    compact = []
    for entry in entries[:limit]:
        compact.append({
            'id': entry.get('id'),
            'type': entry.get('type'),
            'title': entry.get('title'),
            'relative_path': entry.get('relative_path'),
        })
    return compact


def _graph_summary(root: Path) -> dict:
    graph_path = root / 'graph' / 'graph.json'
    graph = _read_optional_json(graph_path)
    if not graph:
        return {'graph_path': _optional_relative(root, graph_path), 'available': False}
    nodes = graph.get('nodes') or []
    edges = graph.get('edges') or []
    return {
        'graph_path': _optional_relative(root, graph_path),
        'available': True,
        'node_count': len(nodes) if isinstance(nodes, list) else None,
        'edge_count': len(edges) if isinstance(edges, list) else None,
    }


def _read_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _optional_relative(root: Path, path: Path) -> str | None:
    if not path.exists():
        return None
    return relative_to_root(root, path)
