import hashlib
import html
import json
import posixpath
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wikify.frontmatter import render_markdown_with_front_matter, split_front_matter
from wikify.object_validation import validate_workspace_objects, validation_report_path
from wikify.objects import SCHEMA_VERSIONS, object_artifacts_dir, object_index_path
from wikify.sync import INGEST_QUEUE_SCHEMA_VERSION, SOURCE_ITEMS_SCHEMA_VERSION, ingest_queue_path, source_items_path
from wikify.wikiize import WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION, wikiization_task_queue_path
from wikify.workspace import load_workspace


VIEWS_RUN_SCHEMA_VERSION = 'wikify.views-run.v1'
VIEWS_MANIFEST_SCHEMA_VERSION = 'wikify.views-manifest.v1'
VIEW_TASK_QUEUE_SCHEMA_VERSION = 'wikify.view-tasks.v1'
VIEW_DOCUMENT_SCHEMA_VERSION = 'wikify.view.v1'

SECTION_CHOICES = {'all', 'home', 'sources', 'pages', 'collections', 'timeline', 'graph', 'review'}
COLLECTION_TYPES = ('topic', 'project', 'person', 'decision')


class ViewGenerationError(ValueError):
    def __init__(self, message: str, code: str = 'views_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _stable_digest(*parts: object) -> str:
    payload = '\0'.join(str(part) for part in parts)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def views_report_path(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'views' / 'last-views.json'


def views_manifest_path(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'views' / 'view-manifest.json'


def view_task_queue_path(base: Path | str) -> Path:
    return _root(base) / '.wikify' / 'queues' / 'view-tasks.json'


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


def _read_json(path: Path, *, schema_version: str | None = None, code: str = 'views_json_invalid') -> dict:
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ViewGenerationError(
            f'views input artifact is invalid JSON: {path}',
            code=code,
            details={'path': str(path)},
        ) from exc
    if schema_version is not None and document.get('schema_version') != schema_version:
        raise ViewGenerationError(
            f'views input artifact schema is unsupported: {path}',
            code=f'{code}_schema_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    return document


def _read_optional_json(path: Path, *, schema_version: str | None = None, code: str = 'views_json_invalid') -> dict | None:
    if not path.exists():
        return None
    return _read_json(path, schema_version=schema_version, code=code)


def _load_manifest(root: Path) -> dict:
    path = views_manifest_path(root)
    if not path.exists():
        return {
            'schema_version': VIEWS_MANIFEST_SCHEMA_VERSION,
            'generated_at': None,
            'files': {},
        }
    document = _read_json(path, schema_version=VIEWS_MANIFEST_SCHEMA_VERSION, code='views_manifest_invalid')
    if not isinstance(document.get('files'), dict):
        raise ViewGenerationError('views manifest files field is invalid', code='views_manifest_invalid', details={'path': str(path)})
    return document


def _load_task_queue(root: Path) -> dict:
    path = view_task_queue_path(root)
    if not path.exists():
        return {
            'schema_version': VIEW_TASK_QUEUE_SCHEMA_VERSION,
            'generated_at': None,
            'summary': {'task_count': 0, 'by_reason': {}},
            'tasks': [],
        }
    document = _read_json(path, schema_version=VIEW_TASK_QUEUE_SCHEMA_VERSION, code='view_task_queue_invalid')
    if not isinstance(document.get('tasks'), list):
        raise ViewGenerationError('view task queue tasks field is invalid', code='view_task_queue_invalid', details={'path': str(path)})
    return document


def _load_object_index(root: Path, warnings: list[dict]) -> dict | None:
    path = object_index_path(root)
    if not path.exists():
        warnings.append(_warning('object_index_missing', 'object index is missing; rendering by scanning object artifacts', 'artifacts/objects/object-index.json'))
        return None
    return _read_json(path, schema_version=SCHEMA_VERSIONS['object_index'], code='views_object_index_invalid')


def _load_object_documents(root: Path) -> list[dict]:
    directory = object_artifacts_dir(root)
    if not directory.exists():
        return []
    objects = []
    for path in sorted(directory.rglob('*.json')):
        if path.name in {'object-index.json', 'validation.json'}:
            continue
        document = _read_json(path, code='views_object_invalid')
        if isinstance(document, dict):
            document.setdefault('_artifact_path', path.relative_to(root).as_posix())
            objects.append(document)
    return objects


def _load_workspace_snapshot(root: Path, warnings: list[dict]) -> dict:
    workspace = load_workspace(root)
    registry = workspace.get('registry') or {}
    source_items = _read_optional_json(
        source_items_path(root),
        schema_version=SOURCE_ITEMS_SCHEMA_VERSION,
        code='views_source_items_invalid',
    )
    if source_items is None:
        warnings.append(_warning('source_items_missing', 'source item index is missing; source pages will show registry status only', '.wikify/sync/source-items.json'))
    ingest_queue = _read_optional_json(
        ingest_queue_path(root),
        schema_version=INGEST_QUEUE_SCHEMA_VERSION,
        code='views_ingest_queue_invalid',
    )
    if ingest_queue is None:
        warnings.append(_warning('ingest_queue_missing', 'ingest queue is missing; review view will omit pending ingest items', '.wikify/queues/ingest-items.json'))
    wikiization_tasks = _read_optional_json(
        wikiization_task_queue_path(root),
        schema_version=WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION,
        code='views_wikiization_tasks_invalid',
    )
    if wikiization_tasks is None:
        warnings.append(_warning('wikiization_tasks_missing', 'wikiization task queue is missing; no wikiization review tasks to display', '.wikify/queues/wikiization-tasks.json'))
    validation = _read_optional_json(validation_report_path(root), schema_version=SCHEMA_VERSIONS['object_validation'], code='views_validation_report_invalid')
    return {
        'workspace': workspace,
        'registry': registry,
        'source_items': source_items,
        'ingest_queue': ingest_queue,
        'wikiization_tasks': wikiization_tasks,
        'validation_report': validation,
        'graph': _load_graph_artifacts(root, warnings),
    }


def _load_graph_artifacts(root: Path, warnings: list[dict]) -> dict:
    graph_dir = root / 'graph'
    paths = {
        'json': graph_dir / 'graph.json',
        'report': graph_dir / 'GRAPH_REPORT.md',
        'html': graph_dir / 'graph.html',
    }
    existing = {key: path.relative_to(root).as_posix() for key, path in paths.items() if path.exists()}
    if not existing:
        warnings.append(_warning('graph_artifacts_missing', 'graph artifacts are missing; run wikify graph to populate graph entry links', 'graph/'))
    return {'paths': existing}


def _warning(code: str, message: str, path: str | None = None) -> dict:
    return {'code': code, 'message': message, 'path': path}


def _group_objects(objects: list[dict]) -> dict:
    groups = {}
    for obj in objects:
        object_type = obj.get('type') or obj.get('object_type') or 'unknown'
        groups.setdefault(object_type, []).append(obj)
    for values in groups.values():
        values.sort(key=_object_sort_key)
    return groups


def _object_sort_key(obj: dict) -> tuple[str, str, str]:
    return (obj.get('updated_at') or obj.get('timestamp') or '', obj.get('title') or '', obj.get('id') or '')


def _sources(snapshot: dict) -> list[dict]:
    sources = list((snapshot.get('registry') or {}).get('sources', {}).values())
    sources.sort(key=lambda source: source.get('source_id') or '')
    return sources


def _source_items_by_source(snapshot: dict) -> dict:
    document = snapshot.get('source_items') or {}
    grouped = {}
    for item in (document.get('items') or {}).values():
        grouped.setdefault(item.get('source_id'), []).append(item)
    for items in grouped.values():
        items.sort(key=lambda item: (item.get('relative_path') or item.get('locator') or '', item.get('item_id') or ''))
    return grouped


def _pages_by_source(pages: list[dict]) -> dict:
    grouped = {}
    for page in pages:
        for ref in page.get('source_refs') or []:
            if isinstance(ref, dict) and ref.get('source_id'):
                grouped.setdefault(ref['source_id'], []).append(page)
    for values in grouped.values():
        values.sort(key=_object_sort_key)
    return grouped


def _tasks_by_source(snapshot: dict) -> dict:
    tasks = (snapshot.get('wikiization_tasks') or {}).get('tasks') or []
    grouped = {}
    for task in tasks:
        grouped.setdefault(task.get('source_id'), []).append(task)
    for values in grouped.values():
        values.sort(key=lambda task: task.get('id') or '')
    return grouped


def _citations_by_source(groups: dict) -> dict:
    grouped = {}
    for citation in groups.get('citation', []):
        grouped.setdefault(citation.get('source_id'), []).append(citation)
    for values in grouped.values():
        values.sort(key=lambda citation: citation.get('id') or '')
    return grouped


def _safe_title(obj: dict) -> str:
    return str(obj.get('title') or obj.get('id') or 'Untitled')


def _slug(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or 'view'


def _view_id(path: str) -> str:
    return f'view_{_stable_digest(path)[:16]}'


def _view_document(path: str, title: str, body: str, *, kind: str, source_object_ids: list[str] | None = None) -> dict:
    return {
        'id': _view_id(path),
        'type': 'view',
        'title': title,
        'path': path,
        'kind': kind,
        'body': body,
        'source_object_ids': list(source_object_ids or []),
    }


def _render_view_markdown(view: dict, now: str) -> str:
    metadata = {
        'schema_version': VIEW_DOCUMENT_SCHEMA_VERSION,
        'id': view['id'],
        'type': 'view',
        'title': view['title'],
        'view_path': view['path'],
        'source_object_ids': view.get('source_object_ids') or [],
        'generated_at': now,
    }
    return render_markdown_with_front_matter(metadata, view['body'])


def _link(label: str, target: str) -> str:
    return f'[{label}]({target})'


def _markdown_rel(source_path: str, target_path: str) -> str:
    if not target_path:
        return '#'
    source_dir = posixpath.dirname(source_path)
    rel = posixpath.relpath(target_path, source_dir or '.')
    if not rel.startswith('.'):
        return rel
    return rel


def _wiki_page_link(source_view_path: str, page: dict) -> str:
    target = page.get('body_path') or page.get('relative_path')
    if not target:
        return page.get('id') or 'unknown'
    return _link(_safe_title(page), _markdown_rel(source_view_path, target))


def _source_ref_text(ref: dict) -> str:
    pieces = []
    for key in ('source_id', 'item_id', 'relative_path', 'locator'):
        value = ref.get(key)
        if value:
            pieces.append(f'{key}={value}')
    confidence = ref.get('confidence')
    if confidence is not None:
        pieces.append(f'confidence={confidence}')
    return ', '.join(pieces) or 'source reference'


def _build_views(root: Path, groups: dict, snapshot: dict, warnings: list[dict]) -> list[dict]:
    pages = groups.get('wiki_page', [])
    sources = _sources(snapshot)
    source_items = _source_items_by_source(snapshot)
    pages_by_source = _pages_by_source(pages)
    tasks_by_source = _tasks_by_source(snapshot)
    citations_by_source = _citations_by_source(groups)
    views = []
    views.append(_home_view(groups, sources, warnings))
    views.append(_pages_view(pages))
    views.extend(_source_views(sources, source_items, pages_by_source, tasks_by_source, citations_by_source))
    views.extend(_collection_views(groups))
    views.append(_timeline_view(groups.get('timeline_entry', [])))
    views.append(_graph_view(snapshot.get('graph') or {}))
    views.append(_review_view(snapshot, warnings, []))
    return _filter_views(views, 'all')


def _filter_views(views: list[dict], section: str) -> list[dict]:
    if section == 'all':
        return views
    if section == 'home':
        return [view for view in views if view['path'] == 'views/index.md']
    if section == 'collections':
        return [view for view in views if view['kind'] in COLLECTION_TYPES or view['kind'] == 'collections']
    return [view for view in views if view['kind'] == section]


def _home_view(groups: dict, sources: list[dict], warnings: list[dict]) -> dict:
    pages = groups.get('wiki_page', [])
    recent = sorted(pages, key=lambda page: page.get('updated_at') or '', reverse=True)[:10]
    lines = [
        '# Wikify',
        '',
        '## Recent Updates',
        '',
    ]
    if recent:
        lines.extend(f'- {_link(_safe_title(page), _markdown_rel("views/index.md", page.get("body_path") or page.get("relative_path") or ""))}' for page in recent)
    else:
        lines.append('- No generated pages yet.')
    lines.extend([
        '',
        '## Sources',
        '',
        f'- Registered sources: {len(sources)}',
        '',
        '## Pages',
        '',
        f'- Wiki pages: {len(pages)}',
        '',
        '## Entry Points',
        '',
        f'- {_link("Pages", "pages.md")}',
        f'- {_link("Sources", "sources/index.md")}',
        f'- {_link("Topics", "topics/index.md")}',
        f'- {_link("Projects", "projects/index.md")}',
        f'- {_link("People", "people/index.md")}',
        f'- {_link("Decisions", "decisions/index.md")}',
        f'- {_link("Graph", "graph.md")}',
        f'- {_link("Timeline", "timeline.md")}',
        f'- {_link("Review", "review.md")}',
        '',
        '## Review',
        '',
        f'- Warnings: {len(warnings)}',
    ])
    return _view_document('views/index.md', 'Wikify', '\n'.join(lines) + '\n', kind='home')


def _pages_view(pages: list[dict]) -> dict:
    lines = ['# Pages', '']
    if not pages:
        lines.append('No wiki pages have been generated yet.')
    for page in pages:
        lines.extend([
            f'## {_safe_title(page)}',
            '',
            f'- Object id: `{page.get("id")}`',
            f'- Review status: `{page.get("review_status")}`',
            f'- Confidence: `{page.get("confidence")}`',
            f'- Updated: `{page.get("updated_at")}`',
            f'- Page: {_wiki_page_link("views/pages.md", page)}',
        ])
        refs = [_source_ref_text(ref) for ref in page.get('source_refs') or [] if isinstance(ref, dict)]
        if refs:
            lines.append('- Source refs:')
            lines.extend(f'  - {ref}' for ref in refs)
        lines.append('')
    return _view_document('views/pages.md', 'Pages', '\n'.join(lines).rstrip() + '\n', kind='pages', source_object_ids=[page.get('id') for page in pages if page.get('id')])


def _source_views(sources: list[dict], source_items: dict, pages_by_source: dict, tasks_by_source: dict, citations_by_source: dict) -> list[dict]:
    index_lines = ['# Sources', '']
    if not sources:
        index_lines.append('No sources have been registered yet.')
    for source in sources:
        source_id = source.get('source_id')
        index_lines.append(f'- {_link(source_id or "source", f"{source_id}.md")} - {source.get("type")} - {source.get("locator")}')
    views = [_view_document('views/sources/index.md', 'Sources', '\n'.join(index_lines).rstrip() + '\n', kind='sources')]
    for source in sources:
        source_id = source.get('source_id') or 'unknown-source'
        path = f'views/sources/{source_id}.md'
        lines = [
            f'# Source {source_id}',
            '',
            f'- Type: `{source.get("type")}`',
            f'- Locator: `{source.get("locator")}`',
            f'- Last sync status: `{source.get("last_sync_status")}`',
            '',
            '## Source Items',
            '',
        ]
        items = source_items.get(source_id, [])
        if items:
            lines.extend(f'- `{item.get("item_id")}` status=`{item.get("status")}` path=`{item.get("relative_path") or item.get("locator")}`' for item in items)
        else:
            lines.append('- No synced source items recorded.')
        lines.extend(['', '## Contributed Pages', ''])
        pages = pages_by_source.get(source_id, [])
        if pages:
            lines.extend(f'- {_wiki_page_link(path, page)}' for page in pages)
        else:
            lines.append('- No generated pages cite this source.')
        lines.extend(['', '## Citations', ''])
        citations = citations_by_source.get(source_id, [])
        if citations:
            lines.extend(f'- `{citation.get("id")}` locator=`{citation.get("locator")}` confidence=`{citation.get("confidence")}`' for citation in citations)
        else:
            lines.append('- No citation objects cite this source.')
        lines.extend(['', '## Unresolved Issues', ''])
        tasks = tasks_by_source.get(source_id, [])
        if tasks:
            lines.extend(f'- `{task.get("id")}` reason=`{task.get("reason_code")}` status=`{task.get("status")}`' for task in tasks)
        else:
            lines.append('- No unresolved wikiization tasks for this source.')
        views.append(_view_document(path, f'Source {source_id}', '\n'.join(lines).rstrip() + '\n', kind='sources', source_object_ids=[page.get('id') for page in pages if page.get('id')]))
    return views


def _collection_views(groups: dict) -> list[dict]:
    views = []
    for object_type in COLLECTION_TYPES:
        objects = groups.get(object_type, [])
        directory = 'people' if object_type == 'person' else f'{object_type}s'
        index_path = f'views/{directory}/index.md'
        title = directory.title()
        lines = [f'# {title}', '']
        if not objects:
            lines.append(f'No {object_type} objects exist yet. Run future semantic enrichment to create source-backed {object_type} objects.')
        for obj in objects:
            detail_path = f'{obj.get("id") or _slug(_safe_title(obj))}.md'
            lines.append(f'- {_link(_safe_title(obj), detail_path)} - {obj.get("summary") or ""}')
        views.append(_view_document(index_path, title, '\n'.join(lines).rstrip() + '\n', kind=object_type, source_object_ids=[obj.get('id') for obj in objects if obj.get('id')]))
        for obj in objects:
            detail = _collection_detail_view(object_type, directory, obj)
            views.append(detail)
    return views


def _collection_detail_view(object_type: str, directory: str, obj: dict) -> dict:
    path = f'views/{directory}/{obj.get("id") or _slug(_safe_title(obj))}.md'
    lines = [
        f'# {_safe_title(obj)}',
        '',
        obj.get('summary') or 'No summary recorded.',
        '',
        '## Related Pages',
        '',
    ]
    page_ids = obj.get('page_ids') or []
    if page_ids:
        lines.extend(f'- `{page_id}`' for page_id in page_ids)
    else:
        lines.append('- No related pages recorded.')
    lines.extend(['', '## Source References', ''])
    refs = obj.get('source_refs') or []
    if refs:
        lines.extend(f'- {_source_ref_text(ref)}' for ref in refs if isinstance(ref, dict))
    else:
        lines.append('- No source references recorded.')
    if object_type == 'decision':
        lines.extend(['', '## Status', '', f'`{obj.get("status")}`'])
    return _view_document(path, _safe_title(obj), '\n'.join(lines).rstrip() + '\n', kind=object_type, source_object_ids=[obj.get('id')] if obj.get('id') else [])


def _timeline_view(entries: list[dict]) -> dict:
    lines = ['# Timeline', '']
    if not entries:
        lines.append('No timeline entries exist yet.')
    for entry in sorted(entries, key=lambda item: item.get('timestamp') or ''):
        lines.extend([
            f'## {entry.get("timestamp") or "Unknown time"} - {_safe_title(entry)}',
            '',
            entry.get('summary') or 'No summary recorded.',
            '',
        ])
    return _view_document('views/timeline.md', 'Timeline', '\n'.join(lines).rstrip() + '\n', kind='timeline', source_object_ids=[entry.get('id') for entry in entries if entry.get('id')])


def _graph_view(graph: dict) -> dict:
    paths = graph.get('paths') or {}
    lines = ['# Graph', '']
    if paths:
        if paths.get('report'):
            lines.append(f'- {_link("Graph report", _markdown_rel("views/graph.md", paths["report"]))}')
        if paths.get('json'):
            lines.append(f'- {_link("Graph JSON", _markdown_rel("views/graph.md", paths["json"]))}')
        if paths.get('html'):
            lines.append(f'- {_link("Graph HTML", _markdown_rel("views/graph.md", paths["html"]))}')
    else:
        lines.extend([
            'Graph artifacts are not available yet.',
            '',
            'Next action: `wikify graph`',
        ])
    return _view_document('views/graph.md', 'Graph', '\n'.join(lines).rstrip() + '\n', kind='graph')


def _review_view(snapshot: dict, warnings: list[dict], conflicts: list[dict]) -> dict:
    validation = snapshot.get('validation_report') or {}
    records = validation.get('records') or []
    wikiization_tasks = (snapshot.get('wikiization_tasks') or {}).get('tasks') or []
    lines = ['# Review', '', '## Warnings', '']
    if warnings:
        lines.extend(f'- `{warning.get("code")}` {warning.get("message")}' for warning in warnings)
    else:
        lines.append('- No warnings.')
    lines.extend(['', '## Validation Records', ''])
    if records:
        lines.extend(f'- `{record.get("severity")}` `{record.get("code")}` {record.get("message")} ({record.get("path")})' for record in records)
    else:
        lines.append('- No validation records.')
    lines.extend(['', '## Wikiization Tasks', ''])
    if wikiization_tasks:
        lines.extend(f'- `{task.get("id")}` reason=`{task.get("reason_code")}` status=`{task.get("status")}`' for task in wikiization_tasks)
    else:
        lines.append('- No wikiization tasks.')
    lines.extend(['', '## View Conflicts', ''])
    if conflicts:
        lines.extend(f'- `{conflict.get("path")}` reason=`{conflict.get("reason_code")}`' for conflict in conflicts)
    else:
        lines.append('- No view conflicts.')
    return _view_document('views/review.md', 'Review', '\n'.join(lines).rstrip() + '\n', kind='review')


def _html_path_for_view(view_path: str) -> str:
    relative = view_path.removeprefix('views/')
    if relative == 'index.md':
        return 'views/site/index.html'
    return f'views/site/{relative[:-3]}.html'


def _planned_html(views: list[dict]) -> list[dict]:
    return [{'path': _html_path_for_view(view['path']), 'source_path': view['path']} for view in views]


def _summary(views: list[dict], html_items: list[dict], groups: dict, sources: list[dict], warnings: list[dict], conflicts: list[dict]) -> dict:
    return {
        'planned_view_count': len(views),
        'planned_html_count': len(html_items),
        'generated_view_count': 0,
        'generated_html_count': 0,
        'source_count': len(sources),
        'object_counts_by_type': {key: len(value) for key, value in sorted(groups.items())},
        'warning_count': len(warnings),
        'conflict_count': len(conflicts),
    }


def _artifacts(root: Path) -> dict:
    return {
        'views': 'views',
        'site': 'views/site',
        'site_css': 'views/site/assets/style.css',
        'views_report': views_report_path(root).relative_to(root).as_posix(),
        'views_manifest': views_manifest_path(root).relative_to(root).as_posix(),
        'view_tasks': view_task_queue_path(root).relative_to(root).as_posix(),
    }


def _next_actions(warnings: list[dict], conflicts: list[dict]) -> list[str]:
    actions = []
    if any(warning.get('code') == 'graph_artifacts_missing' for warning in warnings):
        actions.append('run_wikify_graph')
    if conflicts:
        actions.append('review_view_tasks')
    return actions


def _validate_before_write(root: Path) -> dict:
    result = validate_workspace_objects(root, path=object_artifacts_dir(root), strict=True, write_report=True)
    if result.get('summary', {}).get('error_count', 0):
        raise ViewGenerationError(
            'object validation failed before view generation',
            code='views_validation_failed',
            details={'validation': result},
        )
    return result


def _can_write_generated(path: Path, relative_path: str, manifest: dict) -> tuple[bool, str | None]:
    if not path.exists():
        return True, None
    previous = (manifest.get('files') or {}).get(relative_path) or {}
    expected_hash = previous.get('sha256')
    if expected_hash and expected_hash == _sha256(path.read_text(encoding='utf-8')):
        return True, None
    return False, 'generated_view_drifted'


def _make_task(path: str, reason_code: str, now: str) -> dict:
    task_id = f'view-task-{_stable_digest(path, reason_code)[:16]}'
    return {
        'id': task_id,
        'schema_version': VIEW_TASK_QUEUE_SCHEMA_VERSION,
        'created_at': now,
        'updated_at': now,
        'target_paths': {'view_path': path},
        'reason_code': reason_code,
        'message': reason_code,
        'evidence': {'path': path},
        'agent_instructions': [
            'Inspect the generated view and its manifest entry.',
            'Preserve user edits unless an explicit patch/apply flow approves replacement.',
            'Regenerate the view only when the manifest hash or user decision makes it safe.',
        ],
        'acceptance_checks': [
            'The visible view remains human-readable.',
            'User-edited content is not overwritten silently.',
            'The view manifest matches any regenerated view file.',
        ],
        'requires_user': False,
        'status': 'queued',
    }


def _write_task_queue(root: Path, tasks: list[dict], now: str):
    if not tasks:
        return
    queue = _load_task_queue(root)
    by_id = {task.get('id'): task for task in queue.get('tasks', [])}
    for task in tasks:
        by_id[task['id']] = task
    tasks_sorted = sorted(by_id.values(), key=lambda task: task.get('id') or '')
    by_reason = {}
    for task in tasks_sorted:
        reason = task.get('reason_code') or 'unknown'
        by_reason[reason] = by_reason.get(reason, 0) + 1
    document = {
        'schema_version': VIEW_TASK_QUEUE_SCHEMA_VERSION,
        'generated_at': now,
        'summary': {'task_count': len(tasks_sorted), 'by_reason': dict(sorted(by_reason.items()))},
        'tasks': tasks_sorted,
    }
    _write_json_atomic(view_task_queue_path(root), document)


def _write_views(root: Path, views: list[dict], manifest: dict, now: str) -> tuple[list[dict], list[dict], list[dict]]:
    generated = []
    conflicts = []
    tasks = []
    for view in views:
        relative_path = view['path']
        target = root / relative_path
        can_write, reason = _can_write_generated(target, relative_path, manifest)
        if not can_write:
            conflict = {'path': relative_path, 'reason_code': reason or 'generated_view_drifted'}
            conflicts.append(conflict)
            tasks.append(_make_task(relative_path, conflict['reason_code'], now))
            continue
        markdown = _render_view_markdown(view, now)
        _write_text_atomic(target, markdown)
        generated.append({'path': relative_path, 'sha256': _sha256(markdown), 'kind': 'markdown'})
    return generated, conflicts, tasks


def _write_manifest(root: Path, manifest: dict, generated_files: list[dict], now: str):
    files = dict(manifest.get('files') or {})
    for generated in generated_files:
        files[generated['path']] = {
            'sha256': generated['sha256'],
            'kind': generated.get('kind'),
            'generated_at': now,
        }
    document = {
        'schema_version': VIEWS_MANIFEST_SCHEMA_VERSION,
        'generated_at': now,
        'files': dict(sorted(files.items())),
    }
    _write_json_atomic(views_manifest_path(root), document)


def _convert_link_target(root: Path, markdown_path: str, html_path: str, target: str) -> str:
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
        return target
    markdown_abs = root / markdown_path
    target_abs = (markdown_abs.parent / target).resolve(strict=False)
    if target.endswith('.md') and _is_relative_to(target_abs, root / 'views'):
        view_rel = target_abs.relative_to(root / 'views').as_posix()
        html_target = root / 'views' / 'site' / (view_rel[:-3] + '.html')
    else:
        html_target = target_abs
    return posixpath.relpath(html_target, (root / html_path).parent)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _render_inline(text: str, root: Path, markdown_path: str, html_path: str) -> str:
    parts = []
    index = 0
    pattern = re.compile(r'(`[^`]+`)|(\[([^\]]+)\]\(([^)]+)\))')
    for match in pattern.finditer(text):
        parts.append(html.escape(text[index:match.start()]))
        code = match.group(1)
        if code:
            parts.append(f'<code>{html.escape(code[1:-1])}</code>')
        else:
            label = html.escape(match.group(3))
            target = html.escape(_convert_link_target(root, markdown_path, html_path, match.group(4)), quote=True)
            parts.append(f'<a href="{target}">{label}</a>')
        index = match.end()
    parts.append(html.escape(text[index:]))
    return ''.join(parts)


def _markdown_body_to_html(markdown: str, root: Path, markdown_path: str, html_path: str) -> str:
    _metadata, body = split_front_matter(markdown)
    lines = body.splitlines()
    blocks = []
    in_list = False
    in_code = False
    code_lines = []
    paragraph = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            text = ' '.join(paragraph)
            blocks.append(f'<p>{_render_inline(text, root, markdown_path, html_path)}</p>')
            paragraph = []

    def close_list():
        nonlocal in_list
        if in_list:
            blocks.append('</ul>')
            in_list = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            flush_paragraph()
            close_list()
            if in_code:
                blocks.append(f'<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>')
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            flush_paragraph()
            close_list()
            continue
        heading = re.match(r'^(#{1,3})\s+(.+)$', stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            blocks.append(f'<h{level}>{_render_inline(heading.group(2), root, markdown_path, html_path)}</h{level}>')
            continue
        if stripped.startswith('- '):
            flush_paragraph()
            if not in_list:
                blocks.append('<ul>')
                in_list = True
            blocks.append(f'<li>{_render_inline(stripped[2:], root, markdown_path, html_path)}</li>')
            continue
        paragraph.append(stripped)
    flush_paragraph()
    close_list()
    if in_code:
        blocks.append(f'<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>')
    return '\n'.join(blocks)


def _css_href(root: Path, html_path: str) -> str:
    css_path = root / 'views' / 'site' / 'assets' / 'style.css'
    return posixpath.relpath(css_path, (root / html_path).parent)


def _html_document(title: str, body_html: str, root: Path, html_path: str) -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{html.escape(_css_href(root, html_path), quote=True)}">
</head>
<body>
  <main>
{body_html}
  </main>
</body>
</html>
'''


def _style_css() -> str:
    return '''body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
  color: #202124;
  background: #fbfbf8;
}

main {
  max-width: 920px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}

h1, h2, h3 {
  line-height: 1.2;
  margin-top: 1.6em;
}

a {
  color: #0b57d0;
}

code, pre {
  background: #eeeeea;
  border-radius: 4px;
}

code {
  padding: 0.1rem 0.25rem;
}

pre {
  padding: 1rem;
  overflow: auto;
}

li {
  margin: 0.25rem 0;
}
'''


def _write_html(root: Path, views: list[dict], generated_markdown: list[dict], now: str) -> list[dict]:
    generated_paths = {item['path'] for item in generated_markdown}
    generated_html = []
    for view in views:
        if view['path'] not in generated_paths:
            continue
        markdown_path = root / view['path']
        markdown = markdown_path.read_text(encoding='utf-8')
        html_path = _html_path_for_view(view['path'])
        body_html = _markdown_body_to_html(markdown, root, view['path'], html_path)
        document = _html_document(view['title'], body_html, root, html_path)
        _write_text_atomic(root / html_path, document)
        generated_html.append({'path': html_path, 'sha256': _sha256(document), 'kind': 'html'})
    css_path = root / 'views' / 'site' / 'assets' / 'style.css'
    css = _style_css()
    _write_text_atomic(css_path, css)
    generated_html.append({'path': css_path.relative_to(root).as_posix(), 'sha256': _sha256(css), 'kind': 'css'})
    return generated_html


def run_view_generation(
    base: Path | str,
    *,
    dry_run: bool = False,
    include_html: bool = True,
    section: str = 'all',
) -> dict:
    if section not in SECTION_CHOICES:
        raise ViewGenerationError('view section is invalid', code='views_section_invalid', details={'section': section})
    root = _root(base)
    now = _utc_now()
    warnings: list[dict] = []
    load_workspace(root)
    _load_object_index(root, warnings)
    objects = _load_object_documents(root)
    groups = _group_objects(objects)
    snapshot = _load_workspace_snapshot(root, warnings)
    validation = None
    if not dry_run:
        validation = _validate_before_write(root)
        snapshot['validation_report'] = validation
    views = _filter_views(_build_views(root, groups, snapshot, warnings), section)
    html_items = _planned_html(views) if include_html else []
    sources = _sources(snapshot)
    conflicts: list[dict] = []
    generated_markdown: list[dict] = []
    generated_html: list[dict] = []

    result = {
        'schema_version': VIEWS_RUN_SCHEMA_VERSION,
        'base': str(root),
        'workspace_id': (snapshot.get('workspace') or {}).get('workspace', {}).get('workspace_id'),
        'generated_at': now,
        'status': 'dry_run' if dry_run else 'completed',
        'dry_run': dry_run,
        'selection': {'section': section, 'include_html': include_html},
        'summary': _summary(views, html_items, groups, sources, warnings, conflicts),
        'artifacts': _artifacts(root),
        'views': [{'path': view['path'], 'title': view['title'], 'kind': view['kind']} for view in views],
        'html': html_items,
        'validation': None,
        'warnings': warnings,
        'conflicts': [],
        'next_actions': _next_actions(warnings, conflicts),
    }
    if dry_run:
        return result

    manifest = _load_manifest(root)
    generated_markdown, conflicts, conflict_tasks = _write_views(root, views, manifest, now)
    if include_html:
        generated_html = _write_html(root, views, generated_markdown, now)
    all_generated = generated_markdown + generated_html
    _write_manifest(root, manifest, all_generated, now)
    _write_task_queue(root, conflict_tasks, now)
    result['validation'] = validation
    result['conflicts'] = conflicts
    result['summary'] = _summary(views, html_items, groups, sources, warnings, conflicts)
    result['summary']['generated_view_count'] = len(generated_markdown)
    result['summary']['generated_html_count'] = len(generated_html)
    result['status'] = 'completed_with_conflicts' if conflicts else 'completed'
    result['next_actions'] = _next_actions(warnings, conflicts)
    result['generated'] = all_generated
    result['html'] = generated_html if include_html else []
    _write_json_atomic(views_report_path(root), result)
    return result
