import json
import sys
import tempfile
import unittest
from pathlib import Path


class WikiizeTests(unittest.TestCase):
    def _read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding='utf-8'))

    def _init_workspace(self, root: Path):
        from wikify.workspace import initialize_workspace

        initialize_workspace(root)

    def _add_source(self, root: Path, locator: Path | str, source_type: str) -> dict:
        from wikify.workspace import add_source

        return add_source(root, str(locator), source_type)['source']

    def _sync(self, root: Path):
        from wikify.sync import sync_workspace

        return sync_workspace(root)

    def _write_note_workspace(self, root: Path, content: str = '# Note\n\nFirst useful line.\n') -> tuple[Path, dict, dict]:
        self._init_workspace(root)
        source_path = root / 'sources' / 'note.md'
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(content, encoding='utf-8')
        source = self._add_source(root, source_path, 'file')
        sync_result = self._sync(root)
        item = sync_result['items'][0]
        return source_path, source, item

    def _queue_entries(self, root: Path) -> list[dict]:
        from wikify.sync import ingest_queue_path

        return self._read_json(ingest_queue_path(root))['entries']

    def _generated_page_paths(self, root: Path) -> list[Path]:
        pages = root / 'wiki' / 'pages'
        if not pages.exists():
            return []
        return sorted(pages.glob('*.md'))

    def test_dry_run_reports_planned_paths_without_writes(self):
        from wikify.sync import ingest_queue_path
        from wikify.wikiize import (
            WIKIIZATION_RUN_SCHEMA_VERSION,
            run_wikiization,
            wiki_pages_dir,
            wikiization_task_queue_path,
            wikiize_report_path,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, _source, item = self._write_note_workspace(root)
            queue_before = self._read_json(ingest_queue_path(root))

            result = run_wikiization(root, dry_run=True)

            self.assertEqual(result['schema_version'], WIKIIZATION_RUN_SCHEMA_VERSION)
            self.assertEqual(result['status'], 'dry_run')
            self.assertTrue(result['dry_run'])
            self.assertEqual(result['summary']['selected_count'], 1)
            self.assertEqual(result['summary']['planned_count'], 1)
            planned = result['items'][0]
            self.assertEqual(planned['item_id'], item['item_id'])
            self.assertEqual(planned['outcome'], 'planned')
            self.assertIn('wiki/pages/', planned['planned_paths']['body_path'])
            self.assertIn('artifacts/objects/wiki_pages/', planned['planned_paths']['object_path'])
            self.assertFalse(wiki_pages_dir(root).exists())
            self.assertFalse(wikiize_report_path(root).exists())
            self.assertFalse(wikiization_task_queue_path(root).exists())
            self.assertEqual(self._read_json(ingest_queue_path(root)), queue_before)

    def test_selectors_filter_queue_entries(self):
        from wikify.wikiize import run_wikiization

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            first_path = root / 'sources' / 'first.md'
            second_path = root / 'sources' / 'second.md'
            first_path.parent.mkdir(parents=True, exist_ok=True)
            first_path.write_text('# First\n', encoding='utf-8')
            second_path.write_text('# Second\n', encoding='utf-8')
            first_source = self._add_source(root, first_path, 'file')
            second_source = self._add_source(root, second_path, 'file')
            sync_result = self._sync(root)
            first_item = [item for item in sync_result['items'] if item['source_id'] == first_source['source_id']][0]
            second_item = [item for item in sync_result['items'] if item['source_id'] == second_source['source_id']][0]
            entries = self._queue_entries(root)
            first_queue = [entry for entry in entries if entry['item_id'] == first_item['item_id']][0]

            by_source = run_wikiization(root, dry_run=True, source_id=second_source['source_id'])
            by_item = run_wikiization(root, dry_run=True, item_id=first_item['item_id'])
            by_queue = run_wikiization(root, dry_run=True, queue_id=first_queue['queue_id'])
            limited = run_wikiization(root, dry_run=True, limit=1)

            self.assertEqual([item['item_id'] for item in by_source['items']], [second_item['item_id']])
            self.assertEqual([item['item_id'] for item in by_item['items']], [first_item['item_id']])
            self.assertEqual([item['queue_id'] for item in by_queue['items']], [first_queue['queue_id']])
            self.assertEqual(len(limited['items']), 1)
            self.assertEqual(limited['summary']['selected_count'], 1)

    def test_missing_control_artifacts_raise_typed_error(self):
        from wikify.wikiize import WikiizeError, run_wikiization

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)

            with self.assertRaises(WikiizeError) as raised:
                run_wikiization(root)

            self.assertEqual(raised.exception.code, 'wikiize_source_items_missing')
            self.assertIn('path', raised.exception.details)

    def test_local_markdown_source_writes_page_object_index_validation_and_queue_completion(self):
        from wikify.frontmatter import split_front_matter
        from wikify.objects import object_index_path
        from wikify.sync import ingest_queue_path
        from wikify.wikiize import run_wikiization, wikiize_report_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, source, item = self._write_note_workspace(root, '# Source Title\n\nImportant source detail.\n')

            result = run_wikiization(root)

            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['summary']['completed_count'], 1)
            page_path = self._generated_page_paths(root)[0]
            metadata, body = split_front_matter(page_path.read_text(encoding='utf-8'))
            self.assertEqual(metadata['schema_version'], 'wikify.wiki-page.v1')
            self.assertEqual(metadata['type'], 'wiki_page')
            self.assertEqual(metadata['title'], 'Source Title')
            self.assertEqual(metadata['body_path'], page_path.relative_to(root).as_posix())
            self.assertEqual(metadata['source_refs'][0]['source_id'], source['source_id'])
            self.assertEqual(metadata['source_refs'][0]['item_id'], item['item_id'])
            self.assertIn('# Source Title', body)
            self.assertIn('## Source References', body)
            self.assertIn('Important source detail.', body)

            object_path = Path(result['items'][0]['paths']['object_path'])
            page_object = self._read_json(root / object_path)
            self.assertEqual(page_object['schema_version'], 'wikify.wiki-page.v1')
            self.assertEqual(page_object['id'], metadata['id'])
            self.assertEqual(page_object['body_path'], metadata['body_path'])
            self.assertEqual(page_object['source_refs'][0]['item_id'], item['item_id'])
            self.assertIn('generation', page_object)
            self.assertIn('markdown_sha256', page_object['generation'])

            object_index = self._read_json(object_index_path(root))
            self.assertIn(page_object['id'], [entry['id'] for entry in object_index['objects']])
            validation = self._read_json(root / 'artifacts' / 'objects' / 'validation.json')
            self.assertEqual(validation['status'], 'passed')
            self.assertEqual(validation['summary']['error_count'], 0)

            queue = self._read_json(ingest_queue_path(root))
            queue_entry = queue['entries'][0]
            self.assertEqual(queue_entry['status'], 'completed')
            self.assertEqual(queue_entry['object_ids'], [page_object['id']])
            self.assertIn('completed_at', queue_entry)
            report = self._read_json(wikiize_report_path(root))
            self.assertEqual(report['summary']['completed_count'], 1)

    def test_incremental_update_reuses_object_and_protects_user_edit(self):
        from wikify.sync import sync_workspace
        from wikify.wikiize import run_wikiization, wikiization_task_queue_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_path, _source, _item = self._write_note_workspace(root, '# Title\n\nFirst version.\n')

            first = run_wikiization(root)
            first_item = first['items'][0]
            first_page = root / first_item['paths']['body_path']
            first_object_id = first_item['object_ids'][0]

            source_path.write_text('# Title\n\nSecond version.\n', encoding='utf-8')
            sync_workspace(root)
            second = run_wikiization(root)
            second_item = second['items'][0]
            second_page = root / second_item['paths']['body_path']

            self.assertEqual(second_item['object_ids'][0], first_object_id)
            self.assertEqual(second_page, first_page)
            self.assertIn('Second version.', second_page.read_text(encoding='utf-8'))

            edited_content = second_page.read_text(encoding='utf-8') + '\nUser edit.\n'
            second_page.write_text(edited_content, encoding='utf-8')
            source_path.write_text('# Title\n\nThird version.\n', encoding='utf-8')
            sync_workspace(root)
            third = run_wikiization(root)

            self.assertEqual(third['summary']['needs_review_count'], 1)
            self.assertEqual(second_page.read_text(encoding='utf-8'), edited_content)
            task_queue = self._read_json(wikiization_task_queue_path(root))
            self.assertEqual(task_queue['schema_version'], 'wikify.wikiization-tasks.v1')
            self.assertEqual(task_queue['tasks'][0]['reason_code'], 'generated_page_drifted')
            self.assertFalse(task_queue['tasks'][0]['requires_user'])

    def test_remote_without_agent_creates_task_without_page(self):
        from wikify.wikiize import run_wikiization, wikiization_task_queue_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            self._add_source(root, 'https://example.com/report', 'url')
            self._sync(root)

            result = run_wikiization(root)

            self.assertEqual(result['summary']['needs_review_count'], 1)
            self.assertEqual(self._generated_page_paths(root), [])
            task_queue = self._read_json(wikiization_task_queue_path(root))
            self.assertEqual(task_queue['tasks'][0]['reason_code'], 'remote_without_content')
            self.assertEqual(task_queue['tasks'][0]['status'], 'queued')

    def test_agent_command_receives_request_and_writes_validated_page(self):
        from wikify.wikiize import run_wikiization

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._init_workspace(root)
            self._add_source(root, 'https://example.com/report', 'url')
            self._sync(root)
            script = root / 'agent.py'
            script.write_text(
                '\n'.join([
                    'import json',
                    'import sys',
                    'request = json.load(sys.stdin)',
                    'result = {',
                    '    "schema_version": "wikify.wikiization-result.v1",',
                    '    "queue_id": request["queue_id"],',
                    '    "title": "Remote Report",',
                    '    "summary": "Source-backed remote report summary.",',
                    '    "body": "# Remote Report\\n\\nAgent supplied bounded notes.\\n",',
                    '    "confidence": 0.72,',
                    '    "review_status": "needs_review",',
                    '    "source_refs": request["source_refs"],',
                    '    "outbound_links": [],',
                    '}',
                    'print(json.dumps(result))',
                ]),
                encoding='utf-8',
            )

            result = run_wikiization(root, agent_command=f'{sys.executable} {script}')

            self.assertEqual(result['summary']['completed_count'], 1)
            item_result = result['items'][0]
            self.assertIn('.wikify/wikiization/requests/', item_result['paths']['request_path'])
            self.assertIn('.wikify/wikiization/results/', item_result['paths']['result_path'])
            request = self._read_json(root / item_result['paths']['request_path'])
            saved_result = self._read_json(root / item_result['paths']['result_path'])
            self.assertEqual(request['schema_version'], 'wikify.wikiization-request.v1')
            self.assertEqual(saved_result['schema_version'], 'wikify.wikiization-result.v1')
            page = root / item_result['paths']['body_path']
            self.assertIn('Agent supplied bounded notes.', page.read_text(encoding='utf-8'))
            validation = self._read_json(root / 'artifacts' / 'objects' / 'validation.json')
            self.assertEqual(validation['status'], 'passed')

    def test_agent_command_and_profile_conflict_raises_profile_error(self):
        from wikify.maintenance.agent_profile import AgentProfileError
        from wikify.wikiize import run_wikiization

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_note_workspace(root)

            with self.assertRaises(AgentProfileError) as raised:
                run_wikiization(root, agent_command='python3 agent.py', agent_profile='default')

            self.assertEqual(raised.exception.code, 'agent_profile_ambiguous')


if __name__ == '__main__':
    unittest.main()
