import json
import shutil
import tempfile
import unittest
from pathlib import Path


class MaintenanceRunnerTests(unittest.TestCase):
    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def test_run_maintenance_writes_graph_and_maintenance_artifacts(self):
        from wikify.maintenance.runner import run_maintenance

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir) / 'sample-kb'
            shutil.copytree(repo / 'sample-kb', kb)

            result = run_maintenance(kb, policy='balanced', dry_run=False)

            self.assertEqual(result['policy'], 'balanced')
            for key in ['finding_count', 'planned_count', 'executed_count', 'queued_count']:
                self.assertIn(key, result['summary'])
            self.assertTrue((kb / 'graph' / 'graph.json').exists())
            self.assertTrue((kb / 'sorted' / 'graph-findings.json').exists())
            self.assertTrue((kb / 'sorted' / 'graph-maintenance-plan.json').exists())
            self.assertTrue((kb / 'sorted' / 'graph-maintenance-history.json').exists())
            self.assertTrue((kb / 'sorted' / 'graph-agent-tasks.json').exists())
            self.assertIn('task_count', result['summary'])
            self.assertIn('task_queue', result)
            self.assertIsInstance(result['next_commands'], list)

    def test_dry_run_writes_graph_but_not_maintenance_artifacts(self):
        from wikify.maintenance.runner import run_maintenance

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir) / 'sample-kb'
            shutil.copytree(repo / 'sample-kb', kb)

            result = run_maintenance(kb, policy='balanced', dry_run=True)

            self.assertTrue(result['dry_run'])
            self.assertTrue((kb / 'graph' / 'graph.json').exists())
            self.assertFalse((kb / 'sorted' / 'graph-findings.json').exists())
            self.assertFalse((kb / 'sorted' / 'graph-maintenance-plan.json').exists())
            self.assertFalse((kb / 'sorted' / 'graph-maintenance-history.json').exists())
            self.assertFalse((kb / 'sorted' / 'graph-agent-tasks.json').exists())
            self.assertIn('task_queue', result)

    def test_run_maintenance_enriches_generated_page_tasks(self):
        from wikify.maintenance.runner import run_maintenance

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_refs = [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}]
            self._write_json(
                root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_alpha.json',
                {
                    'schema_version': 'wikify.wiki-page.v1',
                    'id': 'page_alpha',
                    'type': 'wiki_page',
                    'title': 'Alpha',
                    'summary': 'Alpha summary.',
                    'body_path': 'wiki/pages/page_alpha.md',
                    'source_refs': source_refs,
                    'outbound_links': [],
                    'backlinks': [],
                    'created_at': '2026-04-30T00:00:00Z',
                    'updated_at': '2026-04-30T00:00:00Z',
                    'confidence': 0.9,
                    'review_status': 'generated',
                },
            )
            (root / 'wiki' / 'pages').mkdir(parents=True, exist_ok=True)
            (root / 'wiki' / 'pages' / 'page_alpha.md').write_text(
                '---\n'
                'schema_version: wikify.wiki-page.v1\n'
                'id: page_alpha\n'
                'type: wiki_page\n'
                'title: Alpha\n'
                'body_path: wiki/pages/page_alpha.md\n'
                'source_refs: [{"source_id": "src_notes", "item_id": "item_alpha", "confidence": 0.9}]\n'
                'review_status: generated\n'
                '---\n'
                '# Alpha\n\nBroken [[Missing Target]].\n',
                encoding='utf-8',
            )

            result = run_maintenance(root, policy='balanced', dry_run=False)

            self.assertEqual(result['targets']['schema_version'], 'wikify.maintenance-targets.v1')
            task = next(
                task
                for task in result['task_queue']['tasks']
                if task.get('target') == 'wiki/pages/page_alpha.md'
            )
            self.assertEqual(task['target_family'], 'personal_wiki_page')
            self.assertEqual(task['object_id'], 'page_alpha')
            self.assertEqual(task['body_path'], 'wiki/pages/page_alpha.md')
            self.assertEqual(task['review_status'], 'generated')
            self.assertEqual(task['write_scope'], ['wiki/pages/page_alpha.md'])
            task_queue = json.loads((root / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
            self.assertEqual(task_queue['schema_version'], 'wikify.graph-agent-tasks.v1')


if __name__ == '__main__':
    unittest.main()
