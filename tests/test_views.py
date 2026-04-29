import json
import tempfile
import unittest
from pathlib import Path


class ViewGenerationTests(unittest.TestCase):
    def _read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding='utf-8'))

    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _init_workspace(self, root: Path):
        from wikify.workspace import initialize_workspace

        initialize_workspace(root)

    def _add_source(self, root: Path, locator: Path | str, source_type: str) -> dict:
        from wikify.workspace import add_source

        return add_source(root, str(locator), source_type)['source']

    def _sync(self, root: Path):
        from wikify.sync import sync_workspace

        return sync_workspace(root)

    def _wikiize(self, root: Path):
        from wikify.wikiize import run_wikiization

        return run_wikiization(root)

    def _write_note_workspace(self, root: Path, content: str = '# Source Title\n\nImportant source detail.\n') -> tuple[Path, dict, dict]:
        self._init_workspace(root)
        source_path = root / 'sources' / 'source.md'
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(content, encoding='utf-8')
        source = self._add_source(root, source_path, 'file')
        sync_result = self._sync(root)
        item = sync_result['items'][0]
        self._wikiize(root)
        return source_path, source, item

    def _write_semantic_object_fixtures(self, root: Path, source: dict, item: dict):
        from wikify.objects import (
            make_citation_object,
            make_decision_object,
            make_object_index,
            make_person_object,
            make_project_object,
            make_timeline_entry_object,
            make_topic_object,
            object_document_path,
            object_index_path,
        )

        page_object = next((root / 'artifacts' / 'objects' / 'wiki_pages').glob('*.json'))
        page = self._read_json(page_object)
        source_refs = [{'source_id': source['source_id'], 'item_id': item['item_id'], 'confidence': 0.91}]
        objects = [
            page,
            make_topic_object(
                object_id='topic_agent_context',
                title='Agent Context',
                summary='Durable context for coding agents.',
                page_ids=[page['id']],
                source_refs=source_refs,
            ),
            make_project_object(
                object_id='project_wikify',
                title='Wikify',
                summary='CLI-first personal wiki generator.',
                page_ids=[page['id']],
                source_refs=source_refs,
            ),
            make_person_object(
                object_id='person_user',
                title='Knowledge Owner',
                summary='The person maintaining the knowledge base.',
                page_ids=[page['id']],
                source_refs=source_refs,
            ),
            make_decision_object(
                object_id='decision_cli_first',
                title='Keep Wikify CLI-first',
                summary='The CLI remains the control surface.',
                status='accepted',
                source_refs=source_refs,
            ),
            make_timeline_entry_object(
                object_id='timeline_first_wiki',
                title='First Wiki Page Generated',
                summary='The first source-backed page became visible in human views.',
                timestamp='2026-04-29T00:00:00Z',
                source_refs=source_refs,
            ),
            make_citation_object(
                object_id='citation_source_title',
                source_id=source['source_id'],
                item_id=item['item_id'],
                locator='sources/source.md#L1',
                confidence=0.91,
                snippet='Source Title',
            ),
        ]
        for obj in objects[1:]:
            self._write_json(object_document_path(root, obj['type'], obj['id']), obj)
        self._write_json(object_index_path(root), make_object_index(root, objects))
        return page

    def test_dry_run_reports_planned_views_without_writes(self):
        from wikify.views import (
            VIEWS_RUN_SCHEMA_VERSION,
            run_view_generation,
            view_task_queue_path,
            views_manifest_path,
            views_report_path,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_note_workspace(root)

            result = run_view_generation(root, dry_run=True)

            self.assertEqual(result['schema_version'], VIEWS_RUN_SCHEMA_VERSION)
            self.assertEqual(result['status'], 'dry_run')
            self.assertTrue(result['dry_run'])
            self.assertEqual(result['summary']['conflict_count'], 0)
            self.assertGreaterEqual(result['summary']['planned_view_count'], 6)
            self.assertGreaterEqual(result['summary']['planned_html_count'], 6)
            self.assertGreaterEqual(result['summary']['warning_count'], 1)
            self.assertEqual(result['summary']['source_count'], 1)
            self.assertEqual(result['summary']['object_counts_by_type']['wiki_page'], 1)
            planned_paths = {view['path'] for view in result['views']}
            self.assertIn('views/index.md', planned_paths)
            self.assertIn('views/pages.md', planned_paths)
            self.assertIn('views/sources/index.md', planned_paths)
            self.assertIn('views/graph.md', planned_paths)
            self.assertIn('views/timeline.md', planned_paths)
            self.assertIn('views/review.md', planned_paths)
            html_paths = {item['path'] for item in result['html']}
            self.assertIn('views/site/index.html', html_paths)
            self.assertIn('views/site/pages.html', html_paths)
            self.assertIn('views/site/sources/index.html', html_paths)
            self.assertFalse((root / 'views' / 'index.md').exists())
            self.assertFalse((root / 'views' / 'site').exists())
            self.assertFalse(views_report_path(root).exists())
            self.assertFalse(views_manifest_path(root).exists())
            self.assertFalse(view_task_queue_path(root).exists())

    def test_dry_run_no_html_omits_planned_html_paths(self):
        from wikify.views import run_view_generation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_note_workspace(root)

            result = run_view_generation(root, dry_run=True, include_html=False)

            self.assertEqual(result['status'], 'dry_run')
            self.assertEqual(result['summary']['planned_html_count'], 0)
            self.assertEqual(result['html'], [])
            self.assertFalse((root / 'views' / 'site').exists())

    def test_generate_markdown_views_from_workspace_artifacts(self):
        from wikify.views import run_view_generation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _source_path, source, item = self._write_note_workspace(root)
            page = self._write_semantic_object_fixtures(root, source, item)

            result = run_view_generation(root, include_html=False)

            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['summary']['generated_view_count'], len(result['views']))
            home = (root / 'views' / 'index.md').read_text(encoding='utf-8')
            self.assertIn('# Wikify', home)
            self.assertIn('Recent Updates', home)
            self.assertIn('Sources', home)
            self.assertIn('Pages', home)
            self.assertIn('Graph', home)
            self.assertIn('Timeline', home)
            self.assertIn('Review', home)

            pages = (root / 'views' / 'pages.md').read_text(encoding='utf-8')
            self.assertIn(page['title'], pages)
            self.assertIn(page['id'], pages)
            self.assertIn(page['review_status'], pages)
            self.assertIn(str(page['confidence']), pages)
            self.assertIn(source['source_id'], pages)
            self.assertIn('../wiki/pages/', pages)

            source_index = (root / 'views' / 'sources' / 'index.md').read_text(encoding='utf-8')
            self.assertIn(source['source_id'], source_index)
            self.assertIn(f'{source["source_id"]}.md', source_index)

            source_page = (root / 'views' / 'sources' / f'{source["source_id"]}.md').read_text(encoding='utf-8')
            self.assertIn(f'# Source {source["source_id"]}', source_page)
            self.assertIn('Type: `file`', source_page)
            self.assertIn(str(_source_path), source_page)
            self.assertIn('Last sync status:', source_page)
            self.assertIn(page['title'], source_page)
            self.assertIn('citation_source_title', source_page)
            self.assertIn('No unresolved wikiization tasks', source_page)

            self.assertIn('Agent Context', (root / 'views' / 'topics' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('Wikify', (root / 'views' / 'projects' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('Knowledge Owner', (root / 'views' / 'people' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('Keep Wikify CLI-first', (root / 'views' / 'decisions' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('Durable context for coding agents.', (root / 'views' / 'topics' / 'topic_agent_context.md').read_text(encoding='utf-8'))
            self.assertIn('2026-04-29T00:00:00Z', (root / 'views' / 'timeline.md').read_text(encoding='utf-8'))
            self.assertIn('Graph artifacts are not available yet.', (root / 'views' / 'graph.md').read_text(encoding='utf-8'))
            self.assertIn('Warnings', (root / 'views' / 'review.md').read_text(encoding='utf-8'))

    def test_generate_empty_collection_and_timeline_views_without_inventing_entities(self):
        from wikify.views import run_view_generation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_note_workspace(root)

            run_view_generation(root, include_html=False)

            self.assertIn('No topic objects exist yet.', (root / 'views' / 'topics' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('No project objects exist yet.', (root / 'views' / 'projects' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('No person objects exist yet.', (root / 'views' / 'people' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('No decision objects exist yet.', (root / 'views' / 'decisions' / 'index.md').read_text(encoding='utf-8'))
            self.assertIn('No timeline entries exist yet.', (root / 'views' / 'timeline.md').read_text(encoding='utf-8'))
            self.assertNotIn('Source Title.md', (root / 'views' / 'topics' / 'index.md').read_text(encoding='utf-8'))

    def test_generate_static_html_with_local_assets_and_escaped_content(self):
        from wikify.views import run_view_generation

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_note_workspace(root, content='# Unsafe <Name>\n\nNo scripts should execute.\n')

            result = run_view_generation(root)

            self.assertEqual(result['status'], 'completed')
            self.assertTrue((root / 'views' / 'site' / 'index.html').exists())
            self.assertTrue((root / 'views' / 'site' / 'pages.html').exists())
            self.assertTrue((root / 'views' / 'site' / 'sources' / 'index.html').exists())
            self.assertTrue((root / 'views' / 'site' / 'assets' / 'style.css').exists())
            self.assertGreaterEqual(result['summary']['generated_html_count'], 6)

            home_html = (root / 'views' / 'site' / 'index.html').read_text(encoding='utf-8')
            pages_html = (root / 'views' / 'site' / 'pages.html').read_text(encoding='utf-8')
            source_index_html = (root / 'views' / 'site' / 'sources' / 'index.html').read_text(encoding='utf-8')
            css = (root / 'views' / 'site' / 'assets' / 'style.css').read_text(encoding='utf-8')

            self.assertIn('<!doctype html>', home_html)
            self.assertIn('<h1>Wikify</h1>', home_html)
            self.assertIn('href="pages.html"', home_html)
            self.assertIn('href="assets/style.css"', home_html)
            self.assertIn('&lt;Name&gt;', pages_html)
            self.assertNotIn('<Name>', pages_html)
            self.assertIn('href="../assets/style.css"', source_index_html)
            self.assertIn('font-family:', css)
            self.assertNotIn('https://', home_html + pages_html + source_index_html + css)
            self.assertNotIn('<script', home_html + pages_html + source_index_html + css)

    def test_generated_markdown_views_are_hash_guarded_against_user_edits(self):
        from wikify.views import run_view_generation, view_task_queue_path, views_manifest_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_note_workspace(root)
            first = run_view_generation(root, include_html=False)
            self.assertEqual(first['status'], 'completed')
            index_path = root / 'views' / 'index.md'
            original_manifest = self._read_json(views_manifest_path(root))
            original_hash = original_manifest['files']['views/index.md']['sha256']
            index_path.write_text(index_path.read_text(encoding='utf-8') + '\nUser retained note.\n', encoding='utf-8')

            second = run_view_generation(root, include_html=False)

            self.assertEqual(second['status'], 'completed_with_conflicts')
            self.assertEqual(second['summary']['conflict_count'], 1)
            self.assertIn('User retained note.', index_path.read_text(encoding='utf-8'))
            next_manifest = self._read_json(views_manifest_path(root))
            self.assertEqual(next_manifest['files']['views/index.md']['sha256'], original_hash)
            queue = self._read_json(view_task_queue_path(root))
            self.assertEqual(queue['schema_version'], 'wikify.view-tasks.v1')
            self.assertEqual(queue['summary']['task_count'], 1)
            task = queue['tasks'][0]
            self.assertFalse(task['requires_user'])
            self.assertEqual(task['reason_code'], 'generated_view_drifted')
            self.assertEqual(task['target_paths']['view_path'], 'views/index.md')


if __name__ == '__main__':
    unittest.main()
