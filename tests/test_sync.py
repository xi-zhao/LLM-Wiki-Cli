import json
import tempfile
import unittest
from pathlib import Path


class SyncWorkspaceTests(unittest.TestCase):
    def _read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding='utf-8'))

    def _init_workspace(self, root: Path):
        from wikify.workspace import initialize_workspace

        initialize_workspace(root)

    def _add_source(self, root: Path, locator: Path | str, source_type: str) -> dict:
        from wikify.workspace import add_source

        return add_source(root, str(locator), source_type)['source']

    def _items_by_id(self, document: dict) -> dict:
        self.assertIsInstance(document.get('items'), dict)
        return document['items']

    def _queue_entries(self, document: dict) -> list[dict]:
        self.assertIsInstance(document.get('entries'), list)
        return document['entries']

    def test_file_source_sync_writes_index_report_and_ingest_queue(self):
        from wikify.sync import ingest_queue_path, source_items_path, sync_report_path, sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            note = root / 'sources' / 'note.md'
            note.write_text('# Note\n', encoding='utf-8')
            source = self._add_source(root, note, 'file')

            result = sync_workspace(root)

            self.assertEqual(result['schema_version'], 'wikify.sync-run.v1')
            self.assertEqual(result['status'], 'synced')
            self.assertFalse(result['dry_run'])
            self.assertTrue(source_items_path(root).is_file())
            self.assertTrue(sync_report_path(root).is_file())
            self.assertTrue(ingest_queue_path(root).is_file())

            source_items = self._read_json(source_items_path(root))
            report = self._read_json(sync_report_path(root))
            queue = self._read_json(ingest_queue_path(root))

            self.assertEqual(source_items['schema_version'], 'wikify.source-items.v1')
            indexed_items = self._items_by_id(source_items)
            self.assertEqual(len(indexed_items), 1)
            item = next(iter(indexed_items.values()))
            self.assertEqual(item['source_id'], source['source_id'])
            self.assertTrue(item['item_id'].startswith('item_'))
            self.assertEqual(item['status'], 'new')
            self.assertEqual(item['fingerprint']['size_bytes'], len('# Note\n'.encode('utf-8')))
            self.assertIn('mtime_ns', item['fingerprint'])
            self.assertEqual(item['fingerprint']['hash_status'], 'hashed')

            self.assertEqual(report['schema_version'], 'wikify.sync-run.v1')
            self.assertEqual(report['summary']['item_status_counts']['new'], 1)
            self.assertEqual(report['summary']['queued_count'], 1)
            self.assertEqual(report['summary']['error_count'], 0)

            self.assertEqual(queue['schema_version'], 'wikify.ingest-queue.v1')
            entries = self._queue_entries(queue)
            self.assertEqual(len(entries), 1)
            queued = entries[0]
            self.assertTrue(queued['queue_id'].startswith('queue_'))
            self.assertEqual(queued['source_id'], source['source_id'])
            self.assertEqual(queued['item_id'], item['item_id'])
            self.assertEqual(queued['item_status'], 'new')
            self.assertEqual(queued['status'], 'queued')
            self.assertFalse(queued['requires_user'])
            self.assertTrue(queued['evidence'])
            self.assertTrue(queued['acceptance_checks'])

    def test_repeat_sync_is_unchanged_and_changed_sync_updates_existing_queue_entry(self):
        from wikify.sync import ingest_queue_path, sync_report_path, sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            note = root / 'sources' / 'note.md'
            note.write_text('# Note\n', encoding='utf-8')
            self._add_source(root, note, 'file')

            sync_workspace(root)
            initial_queue = self._read_json(ingest_queue_path(root))
            initial_entry = self._queue_entries(initial_queue)[0]

            sync_workspace(root)
            unchanged_report = self._read_json(sync_report_path(root))
            unchanged_queue = self._read_json(ingest_queue_path(root))

            self.assertEqual(unchanged_report['summary']['item_status_counts']['unchanged'], 1)
            self.assertEqual(unchanged_report['summary']['queued_count'], 0)
            self.assertEqual(len(self._queue_entries(unchanged_queue)), 1)
            self.assertEqual(self._queue_entries(unchanged_queue)[0]['queue_id'], initial_entry['queue_id'])

            note.write_text('# Note\n\nChanged.\n', encoding='utf-8')
            sync_workspace(root)
            changed_report = self._read_json(sync_report_path(root))
            changed_queue = self._read_json(ingest_queue_path(root))
            entries = self._queue_entries(changed_queue)

            self.assertEqual(changed_report['summary']['item_status_counts']['changed'], 1)
            self.assertEqual(changed_report['summary']['queued_count'], 1)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['queue_id'], initial_entry['queue_id'])
            self.assertEqual(entries[0]['item_status'], 'changed')

    def test_dry_run_reports_planned_sync_without_writing_artifacts_or_registry_metadata(self):
        from wikify.sync import ingest_queue_path, source_items_path, sync_report_path, sync_workspace
        from wikify.workspace import registry_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            note = root / 'sources' / 'note.md'
            note.write_text('# Note\n', encoding='utf-8')
            self._add_source(root, note, 'file')
            registry_before = self._read_json(registry_path(root))

            result = sync_workspace(root, dry_run=True)
            registry_after = self._read_json(registry_path(root))

            self.assertEqual(result['status'], 'dry_run')
            self.assertTrue(result['dry_run'])
            self.assertEqual(result['summary']['item_status_counts']['new'], 1)
            self.assertEqual(result['summary']['queued_count'], 1)
            self.assertFalse(source_items_path(root).exists())
            self.assertFalse(sync_report_path(root).exists())
            self.assertFalse(ingest_queue_path(root).exists())
            self.assertEqual(registry_after, registry_before)

    def test_directory_source_discovers_regular_files_sorted_and_records_skips_outside_queue(self):
        from wikify.sync import ingest_queue_path, sync_report_path, sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            source_root = root / 'sources' / 'collection'
            (source_root / 'nested').mkdir(parents=True)
            (source_root / 'nested' / 'b.md').write_text('B\n', encoding='utf-8')
            (source_root / 'a.md').write_text('A\n', encoding='utf-8')
            for ignored in ['.git', '.wikify', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build']:
                ignored_path = source_root / ignored
                ignored_path.mkdir(parents=True)
                (ignored_path / 'ignored.md').write_text('ignored\n', encoding='utf-8')
            self._add_source(root, source_root, 'directory')

            result = sync_workspace(root)
            report = self._read_json(sync_report_path(root))
            queue = self._read_json(ingest_queue_path(root))

            discovered = [item['relative_path'] for item in result['items'] if item['status'] == 'new']
            self.assertEqual(discovered, ['a.md', 'nested/b.md'])
            self.assertGreaterEqual(report['summary']['skipped_count'], 8)
            self.assertEqual(len(self._queue_entries(queue)), 2)
            for entry in self._queue_entries(queue):
                self.assertNotIn('ignored.md', json.dumps(entry, sort_keys=True))

    def test_local_repository_source_uses_directory_semantics_and_preserves_registry_metadata(self):
        from wikify.sync import sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            repo = root / 'sources' / 'repo'
            (repo / '.git').mkdir(parents=True)
            (repo / 'README.md').write_text('# Repo\n', encoding='utf-8')
            source = self._add_source(root, repo, 'repository')

            result = sync_workspace(root)

            self.assertEqual(result['summary']['item_status_counts']['new'], 1)
            self.assertEqual(result['sources'][0]['source_id'], source['source_id'])
            self.assertTrue(result['sources'][0]['source']['fingerprint']['git_dir_exists'])
            self.assertEqual(result['items'][0]['relative_path'], 'README.md')

    def test_url_and_remote_repository_sources_create_offline_remote_items(self):
        from wikify.sync import sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            self._add_source(root, 'https://example.com/report', 'url')
            self._add_source(root, 'https://github.com/example/repo', 'repository')

            result = sync_workspace(root)

            self.assertEqual(result['summary']['item_status_counts']['new'], 2)
            self.assertEqual(len(result['items']), 2)
            for item in result['items']:
                self.assertFalse(item['fingerprint']['network_checked'])
                self.assertNotIn('http_status', item['fingerprint'])

    def test_missing_local_sources_are_recorded_without_active_queue_entries(self):
        from wikify.sync import ingest_queue_path, sync_report_path, sync_workspace
        from wikify.workspace import registry_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            missing = root / 'sources' / 'missing.md'
            self._add_source(root, missing, 'file')

            result = sync_workspace(root)
            report = self._read_json(sync_report_path(root))
            queue = self._read_json(ingest_queue_path(root))
            registry = self._read_json(registry_path(root))

            self.assertEqual(result['summary']['item_status_counts']['missing'], 1)
            self.assertEqual(report['summary']['error_count'], 1)
            self.assertEqual(len(self._queue_entries(queue)), 0)
            source = next(iter(registry['sources'].values()))
            self.assertEqual(source['last_sync_status'], 'missing')
            self.assertEqual(source['last_sync_errors'][0]['code'], 'source_item_missing')

    def test_deleted_previously_indexed_local_item_becomes_missing_without_new_queue_entry(self):
        from wikify.sync import ingest_queue_path, sync_report_path, sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            note = root / 'sources' / 'note.md'
            note.write_text('# Note\n', encoding='utf-8')
            self._add_source(root, note, 'file')

            sync_workspace(root)
            note.unlink()
            sync_workspace(root)
            report = self._read_json(sync_report_path(root))
            queue = self._read_json(ingest_queue_path(root))

            self.assertEqual(report['summary']['item_status_counts']['missing'], 1)
            self.assertEqual(report['summary']['queued_count'], 0)
            self.assertEqual(self._queue_entries(queue)[0]['item_status'], 'new')

    def test_single_source_sync_updates_only_selected_source_items(self):
        from wikify.sync import source_items_path, sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            first = root / 'sources' / 'first.md'
            second = root / 'sources' / 'second.md'
            first.write_text('first\n', encoding='utf-8')
            second.write_text('second\n', encoding='utf-8')
            first_source = self._add_source(root, first, 'file')
            second_source = self._add_source(root, second, 'file')
            sync_workspace(root)
            before = self._items_by_id(self._read_json(source_items_path(root)))
            second_before = [
                item for item in before.values() if item['source_id'] == second_source['source_id']
            ][0]

            first.write_text('first changed\n', encoding='utf-8')
            result = sync_workspace(root, source_id=first_source['source_id'])
            after = self._items_by_id(self._read_json(source_items_path(root)))
            second_after = [
                item for item in after.values() if item['source_id'] == second_source['source_id']
            ][0]

            self.assertEqual([source['source_id'] for source in result['sources']], [first_source['source_id']])
            self.assertEqual(result['summary']['item_status_counts']['changed'], 1)
            self.assertEqual(second_after, second_before)

    def test_missing_selected_source_returns_typed_error(self):
        from wikify.sync import SyncError, sync_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)

            with self.assertRaises(SyncError) as raised:
                sync_workspace(root, source_id='src_missing')

            self.assertEqual(raised.exception.code, 'sync_source_not_found')
            self.assertEqual(raised.exception.details['source_id'], 'src_missing')
