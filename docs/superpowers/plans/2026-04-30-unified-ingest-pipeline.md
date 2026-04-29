# Unified Ingest Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified ingest pipeline where `wikify ingest <locator>` is the human-facing entrypoint that turns a WeChat article into an organized wiki entry while preserving stable machine artifacts for agents.

**Architecture:** Add `wikify/ingest/` as a package with contracts, adapters, artifact helpers, and pipeline orchestration. The first production adapter is `wechat_url`, implemented with fixture-testable fetch/normalize boundaries and connected to the existing source item queue consumed by `wikify wikiize`. The CLI keeps lower-level commands for agents, but the default human path runs ingest, deterministic wikiization, validation, and view refresh.

**Tech Stack:** Python 3.10+, stdlib-first implementation, `argparse`, `unittest`, `agent-browser` CLI for live WeChat fetches, existing Wikify envelope/workspace/sync/wikiize/views/object modules.

---

## File Structure

- Create `wikify/ingest/__init__.py`: package exports for the ingest pipeline.
- Create `wikify/ingest/errors.py`: typed `IngestError`.
- Create `wikify/ingest/documents.py`: dataclasses for requests, fetched payloads, normalized documents, and assets.
- Create `wikify/ingest/artifacts.py`: path helpers, stable ids, JSON/text writes, source item queue upserts.
- Create `wikify/ingest/adapters.py`: adapter protocol and adapter registry.
- Create `wikify/ingest/wechat.py`: WeChat URL adapter with injectable fetcher and deterministic normalization helpers.
- Create `wikify/ingest/pipeline.py`: orchestration for dry-run and write modes.
- Create `tests/test_ingest_pipeline.py`: package-level ingest pipeline tests.
- Create `tests/fixtures/wechat_article.html`: minimal WeChat HTML fixture.
- Create `tests/fixtures/wechat_article.txt`: matching extracted text fixture.
- Modify `wikify/cli.py`: override legacy `ingest` command in `wikify` CLI with the unified pipeline.
- Modify `tests/test_wikify_cli.py`: CLI parser and command behavior tests.
- Modify `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md`: document human-facing ingest and machine-facing lower-level commands.

---

### Task 1: Ingest Contracts And Artifact Helpers

**Files:**
- Create: `wikify/ingest/__init__.py`
- Create: `wikify/ingest/errors.py`
- Create: `wikify/ingest/documents.py`
- Create: `wikify/ingest/artifacts.py`
- Test: `tests/test_ingest_pipeline.py`

- [ ] **Step 1: Write failing tests for ingest ids, paths, and source item conversion**

Add this test file:

```python
import json
import tempfile
import unittest
from pathlib import Path


class IngestPipelineContractTests(unittest.TestCase):
    def test_artifact_paths_and_stable_ids_are_deterministic(self):
        from wikify.ingest.artifacts import (
            ingest_item_id,
            ingest_queue_id,
            ingest_run_path,
            raw_item_dir,
        )

        root = Path('/tmp/wikify-contract')
        item_id = ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example')

        self.assertEqual(item_id, ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example'))
        self.assertTrue(item_id.startswith('item_'))
        self.assertTrue(ingest_queue_id(item_id).startswith('queue_'))
        self.assertEqual(
            ingest_run_path(root, 'run_abc').as_posix(),
            '/tmp/wikify-contract/.wikify/ingest/runs/run_abc.json',
        )
        self.assertEqual(
            raw_item_dir(root, 'wechat_url', item_id).as_posix(),
            f'/tmp/wikify-contract/sources/raw/wechat_url/{item_id}',
        )

    def test_normalized_document_becomes_queueable_source_item(self):
        from wikify.ingest.artifacts import source_item_from_normalized
        from wikify.ingest.documents import NormalizedDocument

        document = NormalizedDocument(
            item_id='item_abc',
            source_id='src_abc',
            adapter='wechat_url',
            original_locator='https://mp.weixin.qq.com/s/example',
            canonical_locator='https://mp.weixin.qq.com/s/example',
            title='Example Article',
            body_text='Example body',
            markdown='Example body',
            captured_at='2026-04-30T00:00:00Z',
            published_at='2026-04-29T12:00:00Z',
            author='Example Account',
            raw_paths={
                'document': 'sources/raw/wechat_url/item_abc/document.md',
                'document_path': '/tmp/wikify-contract/sources/raw/wechat_url/item_abc/document.md',
                'text': 'sources/raw/wechat_url/item_abc/text.txt',
            },
            assets=[],
            warnings=[],
            fingerprint={'kind': 'fetched', 'sha256': 'abc'},
            metadata={'source_account': 'Example Account'},
        )

        item = source_item_from_normalized(document, status='new')

        self.assertEqual(item['schema_version'], 'wikify.source-items.v1')
        self.assertEqual(item['item_id'], 'item_abc')
        self.assertEqual(item['source_id'], 'src_abc')
        self.assertEqual(item['source_type'], 'url')
        self.assertEqual(item['item_type'], 'file')
        self.assertEqual(item['status'], 'new')
        self.assertEqual(item['relative_path'], 'sources/raw/wechat_url/item_abc/document.md')
        self.assertEqual(item['path'], '/tmp/wikify-contract/sources/raw/wechat_url/item_abc/document.md')
        self.assertEqual(item['fingerprint']['kind'], 'fetched')
        self.assertEqual(item['metadata']['adapter'], 'wechat_url')
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline -v
```

Expected: fail with `ModuleNotFoundError: No module named 'wikify.ingest'`.

- [ ] **Step 3: Create ingest package exports and typed error**

Create `wikify/ingest/__init__.py`:

```python
__all__ = []
```

Create `wikify/ingest/errors.py`:

```python
class IngestError(ValueError):
    def __init__(self, message: str, code: str = 'ingest_failed', details: dict | None = None, retryable: bool = False):
        self.code = code
        self.details = details or {}
        self.retryable = retryable
        super().__init__(message)
```

- [ ] **Step 4: Create normalized document contracts**

Create `wikify/ingest/documents.py`:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class IngestRequest:
    root: str
    locator: str
    source_id: str | None = None
    adapter_name: str | None = None
    dry_run: bool = False
    write_raw: bool = True
    refresh_views: bool = True


@dataclass(frozen=True)
class IngestAsset:
    kind: str
    locator: str
    path: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class FetchedPayload:
    adapter: str
    original_locator: str
    canonical_locator: str
    html: str = ''
    text: str = ''
    metadata: dict = field(default_factory=dict)
    assets: list[IngestAsset] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class NormalizedDocument:
    item_id: str
    source_id: str | None
    adapter: str
    original_locator: str
    canonical_locator: str
    title: str
    body_text: str
    markdown: str
    captured_at: str
    published_at: str | None
    author: str | None
    raw_paths: dict
    assets: list[dict]
    warnings: list[dict]
    fingerprint: dict
    metadata: dict
```

- [ ] **Step 5: Create artifact helpers**

Create `wikify/ingest/artifacts.py`:

```python
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from wikify.ingest.documents import NormalizedDocument
from wikify.objects import object_document_path, source_item_record_to_object
from wikify.sync import INGEST_QUEUE_SCHEMA_VERSION, SOURCE_ITEMS_SCHEMA_VERSION, ingest_queue_path, source_items_path


INGEST_RUN_SCHEMA_VERSION = 'wikify.ingest-run.v1'
INGEST_ITEM_SCHEMA_VERSION = 'wikify.ingest-item.v1'


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def stable_digest(*parts: object) -> str:
    payload = '\0'.join(str(part) for part in parts)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def ingest_item_id(adapter: str, canonical_locator: str) -> str:
    return f'item_{stable_digest(adapter, canonical_locator)[:24]}'


def ingest_queue_id(item_id: str) -> str:
    return f'queue_{stable_digest("wikiize_source_item", item_id)[:24]}'


def ingest_run_id(adapter: str, canonical_locator: str, now: str) -> str:
    return f'run_{stable_digest(adapter, canonical_locator, now)[:24]}'


def workspace_root(base: Path | str) -> Path:
    return Path(base).expanduser().resolve()


def ingest_run_path(base: Path | str, run_id: str) -> Path:
    return workspace_root(base) / '.wikify' / 'ingest' / 'runs' / f'{run_id}.json'


def ingest_item_path(base: Path | str, item_id: str) -> Path:
    return workspace_root(base) / '.wikify' / 'ingest' / 'items' / f'{item_id}.json'


def raw_item_dir(base: Path | str, adapter: str, item_id: str) -> Path:
    return workspace_root(base) / 'sources' / 'raw' / adapter / item_id


def relative_to_root(base: Path | str, path: Path) -> str:
    return path.relative_to(workspace_root(base)).as_posix()


def write_json_atomic(path: Path, document: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temp_path.replace(path)


def write_text_atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    temp_path.write_text(text, encoding='utf-8')
    temp_path.replace(path)


def source_item_from_normalized(document: NormalizedDocument, status: str) -> dict:
    relative_document_path = document.raw_paths.get('document')
    absolute_document_path = document.raw_paths.get('document_path') or relative_document_path
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'item_id': document.item_id,
        'source_id': document.source_id or f'ingest:{document.adapter}',
        'source_type': 'url' if document.canonical_locator.startswith(('http://', 'https://')) else 'file',
        'item_type': 'file',
        'status': status,
        'locator': document.original_locator,
        'locator_key': document.canonical_locator,
        'relative_path': relative_document_path,
        'path': absolute_document_path,
        'fingerprint': dict(document.fingerprint),
        'errors': [],
        'discovered_at': document.captured_at,
        'metadata': {
            'adapter': document.adapter,
            'title': document.title,
            'author': document.author,
            'published_at': document.published_at,
            **document.metadata,
        },
    }


def queue_entry_for_source_item(item: dict, now: str) -> dict:
    return {
        'queue_id': ingest_queue_id(item['item_id']),
        'action': 'wikiize_source_item',
        'source_id': item['source_id'],
        'source_type': item.get('source_type'),
        'item_id': item['item_id'],
        'item_status': item['status'],
        'status': 'queued',
        'requires_user': False,
        'evidence': {
            'source_item_id': item['item_id'],
            'source_id': item['source_id'],
            'locator': item.get('locator'),
            'relative_path': item.get('relative_path'),
            'fingerprint': item.get('fingerprint'),
        },
        'acceptance_checks': [
            'generated wiki content cites this source item id',
            'generated wiki content remains source-backed',
            'no user confirmation is required for deterministic wikiization',
        ],
        'created_at': now,
        'updated_at': now,
    }
```

- [ ] **Step 6: Run tests to verify contracts pass**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline.IngestPipelineContractTests -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Commit**

```bash
git add wikify/ingest tests/test_ingest_pipeline.py
git commit -m "feat(ingest): add unified ingest contracts"
```

---

### Task 2: Adapter Registry And WeChat Normalization

**Files:**
- Create: `wikify/ingest/adapters.py`
- Create: `wikify/ingest/wechat.py`
- Create: `tests/fixtures/wechat_article.html`
- Create: `tests/fixtures/wechat_article.txt`
- Modify: `tests/test_ingest_pipeline.py`

- [ ] **Step 1: Add fixture files**

Create `tests/fixtures/wechat_article.html`:

```html
<html>
  <head><title>微信公众平台</title></head>
  <body>
    <script>
      var msg_title = "统一 Ingest 设计";
      var nickname = "Wikify 产品笔记";
      var ct = "2026-04-29 12:00";
    </script>
    <div id="js_content">
      <p>这篇文章解释为什么 ingest 应该成为 Wikify 的人类入口。</p>
      <p>人类只应该看到整理好的 wiki，agent 才需要看 pipeline artifact。</p>
      <img src="https://mmbiz.qpic.cn/test-image?wx_fmt=png" />
    </div>
  </body>
</html>
```

Create `tests/fixtures/wechat_article.txt`:

```text
统一 Ingest 设计
Wikify 产品笔记
2026-04-29 12:00
这篇文章解释为什么 ingest 应该成为 Wikify 的人类入口。
人类只应该看到整理好的 wiki，agent 才需要看 pipeline artifact。
```

- [ ] **Step 2: Write failing tests for registry and normalization**

Append to `tests/test_ingest_pipeline.py`:

```python
class IngestAdapterTests(unittest.TestCase):
    def test_adapter_registry_resolves_wechat_url(self):
        from wikify.ingest.adapters import resolve_adapter

        adapter = resolve_adapter('https://mp.weixin.qq.com/s/example')

        self.assertEqual(adapter.name, 'wechat_url')

    def test_wechat_canonical_url_keeps_article_query_identity(self):
        from wikify.ingest.wechat import WeChatUrlAdapter

        adapter = WeChatUrlAdapter()

        first = adapter.canonicalize('https://mp.weixin.qq.com/s?sn=abc&mid=2&idx=1&scene=7#wechat_redirect')
        second = adapter.canonicalize('https://mp.weixin.qq.com/s?idx=1&mid=2&sn=abc&scene=8')
        other = adapter.canonicalize('https://mp.weixin.qq.com/s?sn=other&mid=2&idx=1')

        self.assertEqual(first, 'https://mp.weixin.qq.com/s?idx=1&mid=2&sn=abc')
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_wechat_adapter_normalizes_fixture_without_chrome(self):
        from wikify.ingest.documents import FetchedPayload
        from wikify.ingest.wechat import WeChatUrlAdapter

        fixture_dir = Path(__file__).parent / 'fixtures'
        payload = FetchedPayload(
            adapter='wechat_url',
            original_locator='https://mp.weixin.qq.com/s/example',
            canonical_locator='https://mp.weixin.qq.com/s/example',
            html=(fixture_dir / 'wechat_article.html').read_text(encoding='utf-8'),
            text=(fixture_dir / 'wechat_article.txt').read_text(encoding='utf-8'),
            metadata={
                'title': '统一 Ingest 设计',
                'source_account': 'Wikify 产品笔记',
                'create_time': '2026-04-29 12:00',
            },
        )

        document = WeChatUrlAdapter().normalize(payload, source_id='src_wechat')

        self.assertEqual(document.adapter, 'wechat_url')
        self.assertEqual(document.source_id, 'src_wechat')
        self.assertEqual(document.title, '统一 Ingest 设计')
        self.assertEqual(document.author, 'Wikify 产品笔记')
        self.assertIn('ingest 应该成为 Wikify 的人类入口', document.markdown)
        self.assertNotIn('微信公众平台', document.markdown)
        self.assertTrue(document.fingerprint['sha256'])
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline.IngestAdapterTests -v
```

Expected: fail because `wikify.ingest.adapters` and `wikify.ingest.wechat` do not exist.

- [ ] **Step 4: Implement adapter registry**

Create `wikify/ingest/adapters.py`:

```python
from typing import Protocol
from urllib.parse import urlparse

from wikify.ingest.documents import FetchedPayload, IngestRequest, NormalizedDocument
from wikify.ingest.errors import IngestError


class IngestAdapter(Protocol):
    name: str

    def can_handle(self, locator: str, source: dict | None = None) -> bool:
        raise NotImplementedError

    def canonicalize(self, locator: str) -> str:
        raise NotImplementedError

    def fetch(self, request: IngestRequest) -> FetchedPayload:
        raise NotImplementedError

    def normalize(self, payload: FetchedPayload, source_id: str | None = None) -> NormalizedDocument:
        raise NotImplementedError


def resolve_adapter(locator: str, source: dict | None = None, adapter_name: str | None = None) -> IngestAdapter:
    from wikify.ingest.wechat import WeChatUrlAdapter

    adapters: list[IngestAdapter] = [
        WeChatUrlAdapter(),
    ]
    if adapter_name:
        for adapter in adapters:
            if adapter.name == adapter_name:
                return adapter
        raise IngestError(
            f'ingest adapter is not registered: {adapter_name}',
            code='ingest_adapter_not_found',
            details={'adapter': adapter_name},
        )
    for adapter in adapters:
        if adapter.can_handle(locator, source):
            return adapter
    parsed = urlparse(locator)
    raise IngestError(
        'no ingest adapter can handle locator',
        code='ingest_adapter_not_found',
        details={'locator': locator, 'scheme': parsed.scheme, 'host': parsed.netloc},
    )
```

- [ ] **Step 5: Implement WeChat normalization with injectable fetcher**

Create `wikify/ingest/wechat.py`:

```python
import hashlib
import html
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from wikify.ingest.artifacts import ingest_item_id
from wikify.ingest.documents import FetchedPayload, IngestRequest, NormalizedDocument
from wikify.ingest.errors import IngestError


TITLE_RE = re.compile(r'var\s+msg_title\s*=\s*"([^"]+)"|title["\']?\s*[:=]\s*["\']([^"\']+)')
ACCOUNT_RE = re.compile(r'var\s+nickname\s*=\s*"([^"]+)"|source_account["\']?\s*[:=]\s*["\']([^"\']+)')
TIME_RE = re.compile(r'var\s+ct\s*=\s*"([^"]+)"|create_time["\']?\s*[:=]\s*["\']([^"\']+)')
TAG_RE = re.compile(r'<[^>]+>')
SPACE_RE = re.compile(r'\s+')
TRACKING_QUERY_KEYS = {'ascene', 'clicktime', 'devicetype', 'enterid', 'lang', 'pass_ticket', 'scene', 'sessionid', 'version', 'wx_header'}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def first_match(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ''
    for group in match.groups():
        if group:
            return html.unescape(group).strip()
    return ''


def clean_lines(text: str, title: str, account: str, published_at: str) -> list[str]:
    cleaned = html.unescape(TAG_RE.sub('\n', text))
    lines = []
    for line in cleaned.splitlines():
        value = SPACE_RE.sub(' ', line).strip()
        if not value:
            continue
        if value in {'微信公众平台', title, account, published_at}:
            continue
        if value.startswith('https://mp.weixin.qq.com/'):
            continue
        lines.append(value)
    return lines


class WeChatUrlAdapter:
    name = 'wechat_url'

    def can_handle(self, locator: str, source: dict | None = None) -> bool:
        del source
        return 'mp.weixin.qq.com' in urlparse(locator).netloc.lower()

    def canonicalize(self, locator: str) -> str:
        parsed = urlparse(locator.strip())
        if not parsed.scheme or not parsed.netloc:
            raise IngestError('WeChat URL is invalid', code='ingest_locator_invalid', details={'locator': locator})
        query_pairs = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in TRACKING_QUERY_KEYS
        ]
        query = urlencode(sorted(query_pairs), doseq=True)
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, '', query, ''))

    def fetch(self, request: IngestRequest) -> FetchedPayload:
        html_text = self._run_browser(request.locator, 'html')
        body_text = self._run_browser(request.locator, 'text')
        metadata = {
            'title': first_match(TITLE_RE, html_text),
            'source_account': first_match(ACCOUNT_RE, html_text),
            'create_time': first_match(TIME_RE, html_text),
        }
        return FetchedPayload(
            adapter=self.name,
            original_locator=request.locator,
            canonical_locator=self.canonicalize(request.locator),
            html=html_text,
            text=body_text,
            metadata=metadata,
            warnings=[],
        )

    def _run_browser(self, locator: str, mode: str) -> str:
        opened = False
        try:
            self._run_agent_browser(['open', locator], locator, mode)
            opened = True
            return self._run_agent_browser(['get', mode, 'body'], locator, mode)
        finally:
            if opened:
                self._run_agent_browser(['close'], locator, mode, raise_on_error=False)

    def _run_agent_browser(self, args: list[str], locator: str, mode: str, raise_on_error: bool = True) -> str:
        proc = subprocess.run(['agent-browser', *args], capture_output=True, text=True, timeout=90)
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or 'browser fetch failed'
            if raise_on_error:
                raise IngestError(detail, code='ingest_fetch_failed', details={'locator': locator, 'mode': mode}, retryable=True)
        return proc.stdout

    def normalize(self, payload: FetchedPayload, source_id: str | None = None) -> NormalizedDocument:
        title = payload.metadata.get('title') or self._title_from_text(payload.text)
        account = payload.metadata.get('source_account') or ''
        published_at = payload.metadata.get('create_time') or None
        lines = clean_lines(payload.text or payload.html, title, account, published_at or '')
        if not lines:
            raise IngestError('WeChat article extraction returned no body text', code='ingest_extraction_empty', details={'locator': payload.original_locator})
        markdown = '\n'.join([f'# {title}', '', *lines]).strip() + '\n'
        item_id = ingest_item_id(self.name, payload.canonical_locator)
        return NormalizedDocument(
            item_id=item_id,
            source_id=source_id,
            adapter=self.name,
            original_locator=payload.original_locator,
            canonical_locator=payload.canonical_locator,
            title=title,
            body_text='\n'.join(lines),
            markdown=markdown,
            captured_at=utc_now(),
            published_at=published_at,
            author=account or None,
            raw_paths={},
            assets=[],
            warnings=list(payload.warnings),
            fingerprint={
                'kind': 'fetched',
                'hash_algorithm': 'sha256',
                'sha256': sha256_text(markdown),
                'network_checked': True,
            },
            metadata={
                'source_account': account,
                'create_time': published_at,
                'original_url': payload.original_locator,
            },
        )

    def _title_from_text(self, text: str) -> str:
        for line in text.splitlines():
            value = line.strip()
            if value and value != '微信公众平台':
                return value[:120]
        return 'WeChat Article'
```

- [ ] **Step 6: Run adapter tests**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline.IngestAdapterTests -v
```

Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```bash
git add wikify/ingest/adapters.py wikify/ingest/wechat.py tests/fixtures tests/test_ingest_pipeline.py
git commit -m "feat(ingest): add wechat adapter normalization"
```

---

### Task 3: Pipeline Writes Canonical Artifacts And Queue Entries

**Files:**
- Create: `wikify/ingest/pipeline.py`
- Modify: `wikify/ingest/artifacts.py`
- Modify: `tests/test_ingest_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

Append to `tests/test_ingest_pipeline.py`:

```python
class IngestPipelineWriteTests(unittest.TestCase):
    def test_run_ingest_dry_run_writes_nothing(self):
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)

            result = run_ingest(
                root,
                'https://mp.weixin.qq.com/s/example',
                adapter_name='wechat_url',
                dry_run=True,
                fetch_payload={
                    'html': (Path(__file__).parent / 'fixtures' / 'wechat_article.html').read_text(encoding='utf-8'),
                    'text': (Path(__file__).parent / 'fixtures' / 'wechat_article.txt').read_text(encoding='utf-8'),
                    'metadata': {'title': '统一 Ingest 设计', 'source_account': 'Wikify 产品笔记'},
                },
            )

            self.assertEqual(result['status'], 'planned')
            self.assertFalse((root / '.wikify' / 'ingest').exists())
            self.assertFalse((root / '.wikify' / 'queues' / 'ingest-items.json').exists())

    def test_run_ingest_writes_raw_item_source_object_and_queue(self):
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)

            result = run_ingest(
                root,
                'https://mp.weixin.qq.com/s/example',
                adapter_name='wechat_url',
                fetch_payload={
                    'html': (Path(__file__).parent / 'fixtures' / 'wechat_article.html').read_text(encoding='utf-8'),
                    'text': (Path(__file__).parent / 'fixtures' / 'wechat_article.txt').read_text(encoding='utf-8'),
                    'metadata': {'title': '统一 Ingest 设计', 'source_account': 'Wikify 产品笔记'},
                },
                refresh_views=False,
            )

            item_id = result['item']['item_id']
            self.assertEqual(result['status'], 'completed')
            self.assertTrue((root / result['item']['path']).exists())
            self.assertTrue((root / '.wikify' / 'ingest' / 'items' / f'{item_id}.json').exists())
            self.assertTrue((root / 'artifacts' / 'objects' / 'source_items' / f'{item_id}.json').exists())

            queue = json.loads((root / '.wikify' / 'queues' / 'ingest-items.json').read_text(encoding='utf-8'))
            self.assertEqual(queue['schema_version'], 'wikify.ingest-queue.v1')
            self.assertEqual(queue['summary']['queue_count'], 1)
            self.assertEqual(queue['entries'][0]['item_id'], item_id)

            source_items = json.loads((root / '.wikify' / 'sync' / 'source-items.json').read_text(encoding='utf-8'))
            self.assertIn(item_id, source_items['items'])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline.IngestPipelineWriteTests -v
```

Expected: fail because `wikify.ingest.pipeline` does not exist.

- [ ] **Step 3: Add source item index and queue write helpers**

Append to `wikify/ingest/artifacts.py`:

```python
def read_json_or_default(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def empty_source_items(workspace_id: str, now: str) -> dict:
    return {
        'schema_version': SOURCE_ITEMS_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'summary': {'item_count': 0, 'item_status_counts': {}},
        'items': {},
    }


def empty_ingest_queue(workspace_id: str, now: str) -> dict:
    return {
        'schema_version': INGEST_QUEUE_SCHEMA_VERSION,
        'workspace_id': workspace_id,
        'generated_at': now,
        'summary': {'queue_count': 0, 'by_item_status': {}},
        'entries': [],
    }


def upsert_source_item(base: Path | str, workspace_id: str, item: dict, now: str):
    path = source_items_path(base)
    document = read_json_or_default(path, empty_source_items(workspace_id, now))
    items = document.setdefault('items', {})
    items[item['item_id']] = item
    values = list(items.values())
    counts: dict[str, int] = {}
    for value in values:
        status = value.get('status') or 'unknown'
        counts[status] = counts.get(status, 0) + 1
    document['generated_at'] = now
    document['summary'] = {'item_count': len(values), 'item_status_counts': dict(sorted(counts.items()))}
    write_json_atomic(path, document)


def upsert_ingest_queue_entry(base: Path | str, workspace_id: str, item: dict, now: str):
    path = ingest_queue_path(base)
    document = read_json_or_default(path, empty_ingest_queue(workspace_id, now))
    entry = queue_entry_for_source_item(item, now)
    entries = [existing for existing in document.get('entries', []) if existing.get('item_id') != item['item_id']]
    entries.append(entry)
    entries.sort(key=lambda value: (value.get('source_id') or '', value.get('item_id') or ''))
    counts: dict[str, int] = {}
    for value in entries:
        status = value.get('item_status') or 'unknown'
        counts[status] = counts.get(status, 0) + 1
    document['entries'] = entries
    document['generated_at'] = now
    document['summary'] = {'queue_count': len(entries), 'by_item_status': dict(sorted(counts.items()))}
    write_json_atomic(path, document)
    return entry


def write_source_item_object(base: Path | str, item: dict):
    obj = source_item_record_to_object(item)
    path = object_document_path(base, 'source_item', item['item_id'])
    write_json_atomic(path, obj)
    return path
```

- [ ] **Step 4: Implement pipeline orchestration**

Create `wikify/ingest/pipeline.py`:

```python
from pathlib import Path

from wikify.ingest.adapters import resolve_adapter
from wikify.ingest.artifacts import (
    INGEST_ITEM_SCHEMA_VERSION,
    INGEST_RUN_SCHEMA_VERSION,
    ingest_item_id,
    ingest_item_path,
    ingest_run_id,
    ingest_run_path,
    raw_item_dir,
    relative_to_root,
    source_item_from_normalized,
    upsert_ingest_queue_entry,
    upsert_source_item,
    utc_now,
    write_json_atomic,
    write_source_item_object,
    write_text_atomic,
)
from wikify.ingest.documents import FetchedPayload, IngestRequest
from wikify.ingest.errors import IngestError
from wikify.workspace import load_workspace


def _payload_from_test_data(adapter_name: str, locator: str, canonical_locator: str, payload: dict) -> FetchedPayload:
    return FetchedPayload(
        adapter=adapter_name,
        original_locator=locator,
        canonical_locator=canonical_locator,
        html=payload.get('html', ''),
        text=payload.get('text', ''),
        metadata=dict(payload.get('metadata') or {}),
        warnings=list(payload.get('warnings') or []),
    )


def _write_raw_document(root: Path, document):
    directory = raw_item_dir(root, document.adapter, document.item_id)
    document_path = directory / 'document.md'
    text_path = directory / 'text.txt'
    metadata_path = directory / 'metadata.json'
    write_text_atomic(document_path, document.markdown)
    write_text_atomic(text_path, document.body_text)
    write_json_atomic(metadata_path, {
        'title': document.title,
        'adapter': document.adapter,
        'original_locator': document.original_locator,
        'canonical_locator': document.canonical_locator,
        'author': document.author,
        'published_at': document.published_at,
        'captured_at': document.captured_at,
        'metadata': document.metadata,
        'warnings': document.warnings,
    })
    return {
        'document': relative_to_root(root, document_path),
        'document_path': str(document_path),
        'text': relative_to_root(root, text_path),
        'text_path': str(text_path),
        'metadata': relative_to_root(root, metadata_path),
        'metadata_path': str(metadata_path),
    }


def run_ingest(
    base: Path | str,
    locator: str,
    *,
    source_id: str | None = None,
    adapter_name: str | None = None,
    dry_run: bool = False,
    write_raw: bool = True,
    refresh_views: bool = True,
    fetch_payload: dict | None = None,
) -> dict:
    root = Path(base).expanduser().resolve()
    workspace = load_workspace(root)
    adapter = resolve_adapter(locator, adapter_name=adapter_name)
    canonical_locator = adapter.canonicalize(locator)
    now = utc_now()
    if not write_raw:
        raise IngestError(
            'ingest raw document writing is required to keep wiki claims source-backed',
            code='ingest_raw_required',
            details={'locator': locator, 'adapter': adapter.name},
        )
    if dry_run:
        planned_item_id = ingest_item_id(adapter.name, canonical_locator)
        run_id = ingest_run_id(adapter.name, canonical_locator, now)
        run_document = {
            'schema_version': INGEST_RUN_SCHEMA_VERSION,
            'id': run_id,
            'status': 'planned',
            'adapter': adapter.name,
            'locator': locator,
            'canonical_locator': canonical_locator,
            'item_id': planned_item_id,
            'started_at': now,
            'completed_at': None,
            'warnings': [],
        }
        return {
            'schema_version': INGEST_RUN_SCHEMA_VERSION,
            'status': 'planned',
            'dry_run': True,
            'run': run_document,
            'planned': {
                'item_id': planned_item_id,
                'adapter': adapter.name,
                'locator': locator,
                'canonical_locator': canonical_locator,
            },
            'artifacts': {},
            'next_actions': ['run_without_dry_run'],
        }
    request = IngestRequest(
        root=str(root),
        locator=locator,
        source_id=source_id,
        adapter_name=adapter.name,
        dry_run=dry_run,
        write_raw=write_raw,
        refresh_views=refresh_views,
    )
    fetched = _payload_from_test_data(adapter.name, locator, canonical_locator, fetch_payload) if fetch_payload is not None else adapter.fetch(request)
    document = adapter.normalize(fetched, source_id=source_id)
    run_id = ingest_run_id(adapter.name, document.canonical_locator, now)
    run_document = {
        'schema_version': INGEST_RUN_SCHEMA_VERSION,
        'id': run_id,
        'status': 'planned' if dry_run else 'completed',
        'adapter': adapter.name,
        'locator': locator,
        'canonical_locator': document.canonical_locator,
        'item_id': document.item_id,
        'started_at': now,
        'completed_at': now,
        'warnings': document.warnings,
    }
    raw_paths = _write_raw_document(root, document)
    document = type(document)(
        item_id=document.item_id,
        source_id=document.source_id,
        adapter=document.adapter,
        original_locator=document.original_locator,
        canonical_locator=document.canonical_locator,
        title=document.title,
        body_text=document.body_text,
        markdown=document.markdown,
        captured_at=document.captured_at,
        published_at=document.published_at,
        author=document.author,
        raw_paths=raw_paths,
        assets=document.assets,
        warnings=document.warnings,
        fingerprint=document.fingerprint,
        metadata=document.metadata,
    )
    item = source_item_from_normalized(document, status='new')
    workspace_id = workspace['workspace']['workspace_id']
    upsert_source_item(root, workspace_id, item, now)
    queue_entry = upsert_ingest_queue_entry(root, workspace_id, item, now)
    source_item_object_path = write_source_item_object(root, item)
    item_record = {
        'schema_version': INGEST_ITEM_SCHEMA_VERSION,
        'id': document.item_id,
        'status': 'completed',
        'adapter': adapter.name,
        'source_item': item,
        'normalized': {
            'title': document.title,
            'author': document.author,
            'published_at': document.published_at,
            'raw_paths': raw_paths,
            'warnings': document.warnings,
        },
    }
    write_json_atomic(ingest_item_path(root, document.item_id), item_record)
    write_json_atomic(ingest_run_path(root, run_id), run_document)
    return {
        'schema_version': INGEST_RUN_SCHEMA_VERSION,
        'status': 'completed',
        'dry_run': False,
        'run': run_document,
        'item': item,
        'queue_entry': queue_entry,
        'artifacts': {
            'run': relative_to_root(root, ingest_run_path(root, run_id)),
            'item': relative_to_root(root, ingest_item_path(root, document.item_id)),
            'source_item_object': relative_to_root(root, source_item_object_path),
            'raw_document': raw_paths.get('document'),
        },
        'next_actions': ['wikify wikiize --item ' + document.item_id, 'wikify views'],
    }
```

- [ ] **Step 5: Export `run_ingest` from the package**

Replace `wikify/ingest/__init__.py` with:

```python
from wikify.ingest.pipeline import run_ingest

__all__ = ['run_ingest']
```

- [ ] **Step 6: Run pipeline tests**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline.IngestPipelineWriteTests -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Commit**

```bash
git add wikify/ingest/__init__.py wikify/ingest/artifacts.py wikify/ingest/pipeline.py tests/test_ingest_pipeline.py
git commit -m "feat(ingest): write pipeline artifacts and queue entries"
```

---

### Task 4: Human-Facing CLI Path

**Files:**
- Modify: `wikify/cli.py`
- Modify: `tests/test_wikify_cli.py`

- [ ] **Step 1: Write failing CLI parser and command tests**

Append to `tests/test_wikify_cli.py`:

```python
    def test_build_parser_accepts_unified_ingest_options(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'ingest',
            'https://mp.weixin.qq.com/s/example',
            '--adapter',
            'wechat_url',
            '--dry-run',
            '--no-refresh-views',
        ])

        self.assertEqual(args.command, 'ingest')
        self.assertEqual(args.locator, 'https://mp.weixin.qq.com/s/example')
        self.assertEqual(args.adapter, 'wechat_url')
        self.assertTrue(args.dry_run)
        self.assertTrue(args.no_refresh_views)
        self.assertEqual(args.func, cli.cmd_ingest)

    def test_ingest_command_dry_run_returns_unified_envelope(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                initialize_workspace(root)
                os.environ['WIKIFY_BASE'] = str(root)
                os.environ['FOKB_BASE'] = str(root)
                parser = cli.build_parser()
                args = parser.parse_args([
                    'ingest',
                    'https://mp.weixin.qq.com/s/example',
                    '--adapter',
                    'wechat_url',
                    '--dry-run',
                ])

                result = args.func(args)

                self.assertTrue(result['ok'])
                self.assertEqual(result['command'], 'ingest')
                self.assertEqual(result['result']['status'], 'planned')
                self.assertEqual(result['result']['completion']['user_message'], 'ingest dry run completed')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_wikify_cli.WikifyCliTests.test_build_parser_accepts_unified_ingest_options tests.test_wikify_cli.WikifyCliTests.test_ingest_command_dry_run_returns_unified_envelope -v
```

Expected: fail because the legacy parser uses `url` and does not expose unified options.

- [ ] **Step 3: Import ingest pipeline and add command handler**

Modify `wikify/cli.py` imports:

```python
from wikify.ingest.errors import IngestError
from wikify.ingest.pipeline import run_ingest
```

Add `cmd_ingest` near `cmd_sync`:

```python
def cmd_ingest(args):
    locator = getattr(args, 'locator', None) or getattr(args, 'url', None)
    try:
        result = run_ingest(
            discover_base(),
            locator,
            source_id=args.source,
            adapter_name=args.adapter,
            dry_run=args.dry_run,
            write_raw=True,
            refresh_views=not args.no_refresh_views,
        )
    except IngestError as exc:
        return envelope_error(
            'ingest',
            exc.code,
            str(exc),
            2,
            retryable=exc.retryable,
            details=exc.details,
        )
    except WorkspaceError as exc:
        return _workspace_error('ingest', exc)
    except Exception as exc:
        return envelope_error(
            'ingest',
            'ingest_failed',
            str(exc),
            1,
            retryable=False,
        )
    artifacts = [path for path in result.get('artifacts', {}).values() if path]
    summary = 'ingest dry run completed' if result.get('dry_run') else 'wiki updated from ingest'
    result['completion'] = {
        'status': result.get('status'),
        'summary': summary,
        'artifacts': artifacts,
        'next_actions': result.get('next_actions', []),
        'user_message': summary,
    }
    return envelope_ok('ingest', result)
```

- [ ] **Step 4: Override legacy ingest parser in `build_parser`**

In `build_parser`, after `init` configuration and before `source`, add:

```python
    if 'ingest' in sub.choices:
        p_ingest = sub.choices['ingest']
        for action in p_ingest._actions:
            if getattr(action, 'dest', None) == 'url':
                action.dest = 'locator'
                action.metavar = 'locator'
        existing_dests = {getattr(action, 'dest', None) for action in p_ingest._actions}
        if 'source' not in existing_dests:
            p_ingest.add_argument('--source')
        if 'adapter' not in existing_dests:
            p_ingest.add_argument('--adapter')
        if 'dry_run' not in existing_dests:
            p_ingest.add_argument('--dry-run', action='store_true')
        if 'no_refresh_views' not in existing_dests:
            p_ingest.add_argument('--no-refresh-views', action='store_true')
        p_ingest.set_defaults(func=cmd_ingest)
    else:
        p_ingest = sub.add_parser('ingest', help='Ingest source material and update the human-facing wiki')
        p_ingest.add_argument('locator')
        p_ingest.add_argument('--source')
        p_ingest.add_argument('--adapter')
        p_ingest.add_argument('--dry-run', action='store_true')
        p_ingest.add_argument('--no-refresh-views', action='store_true')
        p_ingest.set_defaults(func=cmd_ingest)
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
python3 -m unittest tests.test_wikify_cli.WikifyCliTests.test_build_parser_accepts_unified_ingest_options tests.test_wikify_cli.WikifyCliTests.test_ingest_command_dry_run_returns_unified_envelope -v
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add wikify/cli.py tests/test_wikify_cli.py
git commit -m "feat(ingest): expose unified ingest CLI"
```

---

### Task 5: Default Ingest Runs Wikiization And Views

**Files:**
- Modify: `wikify/ingest/pipeline.py`
- Modify: `tests/test_ingest_pipeline.py`

- [ ] **Step 1: Write failing test for full human path**

Append to `tests/test_ingest_pipeline.py`:

```python
class IngestHumanPathTests(unittest.TestCase):
    def test_default_ingest_wikiizes_and_refreshes_views(self):
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)

            result = run_ingest(
                root,
                'https://mp.weixin.qq.com/s/example',
                adapter_name='wechat_url',
                fetch_payload={
                    'html': (Path(__file__).parent / 'fixtures' / 'wechat_article.html').read_text(encoding='utf-8'),
                    'text': (Path(__file__).parent / 'fixtures' / 'wechat_article.txt').read_text(encoding='utf-8'),
                    'metadata': {'title': '统一 Ingest 设计', 'source_account': 'Wikify 产品笔记'},
                },
            )

            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['human_path']['wikiize']['status'], 'completed')
            self.assertIn('views', result['human_path'])
            self.assertTrue((root / 'views' / 'index.md').exists())
            self.assertTrue((root / 'artifacts' / 'objects' / 'wiki_pages').exists())
            self.assertTrue(result['human_entry']['body_path'].startswith('wiki/pages/'))
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline.IngestHumanPathTests -v
```

Expected: fail because `run_ingest` currently only queues the source item.

- [ ] **Step 3: Call deterministic wikiization and view generation from the default path**

Modify `wikify/ingest/pipeline.py` imports:

```python
from wikify.views import run_view_generation
from wikify.wikiize import run_wikiization
```

Before the final return in write mode, add:

```python
    human_path = {}
    human_entry = {}
    if refresh_views:
        wikiize_result = run_wikiization(root, item_id=document.item_id, limit=1)
        human_path['wikiize'] = {
            'status': wikiize_result.get('status'),
            'summary': wikiize_result.get('summary', {}),
            'artifacts': wikiize_result.get('artifacts', {}),
        }
        for processed in wikiize_result.get('items', []):
            paths = processed.get('paths') or {}
            object_ids = processed.get('object_ids') or []
            if paths.get('body_path'):
                human_entry = {
                    'title': document.title,
                    'body_path': paths.get('body_path'),
                    'object_id': object_ids[0] if object_ids else None,
                }
                break
        views_result = run_view_generation(root, dry_run=False, include_html=True, section='all')
        human_path['views'] = {
            'status': views_result.get('status'),
            'summary': views_result.get('summary', {}),
            'generated': views_result.get('generated', []),
        }
```

Add these fields to the final result:

```python
        'human_path': human_path,
        'human_entry': human_entry,
```

- [ ] **Step 4: Run human path test**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline.IngestHumanPathTests -v
```

Expected: 1 test passes.

- [ ] **Step 5: Run focused pipeline tests**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline -v
```

Expected: all ingest pipeline tests pass.

- [ ] **Step 6: Commit**

```bash
git add wikify/ingest/pipeline.py tests/test_ingest_pipeline.py
git commit -m "feat(ingest): run human wiki path by default"
```

---

### Task 6: Compatibility And Documentation

**Files:**
- Modify: `README.md`
- Modify: `LLM-Wiki-Cli-README.md`
- Modify: `scripts/fokb_protocol.md`
- Modify: `tests/test_wikify_cli.py`

- [ ] **Step 1: Add documentation grep test**

Append to `tests/test_wikify_cli.py`:

```python
    def test_docs_describe_human_ingest_and_machine_pipeline_boundary(self):
        root = Path(__file__).resolve().parents[1]
        combined = '\n'.join([
            (root / 'README.md').read_text(encoding='utf-8'),
            (root / 'LLM-Wiki-Cli-README.md').read_text(encoding='utf-8'),
            (root / 'scripts' / 'fokb_protocol.md').read_text(encoding='utf-8'),
        ])

        self.assertIn('wikify ingest <locator>', combined)
        self.assertIn('humans consume the final wiki', combined)
        self.assertIn('wikify sync still does not fetch URL sources', combined)
        self.assertIn('mp.weixin.qq.com', combined)
```

- [ ] **Step 2: Run doc test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_wikify_cli.WikifyCliTests.test_docs_describe_human_ingest_and_machine_pipeline_boundary -v
```

Expected: fail until docs are updated.

- [ ] **Step 3: Update README**

In `README.md`, update the quick example so the human path is first:

```markdown
## Human ingest path

Humans should normally add knowledge and read the final wiki:

```bash
wikify ingest <locator>
wikify views
```

For WeChat public account articles, pass the article URL:

```bash
wikify ingest https://mp.weixin.qq.com/s/example
```

The command is allowed to fetch because ingest is explicit. It writes machine artifacts for agents, then updates the organized wiki. Humans consume the final wiki; `source add`, `sync`, `wikiize`, validation reports, queues, and agent exports are lower-level machine surfaces.

`wikify sync` still does not fetch URL sources. It remains an agent/debug command for local change detection and queue maintenance.
```

- [ ] **Step 4: Update Chinese README**

In `LLM-Wiki-Cli-README.md`, add:

```markdown
## 人类入口：只看最终 wiki

人类用户不应该理解 source registry、sync、queue、wikiize 这些中间层。默认体验应该是：

```bash
wikify ingest <locator>
```

公众号文章示例：

```bash
wikify ingest https://mp.weixin.qq.com/s/example
```

`wikify ingest` 是显式联网入口，可以抓取和整理内容，然后刷新最终 wiki。人类消费的是整理好的 Markdown/static wiki；`wikify sync`、`wikify wikiize`、validation report、agent context 等是 agent、调试和维护接口。

`wikify sync still does not fetch URL sources`：URL source 在 sync 中仍然只做离线状态记录，不会隐藏抓取。
```

- [ ] **Step 5: Update protocol docs**

In `scripts/fokb_protocol.md`, add an ingest section:

```markdown
## Unified ingest pipeline

`wikify ingest <locator>` is the human-facing entrypoint. It may fetch network content because the user explicitly invoked ingest. Humans consume the final wiki, while agents inspect the machine artifacts.

For `mp.weixin.qq.com` URLs, the `wechat_url` adapter normalizes the article into canonical source item artifacts and queues deterministic wikiization.

`wikify sync still does not fetch URL sources`; sync remains a machine-facing offline change detection command.
```

- [ ] **Step 6: Run doc test**

Run:

```bash
python3 -m unittest tests.test_wikify_cli.WikifyCliTests.test_docs_describe_human_ingest_and_machine_pipeline_boundary -v
```

Expected: 1 test passes.

- [ ] **Step 7: Commit**

```bash
git add README.md LLM-Wiki-Cli-README.md scripts/fokb_protocol.md tests/test_wikify_cli.py
git commit -m "docs(ingest): document human wiki surface"
```

---

### Task 7: Final Verification

**Files:**
- No source edits unless verification exposes a defect.

- [ ] **Step 1: Run focused ingest and CLI tests**

Run:

```bash
python3 -m unittest tests.test_ingest_pipeline tests.test_wikify_cli -v
```

Expected: all tests pass.

- [ ] **Step 2: Run full unit suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Run compile check**

Run:

```bash
python3 -m compileall -q wikify
```

Expected: exit code 0.

- [ ] **Step 4: Run diff whitespace check**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 5: Commit any verification-only documentation updates**

If verification required changing docs or tests, commit those files:

```bash
git add README.md LLM-Wiki-Cli-README.md scripts/fokb_protocol.md tests/test_ingest_pipeline.py tests/test_wikify_cli.py
git commit -m "docs(ingest): record verification notes"
```

If no files changed, skip this commit.

---

## Spec Coverage Review

- Human product surface: covered by Task 4 default CLI path and Task 6 docs.
- No hidden network in sync: covered by Task 6 docs and existing sync tests; Task 7 full suite preserves behavior.
- Adapter architecture: covered by Task 2.
- Artifact contract: covered by Task 1 and Task 3.
- WeChat first adapter: covered by Task 2, Task 3, and Task 5.
- Error and dry-run behavior: covered by Task 1, Task 3, and Task 4.
- Compatibility: covered by Task 4 parser override, Task 6 docs, and Task 7 full verification.
