import json
import tempfile
import unittest
from pathlib import Path


class ViewGenerationTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
