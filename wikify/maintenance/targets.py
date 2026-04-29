import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from wikify.agent import (
    agent_graph_path,
    agent_report_path,
    citation_index_path,
    page_index_path,
    related_index_path,
)
from wikify.object_validation import validation_report_path
from wikify.objects import SCHEMA_VERSIONS, object_artifacts_dir
from wikify.sync import SOURCE_ITEMS_SCHEMA_VERSION, source_items_path
from wikify.views import VIEWS_MANIFEST_SCHEMA_VERSION, VIEW_TASK_QUEUE_SCHEMA_VERSION, view_task_queue_path, views_manifest_path
from wikify.wikiize import WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION, wikiization_task_queue_path
from wikify.workspace import SOURCE_REGISTRY_SCHEMA_VERSION, registry_path


MAINTENANCE_TARGETS_SCHEMA_VERSION = 'wikify.maintenance-targets.v1'


class MaintenanceTargetError(ValueError):
    def __init__(self, message: str, code: str = 'maintenance_target_failed', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_subject(subject: str | None) -> str:
    if subject is None:
        return ''
    return Path(str(subject)).as_posix().lstrip('./')


def _read_optional_json(
    path: Path,
    schema_version: str | None = None,
    code: str = 'maintenance_target_json_invalid',
) -> dict | None:
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise MaintenanceTargetError(
            f'maintenance target JSON is invalid: {path}',
            code=code,
            details={'path': str(path)},
        ) from exc
    if not isinstance(document, dict):
        raise MaintenanceTargetError(
            f'maintenance target JSON must be an object: {path}',
            code=code,
            details={'path': str(path)},
        )
    if schema_version is not None and document.get('schema_version') != schema_version:
        raise MaintenanceTargetError(
            f'maintenance target JSON schema is unsupported: {path}',
            code=f'{code}_schema_invalid',
            details={'path': str(path), 'schema_version': document.get('schema_version')},
        )
    return document


def _warning(code: str, message: str, path: str | None = None) -> dict:
    return {'code': code, 'message': message, 'path': path}


def _object_type(document: dict) -> str:
    return document.get('object_type') or document.get('type') or 'unknown'


def _load_object_documents(root: Path) -> list[dict]:
    directory = object_artifacts_dir(root)
    if not directory.exists():
        return []
    objects = []
    for path in sorted(directory.rglob('*.json')):
        if path.name in {'object-index.json', 'validation.json'}:
            continue
        document = _read_optional_json(path, code='maintenance_object_invalid')
        if document is None:
            continue
        document = dict(document)
        document['_artifact_path'] = _relative(root, path)
        objects.append(document)
    return objects


def _copy_record(record: dict) -> dict:
    return copy.deepcopy(record)


def _index_path(targets: dict, path: str | None, record: dict):
    if path:
        targets['by_path'][_normalize_subject(path)] = record


def _add_source_ref_indexes(targets: dict, record: dict):
    for ref in record.get('source_refs') or []:
        if isinstance(ref, dict) and ref.get('source_id'):
            targets['by_source_id'].setdefault(ref['source_id'], []).append(record)


def _add_object_targets(targets: dict, objects: list[dict]):
    for document in objects:
        object_id = document.get('id')
        if not object_id:
            continue
        object_type = _object_type(document)
        object_path = document.get('_artifact_path')
        source_refs = list(document.get('source_refs') or [])
        if object_type == 'wiki_page':
            body_path = document.get('body_path')
            write_scope = [body_path] if body_path else ([object_path] if object_path else [])
            record = {
                'target_kind': 'wiki_page',
                'target_family': 'personal_wiki_page',
                'object_id': object_id,
                'object_type': object_type,
                'body_path': body_path,
                'object_path': object_path,
                'source_refs': source_refs,
                'review_status': document.get('review_status'),
                'write_scope': write_scope,
            }
            targets['by_object_id'][object_id] = record
            _index_path(targets, body_path, record)
            _index_path(targets, object_path, record)
            _add_source_ref_indexes(targets, record)
            continue

        record = {
            'target_kind': 'object',
            'target_family': 'object_artifact',
            'object_id': object_id,
            'object_type': object_type,
            'object_path': object_path,
            'source_refs': source_refs,
            'write_scope': [object_path] if object_path else [],
        }
        targets['by_object_id'][object_id] = record
        _index_path(targets, object_path, record)
        _add_source_ref_indexes(targets, record)


def _add_source_targets(root: Path, targets: dict, warnings: list[dict]):
    registry = _read_optional_json(
        registry_path(root),
        schema_version=SOURCE_REGISTRY_SCHEMA_VERSION,
        code='maintenance_source_registry_invalid',
    )
    if registry:
        for source_id, source in sorted((registry.get('sources') or {}).items()):
            record = {
                'target_kind': 'source',
                'target_family': 'source_registry',
                'source_id': source_id,
                'write_scope': [_relative(root, registry_path(root))],
                'evidence_path': _relative(root, registry_path(root)),
            }
            if isinstance(source, dict):
                record['source_type'] = source.get('type')
                record['locator'] = source.get('locator')
            targets['by_source_id'].setdefault(source_id, []).append(record)

    source_items = _read_optional_json(
        source_items_path(root),
        schema_version=SOURCE_ITEMS_SCHEMA_VERSION,
        code='maintenance_source_items_invalid',
    )
    if source_items is None:
        return
    items = source_items.get('items')
    if not isinstance(items, dict):
        raise MaintenanceTargetError(
            'source item index items field is invalid',
            code='maintenance_source_items_invalid',
            details={'path': str(source_items_path(root))},
        )
    for item in items.values():
        if not isinstance(item, dict) or not item.get('source_id'):
            continue
        source_id = item['source_id']
        record = {
            'target_kind': 'source_item',
            'target_family': 'source_item',
            'source_id': source_id,
            'item_id': item.get('item_id'),
            'source_item_path': item.get('relative_path') or item.get('locator'),
            'write_scope': [_relative(root, source_items_path(root))],
            'evidence_path': _relative(root, source_items_path(root)),
        }
        targets['by_source_id'].setdefault(source_id, []).append(record)
    if not items:
        warnings.append(_warning('source_items_empty', 'source item index has no items', _relative(root, source_items_path(root))))


def _add_view_targets(root: Path, targets: dict, warnings: list[dict]) -> dict | None:
    manifest_path = views_manifest_path(root)
    manifest = _read_optional_json(
        manifest_path,
        schema_version=VIEWS_MANIFEST_SCHEMA_VERSION,
        code='maintenance_view_manifest_invalid',
    )
    if manifest is None:
        warnings.append(_warning('views_missing', 'view manifest is missing', _relative(root, manifest_path)))
        return None
    files = manifest.get('files')
    if not isinstance(files, dict):
        raise MaintenanceTargetError(
            'view manifest files field is invalid',
            code='maintenance_view_manifest_invalid',
            details={'path': str(manifest_path)},
        )
    for view_path, metadata in sorted(files.items()):
        record = {
            'target_kind': 'view',
            'target_family': 'human_view',
            'view_path': view_path,
            'view_manifest_path': _relative(root, manifest_path),
            'write_scope': [view_path],
            'regeneration_command': 'wikify views',
        }
        if isinstance(metadata, dict):
            record['view_kind'] = metadata.get('kind')
            record['generated_at'] = metadata.get('generated_at')
        targets['view_files'][view_path] = record
        targets['by_path'][_normalize_subject(view_path)] = record
    return manifest


def _agent_artifact_paths(root: Path) -> list[Path]:
    return [
        root / 'llms.txt',
        root / 'llms-full.txt',
        page_index_path(root),
        citation_index_path(root),
        related_index_path(root),
        agent_graph_path(root),
        agent_report_path(root),
    ]


def _required_agent_export_paths(root: Path) -> list[Path]:
    return [
        root / 'llms.txt',
        root / 'llms-full.txt',
        page_index_path(root),
        citation_index_path(root),
        related_index_path(root),
        agent_graph_path(root),
    ]


def _add_agent_targets(root: Path, targets: dict):
    for path in _agent_artifact_paths(root):
        relative_path = _relative(root, path)
        if path.exists():
            record = {
                'target_kind': 'agent_artifact',
                'target_family': 'agent_export',
                'agent_artifact_path': relative_path,
                'write_scope': [relative_path],
                'regeneration_command': 'wikify agent export',
            }
            targets['agent_artifacts'][relative_path] = record
            targets['by_path'][_normalize_subject(relative_path)] = record
    targets['missing_agent_artifacts'] = [
        _relative(root, path)
        for path in _required_agent_export_paths(root)
        if not path.exists()
    ]


def load_maintenance_targets(base: Path | str) -> dict:
    root = _root(base)
    warnings: list[dict] = []
    objects = _load_object_documents(root)
    if not objects:
        warnings.append(_warning('objects_missing', 'no object documents were found', 'artifacts/objects/'))

    targets = {
        'schema_version': MAINTENANCE_TARGETS_SCHEMA_VERSION,
        'base': str(root),
        'generated_at': _utc_now(),
        'warnings': warnings,
        'by_object_id': {},
        'by_path': {},
        'by_source_id': {},
        'view_files': {},
        'agent_artifacts': {},
        'missing_agent_artifacts': [],
        'objects': objects,
        'object_validation': _read_optional_json(
            validation_report_path(root),
            schema_version=SCHEMA_VERSIONS['object_validation'],
            code='maintenance_validation_report_invalid',
        ),
        'wikiization_tasks': _read_optional_json(
            wikiization_task_queue_path(root),
            schema_version=WIKIIZATION_TASK_QUEUE_SCHEMA_VERSION,
            code='maintenance_wikiization_tasks_invalid',
        ),
        'view_tasks': _read_optional_json(
            view_task_queue_path(root),
            schema_version=VIEW_TASK_QUEUE_SCHEMA_VERSION,
            code='maintenance_view_tasks_invalid',
        ),
    }

    _add_object_targets(targets, objects)
    _add_source_targets(root, targets, warnings)
    _add_view_targets(root, targets, warnings)
    _add_agent_targets(root, targets)

    object_counts_by_type: dict[str, int] = {}
    for obj in objects:
        object_type = _object_type(obj)
        object_counts_by_type[object_type] = object_counts_by_type.get(object_type, 0) + 1
    targets['summary'] = {
        'object_count': len(objects),
        'object_counts_by_type': dict(sorted(object_counts_by_type.items())),
        'path_target_count': len(targets['by_path']),
        'source_target_count': sum(len(values) for values in targets['by_source_id'].values()),
        'view_file_count': len(targets['view_files']),
        'agent_artifact_count': len(targets['agent_artifacts']),
        'missing_agent_artifact_count': len(targets['missing_agent_artifacts']),
        'warning_count': len(warnings),
    }
    return targets


def _legacy_target(subject: str) -> dict:
    target_family = 'legacy_markdown' if subject.endswith('.md') else 'legacy_path'
    return {
        'target_kind': 'legacy_path',
        'target_family': target_family,
        'write_scope': [subject] if subject else [],
    }


def resolve_target(targets: dict, subject: str | None) -> dict:
    normalized = _normalize_subject(subject)
    if not normalized:
        return _legacy_target(normalized)
    by_object_id = targets.get('by_object_id') or {}
    if normalized in by_object_id:
        return _copy_record(by_object_id[normalized])
    by_path = targets.get('by_path') or {}
    if normalized in by_path:
        return _copy_record(by_path[normalized])
    by_source_id = targets.get('by_source_id') or {}
    if normalized in by_source_id and by_source_id[normalized]:
        return _copy_record(by_source_id[normalized][0])
    view_files = targets.get('view_files') or {}
    if normalized in view_files:
        return _copy_record(view_files[normalized])
    agent_artifacts = targets.get('agent_artifacts') or {}
    if normalized in agent_artifacts:
        return _copy_record(agent_artifacts[normalized])
    return _legacy_target(normalized)
