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
