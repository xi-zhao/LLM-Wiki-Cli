import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from wikify.frontmatter import FrontMatterError, split_front_matter
from wikify.markdown_index import SCOPE_DIRS, scan_objects
from wikify.objects import (
    GRAPH_PROVENANCE_VALUES,
    OBJECT_TYPES,
    REQUIRED_FIELDS,
    REVIEW_STATUSES,
    SCHEMA_VERSIONS,
    object_artifacts_dir,
    stable_object_id,
)
from wikify.sync import SOURCE_ITEMS_SCHEMA_VERSION, source_items_path
from wikify.workspace import WorkspaceError, load_workspace, manifest_path, registry_path


OBJECT_VALIDATION_SCHEMA_VERSION = "wikify.object-validation.v1"

RECOGNIZED_OBJECT_SCHEMAS = {
    SOURCE_ITEMS_SCHEMA_VERSION: 'source_item',
    SCHEMA_VERSIONS['wiki_page']: 'wiki_page',
    SCHEMA_VERSIONS['topic']: 'topic',
    SCHEMA_VERSIONS['project']: 'project',
    SCHEMA_VERSIONS['person']: 'person',
    SCHEMA_VERSIONS['decision']: 'decision',
    SCHEMA_VERSIONS['timeline_entry']: 'timeline_entry',
    SCHEMA_VERSIONS['citation']: 'citation',
    SCHEMA_VERSIONS['graph_edge']: 'graph_edge',
    SCHEMA_VERSIONS['context_pack']: 'context_pack',
}

VALIDATION_RECORD_FIELDS = ('code', 'message', 'path', 'object_id', 'field', 'severity', 'details')


@dataclass(frozen=True)
class ValidationRecord:
    code: str
    message: str
    path: str | None
    object_id: str | None
    field: str | None
    severity: str
    details: dict

    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'message': self.message,
            'path': self.path,
            'object_id': self.object_id,
            'field': self.field,
            'severity': self.severity,
            'details': dict(self.details),
        }


def validation_report_path(base: Path | str) -> Path:
    return Path(base).expanduser() / 'artifacts' / 'objects' / 'validation.json'


def write_validation_report(base: Path | str, result: dict) -> Path:
    path = validation_report_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp_path.replace(path)
    return path


def validate_workspace_objects(
    base: Path | str,
    path: Path | str | None = None,
    strict: bool = False,
    write_report: bool = False,
) -> dict:
    root = Path(base).expanduser()
    root_resolved = root.resolve()
    records: list[ValidationRecord] = []

    focus = _resolve_focus(root_resolved, path, records)
    entries = _collect_entries(root_resolved, focus, records)
    entries = _collapse_artifact_body_entries(entries)

    source_ids = _load_source_ids(root_resolved)
    item_ids = _load_source_item_ids(root_resolved, records)
    known_ids = {entry['object_id'] for entry in entries if entry.get('object_id')}

    _validate_duplicate_ids(entries, records)
    for entry in entries:
        _validate_entry(entry, known_ids, source_ids, item_ids, strict, records)

    record_dicts = [record.to_dict() for record in records]
    error_count = sum(1 for record in record_dicts if record['severity'] == 'error')
    warning_count = sum(1 for record in record_dicts if record['severity'] == 'warning')
    status = 'failed' if error_count else ('warnings' if warning_count else 'passed')
    result = {
        'schema_version': OBJECT_VALIDATION_SCHEMA_VERSION,
        'base': str(root_resolved),
        'path': str(focus) if focus else None,
        'strict': strict,
        'status': status,
        'summary': {
            'object_count': len(entries),
            'record_count': len(record_dicts),
            'error_count': error_count,
            'warning_count': warning_count,
        },
        'records': record_dicts,
        'artifacts': {},
    }
    if write_report:
        report_path = validation_report_path(root)
        result['artifacts']['validation_report'] = str(report_path)
        write_validation_report(root, result)
    return result


def _resolve_focus(root: Path, path: Path | str | None, records: list[ValidationRecord]) -> Path | None:
    if path is None:
        return None
    focus = Path(path).expanduser()
    if not focus.is_absolute():
        focus = root / focus
    try:
        resolved = focus.resolve()
    except OSError:
        resolved = focus
    if not _is_relative_to(resolved, root):
        records.append(_record(
            'object_schema_invalid',
            'validation path is outside the workspace',
            str(focus),
            None,
            'path',
            'error',
            {'base': str(root)},
        ))
    return resolved


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _collect_entries(root: Path, focus: Path | None, records: list[ValidationRecord]) -> list[dict]:
    if focus and records and records[-1].field == 'path':
        return []
    if focus:
        paths = _focused_paths(focus)
        return _entries_from_paths(root, paths, records)

    paths = []
    artifact_root = object_artifacts_dir(root)
    if artifact_root.exists():
        paths.extend(
            path
            for path in sorted(artifact_root.rglob('*.json'))
            if path.name not in {'object-index.json', 'validation.json'}
        )
    entries = _entries_from_paths(root, paths, records)
    entries.extend(_entries_from_markdown_index(root, records))
    return entries


def _focused_paths(focus: Path) -> list[Path]:
    if focus.is_file():
        return [focus]
    if focus.is_dir():
        return sorted(
            path
            for path in focus.rglob('*')
            if path.suffix in {'.json', '.md'} and path.name not in {'object-index.json', 'validation.json'}
        )
    return [focus]


def _entries_from_paths(root: Path, paths: list[Path], records: list[ValidationRecord]) -> list[dict]:
    entries = []
    for item_path in paths:
        if item_path.suffix == '.json':
            entry = _entry_from_json(root, item_path, records)
        elif item_path.suffix == '.md':
            entry = _entry_from_markdown_file(root, item_path, records)
        else:
            entry = None
        if entry:
            entries.append(entry)
    return entries


def _entry_from_json(root: Path, path: Path, records: list[ValidationRecord]) -> dict | None:
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        records.append(_record(
            'object_schema_invalid',
            'object JSON artifact is invalid',
            _display_path(root, path),
            None,
            'schema_version',
            'error',
            {'error': str(exc)},
        ))
        return None
    if not isinstance(document, dict):
        records.append(_record(
            'object_schema_invalid',
            'object JSON artifact must be a record',
            _display_path(root, path),
            None,
            'schema_version',
            'error',
            {},
        ))
        return None
    return _entry(root, path, document, 'json')


def _entries_from_markdown_index(root: Path, records: list[ValidationRecord]) -> list[dict]:
    entries = []
    for obj in scan_objects(root):
        if obj.relative_path.startswith('sources/raw/'):
            continue
        if obj.metadata.get('_frontmatter_error'):
            error = obj.metadata['_frontmatter_error']
            records.append(_record(
                'object_frontmatter_invalid',
                error.get('message') or 'front matter is invalid',
                obj.relative_path,
                obj.object_id,
                'frontmatter',
                'error',
                error.get('details') or {},
            ))
            continue
        if not obj.metadata:
            records.append(_record(
                'object_required_field_missing',
                'legacy Markdown file has no object front matter',
                obj.relative_path,
                stable_object_id(obj.canonical_type if obj.canonical_type != 'source' else 'wiki_page', obj.relative_path),
                'frontmatter',
                'warning',
                {'legacy_type': obj.type, 'canonical_type': obj.canonical_type},
            ))
            continue
        document = dict(obj.metadata)
        document.setdefault('relative_path', obj.relative_path)
        entries.append({
            'document': document,
            'path': obj.relative_path,
            'source': 'markdown',
            'object_id': obj.object_id or document.get('id'),
        })
    return entries


def _entry_from_markdown_file(root: Path, path: Path, records: list[ValidationRecord]) -> dict | None:
    try:
        text = path.read_text(encoding='utf-8')
        metadata, _body = split_front_matter(text)
    except (OSError, FrontMatterError) as exc:
        code = getattr(exc, 'code', 'object_frontmatter_invalid')
        details = getattr(exc, 'details', {})
        records.append(_record(
            code,
            str(exc),
            _display_path(root, path),
            None,
            'frontmatter',
            'error',
            details,
        ))
        return None
    if not metadata:
        scope_type = _canonical_type_for_path(root, path)
        records.append(_record(
            'object_required_field_missing',
            'legacy Markdown file has no object front matter',
            _display_path(root, path),
            stable_object_id(scope_type if scope_type != 'source' else 'wiki_page', _display_path(root, path)),
            'frontmatter',
            'warning',
            {'canonical_type': scope_type},
        ))
        return None
    metadata = dict(metadata)
    metadata.setdefault('relative_path', _display_path(root, path))
    return {
        'document': metadata,
        'path': _display_path(root, path),
        'source': 'markdown',
        'object_id': metadata.get('id'),
    }


def _canonical_type_for_path(root: Path, path: Path) -> str:
    for scope, parts in SCOPE_DIRS.items():
        scope_root = root.joinpath(*parts)
        if _is_relative_to(path.resolve(), scope_root.resolve()):
            from wikify.objects import legacy_scope_to_object_type

            return legacy_scope_to_object_type(scope)
    return 'wiki_page'


def _entry(root: Path, path: Path, document: dict, source: str) -> dict:
    return {
        'document': document,
        'path': _display_path(root, path),
        'source': source,
        'object_id': document.get('id'),
    }


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _load_source_ids(root: Path) -> set[str] | None:
    if not manifest_path(root).exists() and not registry_path(root).exists():
        return None
    try:
        workspace = load_workspace(root)
    except WorkspaceError:
        return set()
    return set((workspace.get('registry') or {}).get('sources', {}).keys())


def _load_source_item_ids(root: Path, records: list[ValidationRecord]) -> set[str] | None:
    path = source_items_path(root)
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        records.append(_record(
            'object_source_ref_unresolved',
            'source item index JSON is invalid',
            _display_path(root, path),
            None,
            'item_id',
            'error',
            {'error': str(exc)},
        ))
        return set()
    if document.get('schema_version') != SOURCE_ITEMS_SCHEMA_VERSION or not isinstance(document.get('items'), dict):
        records.append(_record(
            'object_source_ref_unresolved',
            'source item index schema is invalid',
            _display_path(root, path),
            None,
            'item_id',
            'error',
            {'schema_version': document.get('schema_version')},
        ))
        return set()
    return set(document['items'].keys())


def _collapse_artifact_body_entries(entries: list[dict]) -> list[dict]:
    artifact_body_refs = {
        (entry.get('object_id'), body_path)
        for entry in entries
        if entry.get('source') == 'json'
        for body_path in (
            entry.get('document', {}).get('body_path'),
            entry.get('document', {}).get('relative_path'),
        )
        if body_path
    }
    return [
        entry
        for entry in entries
        if not (
            entry.get('source') == 'markdown'
            and (entry.get('object_id'), entry.get('path')) in artifact_body_refs
        )
    ]


def _validate_duplicate_ids(entries: list[dict], records: list[ValidationRecord]):
    seen = {}
    for entry in entries:
        object_id = entry.get('object_id')
        if not object_id:
            continue
        if object_id in seen:
            records.append(_record(
                'object_duplicate_id',
                'object id is duplicated',
                entry['path'],
                object_id,
                'id',
                'error',
                {'first_path': seen[object_id], 'duplicate_path': entry['path']},
            ))
        else:
            seen[object_id] = entry['path']


def _validate_entry(
    entry: dict,
    known_ids: set[str],
    source_ids: set[str] | None,
    item_ids: set[str] | None,
    strict: bool,
    records: list[ValidationRecord],
):
    document = entry['document']
    object_id = entry.get('object_id') or document.get('id')
    path = entry['path']
    schema_version = document.get('schema_version')
    expected_type = RECOGNIZED_OBJECT_SCHEMAS.get(schema_version)
    object_type = expected_type if expected_type == 'graph_edge' else document.get('type')
    declared = schema_version in RECOGNIZED_OBJECT_SCHEMAS

    if schema_version and schema_version not in RECOGNIZED_OBJECT_SCHEMAS:
        records.append(_record(
            'object_schema_invalid',
            'object schema version is not supported',
            path,
            object_id,
            'schema_version',
            'error',
            {'schema_version': schema_version},
        ))
    if expected_type and expected_type != 'graph_edge' and document.get('type') != expected_type:
        records.append(_record(
            'object_schema_invalid',
            'object type does not match schema version',
            path,
            object_id,
            'type',
            'error',
            {'expected': expected_type, 'actual': document.get('type')},
        ))
    if object_type not in OBJECT_TYPES and expected_type != 'graph_edge':
        records.append(_record(
            'object_schema_invalid',
            'object type is not supported',
            path,
            object_id,
            'type',
            'error',
            {'type': object_type},
        ))

    required_type = expected_type or object_type
    if declared or strict:
        for field in sorted(REQUIRED_FIELDS.get(required_type, set())):
            if field not in document or document.get(field) in (None, ''):
                records.append(_record(
                    'object_required_field_missing',
                    'required object field is missing',
                    path,
                    object_id,
                    field,
                    'error',
                    {'object_type': required_type},
                ))

    _validate_confidence(document, path, object_id, records)
    _validate_review_status(document, path, object_id, records)
    _validate_graph_provenance(document, expected_type, path, object_id, records)
    _validate_links(document, known_ids, path, object_id, records)
    _validate_source_refs(document, source_ids, item_ids, path, object_id, records)


def _validate_confidence(document: dict, path: str, object_id: str | None, records: list[ValidationRecord]):
    if 'confidence' not in document:
        return
    confidence = document.get('confidence')
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or confidence < 0.0 or confidence > 1.0:
        records.append(_record(
            'object_schema_invalid',
            'confidence must be numeric from 0.0 to 1.0',
            path,
            object_id,
            'confidence',
            'error',
            {'confidence': confidence},
        ))


def _validate_review_status(document: dict, path: str, object_id: str | None, records: list[ValidationRecord]):
    if 'review_status' not in document:
        return
    review_status = document.get('review_status')
    if review_status not in REVIEW_STATUSES:
        records.append(_record(
            'object_schema_invalid',
            'review_status is not supported',
            path,
            object_id,
            'review_status',
            'error',
            {'review_status': review_status, 'allowed': sorted(REVIEW_STATUSES)},
        ))


def _validate_graph_provenance(
    document: dict,
    expected_type: str | None,
    path: str,
    object_id: str | None,
    records: list[ValidationRecord],
):
    if expected_type != 'graph_edge' or 'provenance' not in document:
        return
    provenance = document.get('provenance')
    if provenance not in GRAPH_PROVENANCE_VALUES:
        records.append(_record(
            'object_schema_invalid',
            'graph edge provenance is not supported',
            path,
            object_id,
            'provenance',
            'error',
            {'provenance': provenance, 'allowed': sorted(GRAPH_PROVENANCE_VALUES)},
        ))


def _validate_links(document: dict, known_ids: set[str], path: str, object_id: str | None, records: list[ValidationRecord]):
    for field in ('outbound_links', 'backlinks'):
        links = document.get(field)
        if not isinstance(links, list):
            continue
        for link in links:
            target = _link_target(link)
            if target and target not in known_ids:
                records.append(_record(
                    'object_link_unresolved',
                    'object link target is unresolved',
                    path,
                    object_id,
                    field,
                    'error',
                    {'target': target},
                ))
    if document.get('schema_version') == SCHEMA_VERSIONS['graph_edge']:
        for field in ('source', 'target'):
            target = document.get(field)
            if isinstance(target, str) and target and target not in known_ids:
                records.append(_record(
                    'object_link_unresolved',
                    'graph edge endpoint is unresolved',
                    path,
                    object_id,
                    field,
                    'error',
                    {'target': target},
                ))


def _link_target(link) -> str | None:
    if isinstance(link, str):
        return link
    if isinstance(link, dict):
        for key in ('id', 'target', 'object_id'):
            value = link.get(key)
            if isinstance(value, str):
                return value
    return None


def _validate_source_refs(
    document: dict,
    source_ids: set[str] | None,
    item_ids: set[str] | None,
    path: str,
    object_id: str | None,
    records: list[ValidationRecord],
):
    source_refs = document.get('source_refs')
    if not isinstance(source_refs, list):
        return
    for index, source_ref in enumerate(source_refs):
        if not isinstance(source_ref, dict):
            records.append(_record(
                'object_source_ref_unresolved',
                'source reference must be a record',
                path,
                object_id,
                'source_refs',
                'error',
                {'index': index},
            ))
            continue
        source_id = source_ref.get('source_id')
        if source_ids is not None and source_id not in source_ids:
            records.append(_record(
                'object_source_ref_unresolved',
                'source reference source_id is unresolved',
                path,
                object_id,
                'source_refs.source_id',
                'error',
                {'index': index, 'source_id': source_id},
            ))
        item_id = source_ref.get('item_id')
        if item_id and item_ids is not None and item_id not in item_ids:
            records.append(_record(
                'object_source_ref_unresolved',
                'source reference item_id is unresolved',
                path,
                object_id,
                'source_refs.item_id',
                'error',
                {'index': index, 'item_id': item_id},
            ))


def _record(
    code: str,
    message: str,
    path: str | None,
    object_id: str | None,
    field: str | None,
    severity: str,
    details: dict,
) -> ValidationRecord:
    return ValidationRecord(
        code=code,
        message=message,
        path=path,
        object_id=object_id,
        field=field,
        severity=severity,
        details=details,
    )
