from dataclasses import dataclass
from pathlib import Path

from wikify.frontmatter import FrontMatterError, split_front_matter
from wikify.objects import is_known_object_type, legacy_scope_to_object_type


SCOPE_DIRS = {
    'topics': ('topics',),
    'timelines': ('timelines',),
    'briefs': ('articles', 'briefs'),
    'parsed': ('articles', 'parsed'),
    'sorted': ('sorted',),
    'sources': ('sources',),
    'wiki_pages': ('wiki', 'pages'),
}


@dataclass(frozen=True)
class WikiObject:
    type: str
    path: Path
    relative_path: str
    title: str
    text: str
    lines: list[tuple[int, str]]
    metadata: dict
    object_id: str | None
    canonical_type: str


def _scope_paths(base: Path, scope: str) -> list[tuple[str, Path]]:
    if scope == 'all':
        return [(name, base.joinpath(*parts)) for name, parts in SCOPE_DIRS.items()]
    if scope not in SCOPE_DIRS:
        raise ValueError(f'unsupported markdown scope: {scope}')
    return [(scope, base.joinpath(*SCOPE_DIRS[scope]))]


def _title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped[2:].strip() or path.stem
    return path.stem


def _title_from_metadata_or_text(path: Path, metadata: dict, body: str) -> str:
    title = metadata.get('title')
    if isinstance(title, str) and title.strip():
        return title.strip()
    return _title_from_text(path, body)


def _canonical_type(source_type: str, metadata: dict) -> str:
    metadata_type = metadata.get('type')
    if is_known_object_type(metadata_type):
        return metadata_type
    return legacy_scope_to_object_type(source_type)


def _read_object(base: Path, source_type: str, path: Path) -> WikiObject:
    text = path.read_text(encoding='utf-8')
    try:
        metadata, body = split_front_matter(text)
    except FrontMatterError as exc:
        metadata = {
            '_frontmatter_error': {
                'code': exc.code,
                'message': str(exc),
                'details': exc.details,
            },
        }
        body = text
    return WikiObject(
        type=source_type,
        path=path.resolve(),
        relative_path=path.resolve().relative_to(base.resolve()).as_posix(),
        title=_title_from_metadata_or_text(path, metadata, body),
        text=text,
        lines=list(enumerate(text.splitlines(), start=1)),
        metadata=metadata,
        object_id=metadata.get('id') if isinstance(metadata.get('id'), str) and metadata.get('id') else None,
        canonical_type=_canonical_type(source_type, metadata),
    )


def scan_objects(base: Path | str, scope: str = 'all') -> list[WikiObject]:
    root = Path(base).expanduser().resolve()
    objects = []
    for source_type, directory in _scope_paths(root, scope):
        if not directory.exists():
            continue
        for path in sorted(directory.rglob('*.md')):
            if path.name.startswith('_'):
                continue
            objects.append(_read_object(root, source_type, path))
    return objects
