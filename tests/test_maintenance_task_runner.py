import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceTaskRunnerTests(unittest.TestCase):
    def _write_queue(self, kb: Path, status: str = 'queued'):
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 1},
            'tasks': [
                {
                    'id': 'agent-task-1',
                    'source_finding_id': 'broken-link:topics/a.md:1:Missing',
                    'source_step_id': 'step-1',
                    'action': 'queue_link_repair',
                    'priority': 'high',
                    'target': 'topics/a.md',
                    'evidence': {'source': 'topics/a.md', 'line': 1, 'target': 'Missing'},
                    'write_scope': ['topics/a.md'],
                    'agent_instructions': ['repair link'],
                    'acceptance_checks': ['link resolves'],
                    'requires_user': False,
                    'status': status,
                }
            ],
        }
        path = kb / 'sorted' / 'graph-agent-tasks.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(queue), encoding='utf-8')
        return path

    def _write_bundle(self, kb: Path):
        bundle = {
            'schema_version': 'wikify.patch-bundle.v1',
            'proposal_task_id': 'agent-task-1',
            'proposal_path': 'sorted/graph-patch-proposals/agent-task-1.json',
            'operations': [
                {
                    'operation': 'replace_text',
                    'path': 'topics/a.md',
                    'find': '[[Missing]]',
                    'replace': '[[Existing]]',
                    'rationale': 'resolve broken wikilink',
                }
            ],
        }
        path = kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(bundle), encoding='utf-8')
        return path

    def _read_queue(self, kb: Path):
        return json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))

    def test_run_agent_task_dry_run_waits_for_bundle_without_writes(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')

            result = run_agent_task(kb, 'agent-task-1', dry_run=True)

            self.assertEqual(result['schema_version'], 'wikify.agent-task-run.v1')
            self.assertTrue(result['dry_run'])
            self.assertEqual(result['status'], 'waiting_for_patch_bundle')
            self.assertIn('generate_patch_bundle', result['next_actions'])
            self.assertEqual(result['artifacts']['patch_bundle_request'], None)
            self.assertEqual(
                result['summary']['bundle_request_path'],
                str(kb.resolve() / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'),
            )
            self.assertEqual(
                result['summary']['suggested_bundle_path'],
                str(kb.resolve() / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'),
            )
            self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())
            self.assertFalse((kb / 'sorted' / 'graph-agent-task-events.json').exists())
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'queued')

    def test_run_agent_task_missing_bundle_writes_proposal_marks_proposed_and_writes_request(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')

            result = run_agent_task(kb, 'agent-task-1')

            proposal_path = kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json'
            request_path = kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'
            expected_request_path = kb.resolve() / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'
            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(result['status'], 'waiting_for_patch_bundle')
            self.assertEqual(result['steps'][0]['name'], 'proposal')
            self.assertEqual(result['steps'][0]['status'], 'written')
            self.assertEqual(result['steps'][1]['name'], 'lifecycle')
            self.assertEqual(result['steps'][1]['status'], 'marked_proposed')
            self.assertEqual(result['steps'][2]['name'], 'bundle_request')
            self.assertEqual(result['steps'][2]['status'], 'written')
            self.assertTrue(proposal_path.exists())
            self.assertTrue(request_path.exists())
            self.assertEqual(result['artifacts']['patch_bundle_request'], str(expected_request_path))
            self.assertEqual(result['summary']['bundle_request_path'], str(expected_request_path))
            self.assertEqual(task['status'], 'proposed')
            self.assertEqual(task['proposal_path'], 'sorted/graph-patch-proposals/agent-task-1.json')
            self.assertEqual(events['events'][0]['action'], 'mark_proposed')

    def test_run_agent_task_bundle_request_failure_keeps_proposed_state(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(kb, 'agent-task-1')

            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(raised.exception.code, 'bundle_request_target_not_found')
            self.assertEqual(raised.exception.details['phase'], 'bundle_request')
            self.assertEqual(raised.exception.details['path'], 'topics/a.md')
            self.assertEqual(task['status'], 'proposed')
            self.assertTrue((kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())

    def test_run_agent_task_with_bundle_applies_patch_and_marks_done(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            self._write_bundle(kb)

            result = run_agent_task(kb, 'agent-task-1')

            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            task = self._read_queue(kb)['tasks'][0]
            application_path = Path(result['artifacts']['application'])
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            self.assertTrue((kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json').exists())
            self.assertTrue(application_path.exists())
            self.assertEqual(task['status'], 'done')
            self.assertEqual([event['action'] for event in events['events']], ['mark_proposed', 'mark_done'])

    def test_run_agent_task_apply_failure_keeps_proposed_state(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('[[Missing]] and [[Missing]].\n', encoding='utf-8')
            self._write_bundle(kb)

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(kb, 'agent-task-1')

            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(raised.exception.code, 'patch_preflight_failed')
            self.assertEqual(raised.exception.details['phase'], 'apply')
            self.assertEqual(task['status'], 'proposed')
            self.assertEqual(target.read_text(encoding='utf-8'), '[[Missing]] and [[Missing]].\n')
            self.assertFalse((kb / 'sorted' / 'graph-patch-applications').exists())


if __name__ == '__main__':
    unittest.main()
