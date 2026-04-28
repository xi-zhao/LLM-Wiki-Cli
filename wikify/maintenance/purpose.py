from pathlib import Path


SCHEMA_VERSION = 'wikify.purpose-context.v1'
PURPOSE_CANDIDATES = ('purpose.md', 'wikify-purpose.md')


def _first_heading(lines: list[str], fallback: str) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            return stripped.lstrip('#').strip() or fallback
    return fallback


def _meaningful_lines(lines: list[str]) -> list[str]:
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        result.append(stripped)
    return result


def _matching_lines(lines: list[str], needles: tuple[str, ...]) -> list[str]:
    result = []
    for line in _meaningful_lines(lines):
        lowered = line.lower()
        if any(needle in lowered for needle in needles):
            result.append(line)
    return result


def _excerpt(lines: list[str], limit: int = 320) -> str:
    text = ' '.join(_meaningful_lines(lines))
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '...'


def load_purpose_context(base: Path | str) -> dict:
    root = Path(base).expanduser().resolve()
    for candidate in PURPOSE_CANDIDATES:
        path = root / candidate
        if not path.exists():
            continue
        lines = path.read_text(encoding='utf-8').splitlines()
        return {
            'schema_version': SCHEMA_VERSION,
            'present': True,
            'path': str(path),
            'relative_path': candidate,
            'title': _first_heading(lines, candidate),
            'excerpt': _excerpt(lines),
            'goal_lines': _matching_lines(lines, ('goal', 'goals', '目标', '目的')),
            'question_lines': _matching_lines(lines, ('question', 'questions', '问题')),
        }

    return {
        'schema_version': SCHEMA_VERSION,
        'present': False,
        'path': None,
        'relative_path': None,
        'title': None,
        'excerpt': '',
        'goal_lines': [],
        'question_lines': [],
        'candidates': list(PURPOSE_CANDIDATES),
    }
