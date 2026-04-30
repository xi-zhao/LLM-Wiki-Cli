import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class IngestPipelineContractTests(unittest.TestCase):
    def test_artifact_paths_and_stable_ids_are_deterministic(self):
        from wikify.ingest.artifacts import (
            ingest_item_id,
            ingest_queue_id,
            ingest_run_path,
            raw_item_dir,
            workspace_root,
        )

        root = Path(tempfile.mkdtemp()) / 'parent' / '..' / 'wikify-contract'
        resolved_root = root.resolve()
        item_id = ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example')

        self.assertEqual(item_id, ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example'))
        self.assertTrue(item_id.startswith('item_'))
        self.assertTrue(ingest_queue_id(item_id).startswith('queue_'))
        self.assertEqual(workspace_root(root), resolved_root)
        self.assertNotIn('..', workspace_root(root).parts)
        self.assertEqual(
            ingest_run_path(root, 'run_abc').as_posix(),
            (resolved_root / '.wikify' / 'ingest' / 'runs' / 'run_abc.json').as_posix(),
        )
        self.assertEqual(
            raw_item_dir(root, 'wechat_url', item_id).as_posix(),
            (resolved_root / 'sources' / 'raw' / 'wechat_url' / item_id).as_posix(),
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

    def test_normalized_local_document_uses_file_source_type(self):
        from wikify.ingest.artifacts import source_item_from_normalized
        from wikify.ingest.documents import NormalizedDocument

        document = NormalizedDocument(
            item_id='item_local',
            source_id='src_local',
            adapter='local_file',
            original_locator='/tmp/wikify-contract/notes/example.md',
            canonical_locator='/tmp/wikify-contract/notes/example.md',
            title='Example Note',
            body_text='Example body',
            markdown='Example body',
            captured_at='2026-04-30T00:00:00Z',
            published_at=None,
            author=None,
            raw_paths={
                'document': 'sources/raw/local_file/item_local/document.md',
                'document_path': '/tmp/wikify-contract/sources/raw/local_file/item_local/document.md',
            },
            assets=[],
            warnings=[],
            fingerprint={'kind': 'fetched', 'sha256': 'local'},
            metadata={},
        )

        item = source_item_from_normalized(document, status='new')

        self.assertEqual(item['source_type'], 'file')
        self.assertEqual(item['locator'], '/tmp/wikify-contract/notes/example.md')

    def test_normalized_document_defaults_source_id_for_direct_ingest(self):
        from wikify.ingest.artifacts import queue_entry_for_source_item, source_item_from_normalized
        from wikify.ingest.documents import NormalizedDocument

        document = NormalizedDocument(
            item_id='item_direct',
            source_id=None,
            adapter='wechat_url',
            original_locator='https://mp.weixin.qq.com/s/direct',
            canonical_locator='https://mp.weixin.qq.com/s/direct',
            title='Direct Article',
            body_text='Direct body',
            markdown='Direct body',
            captured_at='2026-04-30T00:00:00Z',
            published_at=None,
            author=None,
            raw_paths={
                'document': 'sources/raw/wechat_url/item_direct/document.md',
                'document_path': '/tmp/wikify-contract/sources/raw/wechat_url/item_direct/document.md',
            },
            assets=[],
            warnings=[],
            fingerprint={'kind': 'fetched', 'sha256': 'direct'},
            metadata={},
        )

        item = source_item_from_normalized(document, status='new')
        queue_entry = queue_entry_for_source_item(item, now='2026-04-30T00:00:00Z')

        self.assertEqual(item['source_id'], 'ingest:wechat_url')
        self.assertEqual(queue_entry['source_id'], 'ingest:wechat_url')
        self.assertEqual(queue_entry['evidence']['source_id'], 'ingest:wechat_url')


class IngestAdapterTests(unittest.TestCase):
    def test_adapter_registry_resolves_wechat_url(self):
        from wikify.ingest.adapters import resolve_adapter

        adapter = resolve_adapter('https://mp.weixin.qq.com/s/example')

        self.assertEqual(adapter.name, 'wechat_url')

    def test_adapter_registry_rejects_wechat_lookalike_host(self):
        from wikify.ingest.adapters import resolve_adapter
        from wikify.ingest.errors import IngestError

        with self.assertRaises(IngestError) as context:
            resolve_adapter('https://mp.weixin.qq.com.evil.example/s/example')

        self.assertEqual(context.exception.code, 'ingest_adapter_not_found')

    def test_explicit_wechat_adapter_rejects_incompatible_locator(self):
        from wikify.ingest.adapters import resolve_adapter
        from wikify.ingest.errors import IngestError

        with self.assertRaises(IngestError) as context:
            resolve_adapter('https://example.com/article', adapter_name='wechat_url')

        self.assertEqual(context.exception.code, 'ingest_adapter_not_found')
        self.assertEqual(context.exception.details['adapter'], 'wechat_url')
        self.assertEqual(context.exception.details['locator'], 'https://example.com/article')

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

    def test_wechat_fetch_uses_agent_browser_body_get_command(self):
        from wikify.ingest.documents import IngestRequest
        from wikify.ingest.wechat import WeChatUrlAdapter

        locator = 'https://mp.weixin.qq.com/s/example'
        responses = [
            subprocess.CompletedProcess(['agent-browser', 'open', locator], 0, stdout=''),
            subprocess.CompletedProcess(['agent-browser', 'get', 'html', 'body'], 0, stdout='<html></html>'),
            subprocess.CompletedProcess(['agent-browser', 'close'], 0, stdout=''),
            subprocess.CompletedProcess(['agent-browser', 'open', locator], 0, stdout=''),
            subprocess.CompletedProcess(['agent-browser', 'get', 'text', 'body'], 0, stdout='Example text'),
            subprocess.CompletedProcess(['agent-browser', 'close'], 0, stdout=''),
        ]

        with patch('subprocess.run', side_effect=responses) as run:
            WeChatUrlAdapter().fetch(IngestRequest(root='.', locator=locator))

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0:3], [
            ['agent-browser', 'open', locator],
            ['agent-browser', 'get', 'html', 'body'],
            ['agent-browser', 'close'],
        ])

    def test_wechat_fetch_get_failure_is_retryable_and_closes_browser(self):
        from wikify.ingest.documents import IngestRequest
        from wikify.ingest.errors import IngestError
        from wikify.ingest.wechat import WeChatUrlAdapter

        locator = 'https://mp.weixin.qq.com/s/example'
        responses = [
            subprocess.CompletedProcess(['agent-browser', 'open', locator], 0, stdout=''),
            subprocess.CompletedProcess(['agent-browser', 'get', 'html', 'body'], 1, stdout='', stderr='failed'),
            subprocess.CompletedProcess(['agent-browser', 'close'], 0, stdout=''),
        ]

        with patch('subprocess.run', side_effect=responses) as run:
            with self.assertRaises(IngestError) as context:
                WeChatUrlAdapter().fetch(IngestRequest(root='.', locator=locator))

        self.assertEqual(context.exception.code, 'ingest_fetch_failed')
        self.assertTrue(context.exception.retryable)
        self.assertEqual(run.call_args_list[-1].args[0], ['agent-browser', 'close'])

    def test_wechat_browser_close_failure_does_not_mask_successful_get(self):
        from wikify.ingest.wechat import WeChatUrlAdapter

        locator = 'https://mp.weixin.qq.com/s/example'
        responses = [
            subprocess.CompletedProcess(['agent-browser', 'open', locator], 0, stdout=''),
            subprocess.CompletedProcess(['agent-browser', 'get', 'html', 'body'], 0, stdout='<html>ok</html>'),
            subprocess.TimeoutExpired(['agent-browser', 'close'], timeout=15),
        ]

        with patch('subprocess.run', side_effect=responses):
            output = WeChatUrlAdapter()._run_browser(locator, 'html')

        self.assertEqual(output, '<html>ok</html>')


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
            absolute_path = Path(result['item']['path'])
            resolved_root = root.resolve()
            self.assertEqual(result['status'], 'completed')
            self.assertTrue(absolute_path.is_absolute())
            self.assertEqual(result['item']['relative_path'], absolute_path.relative_to(resolved_root).as_posix())
            self.assertTrue(absolute_path.exists())
            self.assertTrue((root / '.wikify' / 'ingest' / 'items' / f'{item_id}.json').exists())
            self.assertTrue((root / 'artifacts' / 'objects' / 'source_items' / f'{item_id}.json').exists())

            queue = json.loads((root / '.wikify' / 'queues' / 'ingest-items.json').read_text(encoding='utf-8'))
            self.assertEqual(queue['schema_version'], 'wikify.ingest-queue.v1')
            self.assertEqual(queue['summary']['queue_count'], 1)
            self.assertEqual(queue['entries'][0]['item_id'], item_id)

            source_items = json.loads((root / '.wikify' / 'sync' / 'source-items.json').read_text(encoding='utf-8'))
            self.assertIn(item_id, source_items['items'])

    def test_run_ingest_duplicate_url_keeps_single_queue_entry_created_at(self):
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            payload = {
                'html': (Path(__file__).parent / 'fixtures' / 'wechat_article.html').read_text(encoding='utf-8'),
                'text': (Path(__file__).parent / 'fixtures' / 'wechat_article.txt').read_text(encoding='utf-8'),
                'metadata': {'title': '统一 Ingest 设计', 'source_account': 'Wikify 产品笔记'},
            }

            with patch('wikify.ingest.pipeline.utc_now', return_value='2026-04-30T00:00:00Z'):
                first = run_ingest(
                    root,
                    'https://mp.weixin.qq.com/s/example',
                    adapter_name='wechat_url',
                    fetch_payload=payload,
                    refresh_views=False,
                )
                queue_path = root / '.wikify' / 'queues' / 'ingest-items.json'
                first_queue = json.loads(queue_path.read_text(encoding='utf-8'))
                first_entry = first_queue['entries'][0]

                second = run_ingest(
                    root,
                    'https://mp.weixin.qq.com/s/example',
                    adapter_name='wechat_url',
                    fetch_payload=payload,
                    refresh_views=False,
                )
            second_queue = json.loads(queue_path.read_text(encoding='utf-8'))
            second_entry = second_queue['entries'][0]
            run_artifacts = sorted((root / '.wikify' / 'ingest' / 'runs').glob('*.json'))

            self.assertEqual(first['item']['item_id'], second['item']['item_id'])
            self.assertNotEqual(first['run']['run_id'], second['run']['run_id'])
            self.assertEqual(len(run_artifacts), 2)
            self.assertEqual(second_queue['summary']['queue_count'], 1)
            self.assertEqual(len(second_queue['entries']), 1)
            self.assertEqual(second_entry['created_at'], first_entry['created_at'])
            self.assertGreaterEqual(second_entry['updated_at'], first_entry['updated_at'])

    def test_run_ingest_raises_typed_error_for_invalid_source_items_json(self):
        from wikify.ingest.artifacts import ingest_item_id
        from wikify.ingest.errors import IngestError
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            item_id = ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example')
            source_items_path = root / '.wikify' / 'sync' / 'source-items.json'
            source_items_path.parent.mkdir(parents=True, exist_ok=True)
            source_items_path.write_text('{not json', encoding='utf-8')

            with self.assertRaises(IngestError) as context:
                run_ingest(
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

            self.assertEqual(context.exception.code, 'ingest_artifact_invalid_json')
            self.assertEqual(context.exception.details['path'], str(source_items_path.resolve()))
            self.assertFalse((root / 'sources' / 'raw' / 'wechat_url' / item_id).exists())
            self.assertFalse((root / '.wikify' / 'ingest' / 'items' / f'{item_id}.json').exists())
            self.assertFalse(any((root / '.wikify' / 'ingest' / 'runs').glob('*.json')))
            self.assertFalse((root / 'artifacts' / 'objects' / 'source_items' / f'{item_id}.json').exists())

    def test_run_ingest_raises_typed_error_for_invalid_queue_entries_type(self):
        from wikify.ingest.artifacts import ingest_item_id
        from wikify.ingest.errors import IngestError
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            item_id = ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example')
            queue_path = root / '.wikify' / 'queues' / 'ingest-items.json'
            queue_path.parent.mkdir(parents=True, exist_ok=True)
            queue_path.write_text(json.dumps({
                'schema_version': 'wikify.ingest-queue.v1',
                'workspace_id': 'wk_test',
                'summary': {},
                'entries': {},
            }), encoding='utf-8')

            with self.assertRaises(IngestError) as context:
                run_ingest(
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

            self.assertEqual(context.exception.code, 'ingest_queue_invalid')
            self.assertEqual(context.exception.details['path'], str(queue_path.resolve()))
            self.assertFalse((root / 'sources' / 'raw' / 'wechat_url' / item_id).exists())
            self.assertFalse((root / '.wikify' / 'ingest' / 'items' / f'{item_id}.json').exists())
            self.assertFalse(any((root / '.wikify' / 'ingest' / 'runs').glob('*.json')))
            self.assertFalse((root / 'artifacts' / 'objects' / 'source_items' / f'{item_id}.json').exists())
            source_items_path = root / '.wikify' / 'sync' / 'source-items.json'
            if source_items_path.exists():
                source_items = json.loads(source_items_path.read_text(encoding='utf-8'))
                self.assertNotIn(item_id, source_items.get('items', {}))

    def test_run_ingest_raises_typed_error_for_invalid_queue_entry_member(self):
        from wikify.ingest.artifacts import ingest_item_id
        from wikify.ingest.errors import IngestError
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            item_id = ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example')
            queue_path = root / '.wikify' / 'queues' / 'ingest-items.json'
            queue_path.parent.mkdir(parents=True, exist_ok=True)
            queue_path.write_text(json.dumps({
                'schema_version': 'wikify.ingest-queue.v1',
                'workspace_id': 'wk_test',
                'summary': {},
                'entries': [1],
            }), encoding='utf-8')

            with self.assertRaises(IngestError) as context:
                run_ingest(
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

            self.assertEqual(context.exception.code, 'ingest_queue_invalid')
            self.assertEqual(context.exception.details['path'], str(queue_path.resolve()))
            self.assertEqual(context.exception.details['field'], 'entries[0]')
            self.assertFalse((root / 'sources' / 'raw' / 'wechat_url' / item_id).exists())
            self.assertFalse((root / '.wikify' / 'ingest' / 'items' / f'{item_id}.json').exists())
            self.assertFalse(any((root / '.wikify' / 'ingest' / 'runs').glob('*.json')))
            self.assertFalse((root / 'artifacts' / 'objects' / 'source_items' / f'{item_id}.json').exists())
            source_items_path = root / '.wikify' / 'sync' / 'source-items.json'
            if source_items_path.exists():
                source_items = json.loads(source_items_path.read_text(encoding='utf-8'))
                self.assertNotIn(item_id, source_items.get('items', {}))

    def test_run_ingest_raises_typed_error_for_invalid_source_item_member(self):
        from wikify.ingest.artifacts import ingest_item_id
        from wikify.ingest.errors import IngestError
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            item_id = ingest_item_id('wechat_url', 'https://mp.weixin.qq.com/s/example')
            source_items_path = root / '.wikify' / 'sync' / 'source-items.json'
            source_items_path.parent.mkdir(parents=True, exist_ok=True)
            source_items_path.write_text(json.dumps({
                'schema_version': 'wikify.source-items.v1',
                'workspace_id': 'wk_test',
                'summary': {},
                'items': {'old': 1},
            }), encoding='utf-8')

            with self.assertRaises(IngestError) as context:
                run_ingest(
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

            self.assertEqual(context.exception.code, 'ingest_source_items_invalid')
            self.assertEqual(context.exception.details['path'], str(source_items_path.resolve()))
            self.assertEqual(context.exception.details['field'], 'items.old')
            self.assertFalse((root / 'sources' / 'raw' / 'wechat_url' / item_id).exists())
            self.assertFalse((root / '.wikify' / 'ingest' / 'items' / f'{item_id}.json').exists())
            self.assertFalse(any((root / '.wikify' / 'ingest' / 'runs').glob('*.json')))
            self.assertFalse((root / 'artifacts' / 'objects' / 'source_items' / f'{item_id}.json').exists())
            source_items = json.loads(source_items_path.read_text(encoding='utf-8'))
            self.assertNotIn(item_id, source_items.get('items', {}))


class IngestHumanPathTests(unittest.TestCase):
    def test_default_ingest_wikiizes_and_refreshes_views(self):
        from wikify.agent import run_agent_export
        from wikify.ingest.pipeline import run_ingest
        from wikify.object_validation import validate_workspace_objects
        from wikify.sync import ingest_queue_path, source_items_path, sync_workspace
        from wikify.views import run_view_generation
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
            self.assertEqual(result['queue_entry']['status'], 'completed')
            self.assertEqual(result['next_actions'], [])

            queue = json.loads(ingest_queue_path(root).read_text(encoding='utf-8'))
            queue_entry = [entry for entry in queue['entries'] if entry['item_id'] == result['item']['item_id']][0]
            self.assertEqual(result['queue_entry']['status'], queue_entry['status'])

            validation = validate_workspace_objects(root, strict=True)
            self.assertEqual(validation['status'], 'passed')
            views_result = run_view_generation(root, dry_run=False, include_html=True, section='all')
            self.assertEqual(views_result['status'], 'completed')

            sync_result = sync_workspace(root)
            self.assertEqual(sync_result['status'], 'synced')
            source_items = json.loads(source_items_path(root).read_text(encoding='utf-8'))
            self.assertIn(result['item']['item_id'], source_items['items'])
            validation_after_sync = validate_workspace_objects(root, strict=True)
            self.assertEqual(validation_after_sync['status'], 'passed')
            views_after_sync = run_view_generation(root, dry_run=False, include_html=True, section='all')
            self.assertEqual(views_after_sync['status'], 'completed')
            agent_export = run_agent_export(root, dry_run=False)
            self.assertEqual(agent_export['status'], 'completed')

            run_record = json.loads((root / result['artifacts']['run']).read_text(encoding='utf-8'))
            self.assertEqual(run_record['status'], 'completed')
            self.assertEqual(run_record['queue_entry']['status'], 'completed')
            self.assertEqual(run_record['human_path']['wikiize']['status'], 'completed')
            self.assertTrue(run_record['human_entry']['body_path'].startswith('wiki/pages/'))

    def test_ingest_skips_human_path_when_refresh_views_false(self):
        from wikify.ingest.pipeline import run_ingest
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)

            result = run_ingest(
                root,
                'https://mp.weixin.qq.com/s/example',
                adapter_name='wechat_url',
                refresh_views=False,
                fetch_payload={
                    'html': (Path(__file__).parent / 'fixtures' / 'wechat_article.html').read_text(encoding='utf-8'),
                    'text': (Path(__file__).parent / 'fixtures' / 'wechat_article.txt').read_text(encoding='utf-8'),
                    'metadata': {'title': '统一 Ingest 设计', 'source_account': 'Wikify 产品笔记'},
                },
            )

            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['human_path'], {})
            self.assertEqual(result['human_entry'], {})
            self.assertEqual(result['queue_entry']['status'], 'queued')
            self.assertIn(f'wikify wikiize --item {result["item"]["item_id"]}', result['next_actions'])
            self.assertIn('wikify views', result['next_actions'])
            self.assertFalse((root / 'views' / 'index.md').exists())

    def test_human_path_failure_writes_failed_run_record(self):
        from wikify.ingest.pipeline import run_ingest
        from wikify.views import ViewGenerationError
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            error = ViewGenerationError('view boom', code='views_boom')

            with patch('wikify.ingest.pipeline.run_view_generation', side_effect=error):
                with self.assertRaises(ViewGenerationError):
                    run_ingest(
                        root,
                        'https://mp.weixin.qq.com/s/example',
                        adapter_name='wechat_url',
                        fetch_payload={
                            'html': (Path(__file__).parent / 'fixtures' / 'wechat_article.html').read_text(encoding='utf-8'),
                            'text': (Path(__file__).parent / 'fixtures' / 'wechat_article.txt').read_text(encoding='utf-8'),
                            'metadata': {'title': '统一 Ingest 设计', 'source_account': 'Wikify 产品笔记'},
                        },
                    )

            run_records = list((root / '.wikify' / 'ingest' / 'runs').glob('*.json'))
            self.assertEqual(len(run_records), 1)
            run_record = json.loads(run_records[0].read_text(encoding='utf-8'))
            self.assertEqual(run_record['status'], 'failed')
            self.assertEqual(run_record['error']['code'], 'views_boom')
            self.assertEqual(run_record['queue_entry']['status'], 'completed')
            self.assertIn('item', run_record['artifacts'])
            self.assertIn('raw_document', run_record['artifacts'])
