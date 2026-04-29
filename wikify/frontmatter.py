import json
import re


class FrontMatterError(ValueError):
    def __init__(self, message: str, code: str = 'object_frontmatter_invalid', details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


def split_front_matter(text: str) -> tuple[dict, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        return {}, text

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            closing_index = index
            break
    if closing_index is None:
        raise FrontMatterError('front matter closing delimiter is missing')

    front_matter_text = ''.join(lines[1:closing_index])
    body = ''.join(lines[closing_index + 1:])
    return parse_front_matter(front_matter_text), body


def parse_front_matter(front_matter_text: str) -> dict:
    metadata = {}
    for line_number, raw_line in enumerate(front_matter_text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        if raw_line[:1].isspace() or raw_line.lstrip().startswith('- '):
            raise FrontMatterError(
                'front matter supports only single-line key-value entries',
                details={'line': line_number},
            )
        if ':' not in raw_line:
            raise FrontMatterError(
                'front matter line must contain a key-value separator',
                details={'line': line_number},
            )
        key, raw_value = raw_line.split(':', 1)
        key = key.strip()
        if not key or not re.match(r'^[A-Za-z_][A-Za-z0-9_-]*$', key):
            raise FrontMatterError('front matter key is invalid', details={'line': line_number, 'key': key})
        metadata[key] = _parse_value(raw_value.strip(), line_number)
    return metadata


def _parse_value(value: str, line_number: int):
    if value == '':
        return ''
    lowered = value.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    if value.startswith('[') or value.startswith('{'):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise FrontMatterError(
                'front matter JSON-flow value is invalid',
                details={'line': line_number},
            ) from exc
    if re.match(r'^-?\d+$', value):
        return int(value)
    if re.match(r'^-?(?:\d+\.\d*|\d*\.\d+)$', value):
        return float(value)
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def serialize_front_matter(metadata: dict) -> str:
    lines = []
    for key in sorted(metadata):
        value = metadata[key]
        lines.append(f'{key}: {_serialize_value(value)}')
    return '\n'.join(lines) + ('\n' if lines else '')


def _serialize_value(value) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value)
    if '\n' in text:
        raise FrontMatterError('front matter value must be single-line')
    return text


def render_markdown_with_front_matter(metadata: dict, body: str) -> str:
    if body and not body.endswith('\n'):
        body += '\n'
    return f'---\n{serialize_front_matter(metadata)}---\n{body}'
