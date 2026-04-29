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
