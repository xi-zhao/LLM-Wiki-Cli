import hashlib
import html
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from wikify.ingest.artifacts import ingest_item_id
from wikify.ingest.documents import FetchedPayload, IngestRequest, NormalizedDocument
from wikify.ingest.errors import IngestError


_TRACKING_QUERY_KEYS = {
    'ascene',
    'clicktime',
    'devicetype',
    'enterid',
    'lang',
    'pass_ticket',
    'scene',
    'sessionid',
    'version',
    'wx_header',
}


class WeChatUrlAdapter:
    name = 'wechat_url'

    def can_handle(self, locator: str, source=None) -> bool:
        parsed = urlsplit((locator or '').strip())
        host = parsed.hostname or ''
        host = host.lower()
        return host == 'mp.weixin.qq.com' or host.endswith('.mp.weixin.qq.com')

    def canonicalize(self, locator: str) -> str:
        raw_locator = (locator or '').strip()
        parsed = urlsplit(raw_locator)
        if not parsed.scheme or not parsed.netloc:
            raise IngestError(
                'WeChat locator must include scheme and host',
                code='ingest_locator_invalid',
                details={'locator': locator},
            )

        query_items = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in _TRACKING_QUERY_KEYS
        ]
        query = urlencode(sorted(query_items), doseq=True)
        return urlunsplit((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            query,
            '',
        ))

    def fetch(self, request: IngestRequest) -> FetchedPayload:
        canonical_locator = self.canonicalize(request.locator)
        html_content = self._run_browser(request.locator, 'html')
        text_content = self._run_browser(request.locator, 'text')
        metadata = _extract_metadata(html_content, text_content)
        return FetchedPayload(
            adapter=self.name,
            original_locator=request.locator,
            canonical_locator=canonical_locator,
            html=html_content,
            text=text_content,
            metadata=metadata,
            warnings=[],
        )

    def _run_browser(self, locator: str, mode: str) -> str:
        opened = False
        try:
            open_result = subprocess.run(
                ['agent-browser', 'open', locator],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            opened = open_result.returncode == 0
            if open_result.returncode != 0:
                raise IngestError(
                    'Failed to open WeChat locator in browser',
                    code='ingest_fetch_failed',
                    retryable=True,
                    details={'locator': locator, 'mode': mode},
                )

            get_result = subprocess.run(
                ['agent-browser', 'get', mode, 'body'],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            if get_result.returncode != 0:
                raise IngestError(
                    'Failed to fetch WeChat browser content',
                    code='ingest_fetch_failed',
                    retryable=True,
                    details={'locator': locator, 'mode': mode},
                )
            return get_result.stdout
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestError(
                'Failed to run WeChat browser fetch',
                code='ingest_fetch_failed',
                retryable=True,
                details={'locator': locator, 'mode': mode},
            ) from exc
        finally:
            if opened:
                try:
                    subprocess.run(
                        ['agent-browser', 'close'],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass

    def normalize(self, payload: FetchedPayload, source_id: str | None = None) -> NormalizedDocument:
        lines = _clean_lines(payload.text or payload.html)
        title = _metadata_value(payload, 'title') or _first_content_line(lines)
        source_account = _metadata_value(payload, 'source_account') or _metadata_value(payload, 'account')
        create_time = _metadata_value(payload, 'create_time')
        excluded = {value for value in (title, source_account, create_time, '微信公众平台') if value}
        body_lines = [
            line
            for line in lines
            if line not in excluded and not line.startswith('https://mp.weixin.qq.com/')
        ]
        if not body_lines:
            raise IngestError(
                'WeChat extraction produced empty body',
                code='ingest_extraction_empty',
                details={'locator': payload.canonical_locator},
            )

        body_text = '\n'.join(body_lines)
        markdown = f'# {title}\n\n{body_text}\n'
        sha256 = hashlib.sha256(
            '\n'.join((payload.canonical_locator, title or '', body_text)).encode('utf-8')
        ).hexdigest()
        return NormalizedDocument(
            item_id=ingest_item_id(self.name, payload.canonical_locator),
            source_id=source_id,
            adapter=self.name,
            original_locator=payload.original_locator,
            canonical_locator=payload.canonical_locator,
            title=title,
            body_text=body_text,
            markdown=markdown,
            captured_at=_utc_now(),
            published_at=create_time,
            author=source_account,
            raw_paths={},
            assets=[],
            warnings=list(payload.warnings or []),
            fingerprint={
                'kind': 'fetched',
                'hash_algorithm': 'sha256',
                'sha256': sha256,
                'network_checked': True,
            },
            metadata={
                'source_account': source_account,
                'create_time': create_time,
                'original_url': payload.original_locator,
            },
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _metadata_value(payload: FetchedPayload, key: str) -> str | None:
    value = (payload.metadata or {}).get(key)
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _extract_metadata(html_content: str, text_content: str) -> dict:
    metadata = {
        'title': _script_var(html_content, 'msg_title'),
        'source_account': _script_var(html_content, 'nickname'),
        'create_time': _script_var(html_content, 'ct'),
    }
    lines = _clean_lines(text_content)
    if not metadata['title']:
        metadata['title'] = _first_content_line(lines)
    if not metadata['source_account'] and len(lines) > 1:
        metadata['source_account'] = lines[1]
    if not metadata['create_time'] and len(lines) > 2:
        metadata['create_time'] = lines[2]
    return {key: value for key, value in metadata.items() if value}


def _script_var(html_content: str, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*["\']([^"\']+)["\']', html_content or '')
    if not match:
        return None
    return html.unescape(match.group(1)).strip() or None


def _first_content_line(lines: list[str]) -> str:
    for line in lines:
        if line and line != '微信公众平台':
            return line
    return 'Untitled WeChat Article'


def _clean_lines(content: str) -> list[str]:
    text = content or ''
    if '<' in text and '>' in text:
        text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'</?(p|div|br|h[1-6]|li|section|article)\b[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r'\s+', ' ', raw_line).strip()
        if line:
            lines.append(line)
    return lines
