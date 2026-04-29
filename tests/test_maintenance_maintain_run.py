import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


class MaintenanceRunTests(unittest.TestCase):
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

    def _write_verifier(self, kb: Path) -> Path:
        script = kb / 'verifier_agent.py'
        verdict = {
            'schema_version': 'wikify.patch-bundle-verdict.v1',
            'accepted': True,
            'summary': 'accepted',
            'findings': [],
        }
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'assert request["schema_version"] == "wikify.patch-bundle-verification-request.v1"',
                f'print(json.dumps({verdict!r}))',
            ]),
            encoding='utf-8',
        )
        return script

    def _read_queue(self, kb: Path) -> dict:
        return json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))

    def test_maintain_run_refreshes_and_runs_bounded_tasks(self):
        from wikify.maintenance.maintain_run import run_maintenance_workflow

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)
            script = self._write_link_repair_agent(kb)

            result = run_maintenance_workflow(
                kb,
                limit=1,
                action='queue_link_repair',
                agent_command=[sys.executable, str(script)],
            )

            queue = self._read_queue(kb)
            target = kb / 'topics' / 'topics-moc.md'
            self.assertEqual(result['schema_version'], 'wikify.maintenance-run.v1')
            self.assertEqual(result['status'], 'completed')
            self.assertFalse(result['dry_run'])
            self.assertEqual(result['maintenance']['summary']['task_count'], 6)
            self.assertEqual(result['batch']['schema_version'], 'wikify.agent-task-batch-run.v1')
            self.assertEqual(result['batch']['summary']['selected_count'], 1)
            self.assertEqual(result['batch']['summary']['completed_count'], 1)
            self.assertEqual(result['summary']['selected_count'], 1)
            self.assertEqual(result['summary']['completed_count'], 1)
            self.assertEqual(result['batch']['items'][0]['task_id'], 'agent-task-1')
            self.assertEqual(queue['tasks'][0]['status'], 'done')
            self.assertIn('[[agent-knowledge-loops]]', target.read_text(encoding='utf-8'))
            self.assertTrue((kb / 'sorted' / 'graph-maintenance-history.json').exists())
            self.assertTrue((kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json').exists())

    def test_maintain_run_forwards_verifier_command(self):
        from wikify.maintenance.maintain_run import run_maintenance_workflow

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)
            agent = self._write_link_repair_agent(kb)
            verifier = self._write_verifier(kb)

            result = run_maintenance_workflow(
                kb,
                limit=1,
                action='queue_link_repair',
                agent_command=[sys.executable, str(agent)],
                verifier_command=[sys.executable, str(verifier)],
            )

            item_result = result['batch']['items'][0]['result']
            self.assertEqual(result['status'], 'completed')
            self.assertIn('bundle_verifier', [step['name'] for step in item_result['steps']])
            self.assertTrue(Path(item_result['artifacts']['verification']).exists())

    def test_maintain_run_defaults_to_balanced_queued_limit_five(self):
        from wikify.maintenance.maintain_run import run_maintenance_workflow

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)

            result = run_maintenance_workflow(kb, dry_run=True)

            self.assertEqual(result['policy'], 'balanced')
            self.assertEqual(result['batch']['selection']['status'], 'queued')
            self.assertEqual(result['batch']['selection']['limit'], 5)
            self.assertEqual(result['batch']['summary']['selected_count'], 5)
            self.assertEqual(result['batch']['status'], 'dry_run')
            self.assertEqual(result['summary']['selected_count'], 5)

    def test_maintain_run_dry_run_uses_fresh_preview_without_task_side_effects(self):
        from wikify.maintenance.maintain_run import run_maintenance_workflow

        stale_queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 0},
            'tasks': [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)
            stale_path = kb / 'sorted' / 'graph-agent-tasks.json'
            stale_path.write_text(json.dumps(stale_queue), encoding='utf-8')

            result = run_maintenance_workflow(kb, dry_run=True, action='queue_link_repair')

            persisted_queue = json.loads(stale_path.read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'dry_run')
            self.assertEqual(result['batch']['summary']['selected_count'], 1)
            self.assertEqual(result['batch']['items'][0]['task_id'], 'agent-task-1')
            self.assertEqual(persisted_queue['summary']['task_count'], 0)
            self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundles').exists())
            self.assertFalse((kb / 'sorted' / 'graph-agent-task-events.json').exists())

    def test_maintain_run_batch_errors_preserve_phase_context(self):
        from wikify.maintenance.maintain_run import MaintenanceRunError, run_maintenance_workflow

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = self._copy_sample_kb(tmpdir)

            with self.assertRaises(MaintenanceRunError) as raised:
                run_maintenance_workflow(kb, task_id='missing-task')

            self.assertEqual(raised.exception.code, 'agent_task_not_found')
            self.assertEqual(raised.exception.details['phase'], 'batch_execution')
            self.assertEqual(raised.exception.details['id'], 'missing-task')


if __name__ == '__main__':
    unittest.main()
