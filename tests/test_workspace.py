import json
import tempfile
import unittest
from pathlib import Path


class WorkspaceTests(unittest.TestCase):
    def test_initialize_workspace_creates_manifest_registry_and_directories(self):
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = initialize_workspace(root)

            self.assertEqual(result['status'], 'initialized')
            self.assertTrue((root / 'wikify.json').is_file())
            self.assertTrue((root / '.wikify' / 'registry' / 'sources.json').is_file())
            for name in ['sources', 'wiki', 'artifacts', 'views']:
                self.assertTrue((root / name).is_dir())

            manifest = json.loads((root / 'wikify.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['schema_version'], 'wikify.workspace.v1')
            self.assertTrue(manifest['workspace_id'].startswith('wk_'))
            self.assertEqual(
                manifest['paths'],
                {
                    'sources': 'sources',
                    'wiki': 'wiki',
                    'artifacts': 'artifacts',
                    'views': 'views',
                    'state': '.wikify',
                },
            )

            registry = json.loads((root / '.wikify' / 'registry' / 'sources.json').read_text(encoding='utf-8'))
            self.assertEqual(registry['schema_version'], 'wikify.source-registry.v1')
            self.assertEqual(registry['workspace_id'], manifest['workspace_id'])
            self.assertEqual(registry['sources'], {})

    def test_initialize_workspace_is_idempotent_and_preserves_workspace_id(self):
        from wikify.workspace import initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            first = initialize_workspace(root)
            second = initialize_workspace(root)

            self.assertEqual(first['workspace']['workspace_id'], second['workspace']['workspace_id'])
            self.assertEqual(second['status'], 'initialized')

    def test_add_source_records_existing_file_with_stable_id_and_fingerprint(self):
        from wikify.workspace import add_source, initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            source_file = root / 'notes.md'
            source_file.write_text('# Notes\n', encoding='utf-8')

            result = add_source(root, str(source_file), 'file')
            record = result['source']

            self.assertEqual(result['status'], 'added')
            self.assertTrue(record['source_id'].startswith('src_'))
            self.assertEqual(record['type'], 'file')
            self.assertEqual(record['last_sync_status'], 'never_synced')
            self.assertEqual(record['discovery_status'], 'found')
            self.assertEqual(record['fingerprint']['exists'], True)
            self.assertEqual(record['fingerprint']['kind'], 'file')

    def test_add_source_is_idempotent_for_same_canonical_locator(self):
        from wikify.workspace import add_source, initialize_workspace, list_sources

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            source_file = root / 'notes.md'
            source_file.write_text('# Notes\n', encoding='utf-8')

            first = add_source(root, str(source_file), 'file')
            second = add_source(root, str(source_file.resolve()), 'file')
            listing = list_sources(root)

            self.assertEqual(second['status'], 'existing')
            self.assertEqual(first['source']['source_id'], second['source']['source_id'])
            self.assertEqual(listing['summary']['source_count'], 1)

    def test_add_source_records_missing_local_file_with_error(self):
        from wikify.workspace import add_source, initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            missing = root / 'missing.md'

            result = add_source(root, str(missing), 'file')
            record = result['source']

            self.assertEqual(record['discovery_status'], 'missing')
            self.assertEqual(record['last_sync_status'], 'never_synced')
            self.assertTrue(record['errors'])
            self.assertEqual(record['errors'][0]['code'], 'source_missing')

    def test_add_url_source_normalizes_without_network_metadata(self):
        from wikify.workspace import add_source, initialize_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)

            result = add_source(root, 'HTTPS://Example.COM:443/a/../b?x=1#frag', 'url')
            record = result['source']

            self.assertEqual(record['type'], 'url')
            self.assertEqual(record['discovery_status'], 'unverified')
            self.assertEqual(record['last_sync_status'], 'never_synced')
            self.assertIn('https://example.com/b?x=1', record['locator_key'])
            self.assertEqual(record['fingerprint']['network_checked'], False)

    def test_list_sources_returns_sources_sorted_by_created_at_then_id(self):
        from wikify.workspace import add_source, initialize_workspace, list_sources

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            b = add_source(root, 'https://example.com/b', 'url')
            a = add_source(root, 'https://example.com/a', 'url')

            listing = list_sources(root)

            self.assertEqual(listing['summary']['source_count'], 2)
            self.assertEqual(
                [item['source_id'] for item in listing['sources']],
                sorted([b['source']['source_id'], a['source']['source_id']]),
            )

    def test_show_source_returns_record_or_structured_not_found_error(self):
        from wikify.workspace import WorkspaceError, add_source, initialize_workspace, show_source

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialize_workspace(root)
            added = add_source(root, 'https://example.com/a', 'url')

            shown = show_source(root, added['source']['source_id'])

            self.assertEqual(shown['source'], added['source'])
            with self.assertRaises(WorkspaceError) as caught:
                show_source(root, 'src_missing')
            self.assertEqual(caught.exception.code, 'source_not_found')

    def test_add_source_requires_initialized_workspace(self):
        from wikify.workspace import WorkspaceError, add_source

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(WorkspaceError) as caught:
                add_source(Path(tmp), 'https://example.com/a', 'url')
            self.assertEqual(caught.exception.code, 'workspace_missing')


if __name__ == '__main__':
    unittest.main()
