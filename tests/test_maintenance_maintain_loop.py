import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


class MaintenanceLoopTests(unittest.TestCase):
    def _copy_sample_kb(self, tmpdir: str) -> Path:
        repo = Path(__file__).resolve().parents[1]
        kb = Path(tmpdir) / 'sample-kb'
        shutil.copytree(repo / 'sample-kb', kb)
        return kb

    def _write_link_repair_agent(self, kb: Path) -> Path:
        script = kb / 'link_repair_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'target = request["targets"][0]',
                'edit = request["proposal"]["planned_edits"][0]',
                'missing = edit["evidence"]["target"]',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": request["proposal_path"],',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": target["path"],',
                '            "find": f"[[{missing}]]",',
                '            "replace": "[[agent-knowledge-loops]]",',
                '            "rationale": "resolve sample broken wikilink"',
                '        }',
                '    ]',
                '}',
                'print(json.dumps(bundle))',
            ]),
            encoding='utf-8',
        )
        return script

    def _read_queue(self, kb: Path) -> dict:
        return json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))

    def test_maintain_loop_runs_until_no_selected_tasks(self):
        from wikify.maintenance.maintain_loop import run_maintenance_loop

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)
            script = self._write_link_repair_agent(kb)

            result = run_maintenance_loop(
                kb,
                action='queue_link_repair',
                limit=1,
                max_rounds=3,
                task_budget=3,
                agent_command=[sys.executable, str(script)],
            )

            queue = self._read_queue(kb)
            target = kb / 'topics' / 'topics-moc.md'
            self.assertEqual(result['schema_version'], 'wikify.maintenance-loop.v1')
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['stop_reason'], 'no_tasks')
            self.assertEqual(result['summary']['round_count'], 2)
            self.assertEqual(result['summary']['selected_count'], 1)
            self.assertEqual(result['summary']['completed_count'], 1)
            self.assertEqual(result['rounds'][0]['status'], 'completed')
            self.assertEqual(result['rounds'][1]['status'], 'maintenance_completed_no_tasks')
            self.assertEqual([task for task in queue['tasks'] if task['action'] == 'queue_link_repair'], [])
            self.assertIn('[[agent-knowledge-loops]]', target.read_text(encoding='utf-8'))

    def test_maintain_loop_stops_when_task_budget_is_exhausted(self):
        from wikify.maintenance.maintain_loop import run_maintenance_loop

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)
            script = self._write_link_repair_agent(kb)

            result = run_maintenance_loop(
                kb,
                action='queue_link_repair',
                limit=5,
                max_rounds=3,
                task_budget=1,
                agent_command=[sys.executable, str(script)],
            )

            self.assertEqual(result['status'], 'task_budget_exhausted')
            self.assertEqual(result['stop_reason'], 'task_budget_exhausted')
            self.assertEqual(result['summary']['round_count'], 1)
            self.assertEqual(result['summary']['selected_count'], 1)
            self.assertEqual(result['summary']['completed_count'], 1)
            self.assertTrue(result['summary']['stopped'])

    def test_maintain_loop_dry_run_previews_one_round_only(self):
        from wikify.maintenance.maintain_loop import run_maintenance_loop

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)

            result = run_maintenance_loop(
                kb,
                action='queue_link_repair',
                max_rounds=5,
                task_budget=5,
                dry_run=True,
            )

            self.assertEqual(result['status'], 'dry_run')
            self.assertEqual(result['stop_reason'], 'dry_run_preview')
            self.assertEqual(result['summary']['round_count'], 1)
            self.assertEqual(result['summary']['selected_count'], 1)
            self.assertEqual(result['rounds'][0]['status'], 'dry_run')
            self.assertFalse((kb / 'sorted' / 'graph-agent-tasks.json').exists())

    def test_maintain_loop_validates_positive_bounds(self):
        from wikify.maintenance.maintain_loop import MaintenanceLoopError, run_maintenance_loop

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)

            cases = [
                {'max_rounds': 0},
                {'task_budget': 0},
                {'limit': 0},
            ]

            for kwargs in cases:
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(MaintenanceLoopError) as raised:
                        run_maintenance_loop(kb, **kwargs)

                    self.assertEqual(raised.exception.code, 'maintenance_loop_invalid_bounds')
                    self.assertIn('field', raised.exception.details)


if __name__ == '__main__':
    unittest.main()
