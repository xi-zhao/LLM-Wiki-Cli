import copy
import json
from pathlib import Path, PurePosixPath

from wikify.frontmatter import FrontMatterError, split_front_matter
from wikify.objects import object_document_path


PRESERVATION_SCHEMA_VERSION = 'wikify.generated-page-preservation.v1'


class GeneratedPagePreservationError(ValueError):
    def __init__(
        self,
        message: str,
        code: str = 'generated_page_preservation_failed',
        details: dict | None = None,
    ):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def _normalize_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeneratedPagePreservationError(
            'preservation path is empty',
            details={'path': value},
        )
    raw = value.strip().replace('\\', '/')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts:
        raise GeneratedPagePreservationError(
            'preservation path must be relative and stay inside the wiki',
            details={'path': value},
        )
    return str(path)


def _content_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if root not in (path, *path.parents):
        raise GeneratedPagePreservationError(
            'preservation path must stay inside the wiki',
            details={'path': relative_path},
        )
    return path


def _read_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise GeneratedPagePreservationError(
            'generated page object JSON is invalid',
            details={'path': str(path)},
        ) from exc
    return document if isinstance(document, dict) else None


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _object_path_for_markdown(root: Path, metadata: dict, body_path: str) -> tuple[str | None, dict | None]:
    object_id = metadata.get('id') if isinstance(metadata.get('id'), str) else None
    if object_id:
        path = object_document_path(root, 'wiki_page', object_id)
        return _relative(root, path), _read_json_if_exists(path)
    object_root = root / 'artifacts' / 'objects' / 'wiki_pages'
    if not object_root.exists():
        return None, None
    for path in sorted(object_root.glob('*.json')):
        document = _read_json_if_exists(path)
        if document and document.get('body_path') == body_path:
            return _relative(root, path), document
    return None, None


def _object_path_for_body_path(root: Path, body_path: str) -> tuple[str | None, dict | None]:
    object_root = root / 'artifacts' / 'objects' / 'wiki_pages'
    if not object_root.exists():
        return None, None
    for path in sorted(object_root.glob('*.json')):
        document = _read_json_if_exists(path)
        if document and document.get('body_path') == body_path:
            return _relative(root, path), document
    return None, None


def _preserved_metadata(metadata: dict | None) -> dict | None:
    if metadata is None:
        return None
    return {
        'source_refs': copy.deepcopy(metadata.get('source_refs')),
        'review_status': metadata.get('review_status'),
    }


def _record_from_markdown(root: Path, relative_path: str) -> dict | None:
    path = _content_path(root, relative_path)
    if not path.exists() or path.suffix != '.md':
        return None
    try:
        metadata, _body = split_front_matter(path.read_text(encoding='utf-8'))
    except FrontMatterError as exc:
        _object_path, object_document = _object_path_for_body_path(root, relative_path)
        if object_document:
            raise GeneratedPagePreservationError(
                'generated page front matter is invalid',
                details={'path': relative_path, 'frontmatter_code': exc.code, 'frontmatter_details': exc.details},
            ) from exc
        return None
    is_wiki_page = metadata.get('type') == 'wiki_page' or bool(metadata.get('body_path'))
    if not is_wiki_page:
        return None
    body_path = metadata.get('body_path') or relative_path
    object_path, object_document = _object_path_for_markdown(root, metadata, body_path)
    return {
        'path': relative_path,
        'body_path': body_path,
        'object_id': metadata.get('id') or (object_document or {}).get('id'),
        'object_path': object_path,
        'preserve_fields': ['source_refs', 'review_status'],
        'front_matter': _preserved_metadata(metadata),
        'object': _preserved_metadata(object_document),
    }


def _record_from_object(root: Path, relative_path: str) -> dict | None:
    path = _content_path(root, relative_path)
    if not path.exists() or path.suffix != '.json':
        return None
    document = _read_json_if_exists(path)
    if not document:
        return None
    object_type = document.get('object_type') or document.get('type')
    if object_type != 'wiki_page':
        return None
    body_path = document.get('body_path')
    if not body_path:
        return None
    front_matter = None
    markdown_path = _content_path(root, body_path)
    if markdown_path.exists():
        try:
            metadata, _body = split_front_matter(markdown_path.read_text(encoding='utf-8'))
        except FrontMatterError as exc:
            raise GeneratedPagePreservationError(
                'generated page front matter is invalid',
                details={'path': body_path, 'frontmatter_code': exc.code, 'frontmatter_details': exc.details},
            ) from exc
        front_matter = _preserved_metadata(metadata)
    return {
        'path': body_path,
        'body_path': body_path,
        'object_id': document.get('id'),
        'object_path': relative_path,
        'preserve_fields': ['source_refs', 'review_status'],
        'front_matter': front_matter,
        'object': _preserved_metadata(document),
    }


def build_preservation_context(base: Path | str, write_scope: list[str]) -> dict:
    root = _root(base)
    records = []
    by_key = {}
    for raw_path in write_scope or []:
        relative_path = _normalize_relative_path(raw_path)
        record = _record_from_markdown(root, relative_path) or _record_from_object(root, relative_path)
        if not record:
            continue
        key = record.get('object_id') or record.get('body_path') or relative_path
        by_key[key] = record
    records = [by_key[key] for key in sorted(by_key)]
    return {
        'schema_version': PRESERVATION_SCHEMA_VERSION,
        'required': bool(records),
        'pages': records,
    }


def _simulate_operations(root: Path, relative_path: str, bundle: dict) -> str:
    path = _content_path(root, relative_path)
    try:
        content = path.read_text(encoding='utf-8')
    except FileNotFoundError as exc:
        raise GeneratedPagePreservationError(
            'generated page preservation target is missing',
            details={'path': relative_path},
        ) from exc
    for index, operation in enumerate(bundle.get('operations') or []):
        if operation.get('operation') != 'replace_text':
            continue
        if _normalize_relative_path(operation.get('path')) != relative_path:
            continue
        find = operation.get('find')
        replace = operation.get('replace')
        if not isinstance(find, str) or not isinstance(replace, str):
            raise GeneratedPagePreservationError(
                'generated page preservation operation is invalid',
                details={'path': relative_path, 'index': index},
            )
        occurrences = content.count(find)
        if occurrences != 1:
            raise GeneratedPagePreservationError(
                'generated page preservation could not simulate patch operation',
                details={'path': relative_path, 'index': index, 'occurrences': occurrences},
            )
        content = content.replace(find, replace, 1)
    return content


def _assert_equal(page: dict, carrier: str, field: str, expected, actual):
    if actual != expected:
        raise GeneratedPagePreservationError(
            f'generated page {carrier} {field} changed',
            details={
                'path': page.get('body_path') or page.get('path'),
                'object_id': page.get('object_id'),
                'carrier': carrier,
                'field': field,
                'expected': expected,
                'actual': actual,
            },
        )


def _validate_markdown_page(root: Path, page: dict, bundle: dict):
    front_matter = page.get('front_matter')
    body_path = page.get('body_path') or page.get('path')
    if not front_matter or not body_path:
        return
    after = _simulate_operations(root, body_path, bundle)
    try:
        metadata, _body = split_front_matter(after)
    except FrontMatterError as exc:
        raise GeneratedPagePreservationError(
            'generated page front matter becomes invalid after patch',
            details={'path': body_path, 'frontmatter_code': exc.code, 'frontmatter_details': exc.details},
        ) from exc
    for field in ('source_refs', 'review_status'):
        _assert_equal(page, 'front_matter', field, front_matter.get(field), metadata.get(field))


def _validate_object_page(root: Path, page: dict, bundle: dict):
    object_metadata = page.get('object')
    object_path = page.get('object_path')
    if not object_metadata or not object_path:
        return
    after = _simulate_operations(root, object_path, bundle)
    try:
        document = json.loads(after)
    except json.JSONDecodeError as exc:
        raise GeneratedPagePreservationError(
            'generated page object JSON becomes invalid after patch',
            details={'path': object_path},
        ) from exc
    for field in ('source_refs', 'review_status'):
        _assert_equal(page, 'object', field, object_metadata.get(field), document.get(field))


def validate_patch_bundle_preservation(base: Path | str, proposal: dict, bundle: dict) -> dict:
    root = _root(base)
    preservation = proposal.get('preservation')
    if not preservation:
        preservation = build_preservation_context(root, proposal.get('write_scope') or [])
    if not preservation.get('required'):
        return {
            'schema_version': PRESERVATION_SCHEMA_VERSION,
            'ok': True,
            'checked_page_count': 0,
        }
    for page in preservation.get('pages') or []:
        _validate_markdown_page(root, page, bundle)
        _validate_object_page(root, page, bundle)
    return {
        'schema_version': PRESERVATION_SCHEMA_VERSION,
        'ok': True,
        'checked_page_count': len(preservation.get('pages') or []),
    }
