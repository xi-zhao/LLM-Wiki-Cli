from dataclasses import dataclass
from pathlib import Path


SCOPE_DIRS = {
    'topics': ('topics',),
    'timelines': ('timelines',),
    'briefs': ('articles', 'briefs'),
    'parsed': ('articles', 'parsed'),
    'sorted': ('sorted',),
    'sources': ('sources',),
}


@dataclass(frozen=True)
class WikiObject:
    type: str
    path: Path
    relative_path: str
    title: str
    text: str
    lines: list[tuple[int, str]]


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


def _read_object(base: Path, source_type: str, path: Path) -> WikiObject:
    text = path.read_text(encoding='utf-8')
    return WikiObject(
        type=source_type,
        path=path.resolve(),
        relative_path=path.resolve().relative_to(base.resolve()).as_posix(),
        title=_title_from_text(path, text),
        text=text,
        lines=list(enumerate(text.splitlines(), start=1)),
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
