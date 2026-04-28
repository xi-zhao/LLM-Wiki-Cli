import shutil
import tempfile
import unittest
from pathlib import Path


class MaintenanceRunnerTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
