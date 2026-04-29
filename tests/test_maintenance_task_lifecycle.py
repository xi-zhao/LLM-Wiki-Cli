import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceTaskLifecycleTests(unittest.TestCase):
    def _write_queue(self, kb: Path, status: str = 'queued'):
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 1},
            'tasks': [
                {
                    'id': 'agent-task-1',
                    'source_finding_id': 'broken-link:topics/a.md:7:Missing',
                    'source_step_id': 'step-1',
                    'action': 'queue_link_repair',
                    'priority': 'high',
                    'target': 'topics/a.md',
                    'evidence': {'source': 'topics/a.md', 'line': 7, 'target': 'Missing'},
                    'write_scope': ['topics/a.md'],
                    'agent_instructions': ['repair link'],
                    'acceptance_checks': ['link resolves'],
                    'requires_user': False,
                    'status': status,
                },
            ],
        }
        target = kb / 'sorted' / 'graph-agent-tasks.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(queue), encoding='utf-8')

    def _read_queue(self, kb: Path):
        return json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))

    def _read_events(self, kb: Path):
        return json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))

    def test_mark_proposed_persists_status_and_appends_event(self):
        from wikify.maintenance.task_lifecycle import apply_lifecycle_action

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            result = apply_lifecycle_action(
                kb,
                'agent-task-1',
                'mark_proposed',
                note='proposal ready',
                proposal_path='sorted/graph-patch-proposals/agent-task-1.json',
            )

            queue = self._read_queue(kb)
            events = self._read_events(kb)
            task = queue['tasks'][0]
            event = events['events'][0]
            self.assertEqual(result['schema_version'], 'wikify.agent-task-lifecycle.v1')
            self.assertEqual(task['status'], 'proposed')
            self.assertEqual(task['proposal_path'], 'sorted/graph-patch-proposals/agent-task-1.json')
            self.assertEqual(event['id'], 'event-1')
            self.assertEqual(event['from_status'], 'queued')
            self.assertEqual(event['to_status'], 'proposed')
            self.assertEqual(event['action'], 'mark_proposed')
            self.assertEqual(event['note'], 'proposal ready')

    def test_progression_to_done_appends_events(self):
        from wikify.maintenance.task_lifecycle import apply_lifecycle_action

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            apply_lifecycle_action(kb, 'agent-task-1', 'mark_proposed')
            apply_lifecycle_action(kb, 'agent-task-1', 'start')
            result = apply_lifecycle_action(kb, 'agent-task-1', 'mark_done')

            queue = self._read_queue(kb)
            events = self._read_events(kb)
            self.assertEqual(queue['tasks'][0]['status'], 'done')
            self.assertEqual(result['task']['status'], 'done')
            self.assertEqual([event['id'] for event in events['events']], ['event-1', 'event-2', 'event-3'])
            self.assertEqual(events['events'][-1]['from_status'], 'in_progress')
            self.assertEqual(events['events'][-1]['to_status'], 'done')

    def test_retry_restore_and_cancel_transitions(self):
        from wikify.maintenance.task_lifecycle import apply_lifecycle_action

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb, status='failed')
            apply_lifecycle_action(kb, 'agent-task-1', 'retry')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'queued')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['attempts'], 1)

            self._write_queue(kb, status='blocked')
            apply_lifecycle_action(kb, 'agent-task-1', 'restore')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'queued')

            apply_lifecycle_action(kb, 'agent-task-1', 'cancel')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'rejected')

    def test_block_details_are_persisted_and_retry_clears_feedback(self):
        from wikify.maintenance.task_lifecycle import apply_lifecycle_action

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb, status='proposed')
            feedback = {
                'source': 'bundle_verifier',
                'summary': 'rejected',
                'findings': [{'severity': 'high', 'message': 'test rejection'}],
                'verification_path': '/tmp/verification.json',
                'verdict': {'accepted': False, 'summary': 'rejected'},
            }

            apply_lifecycle_action(
                kb,
                'agent-task-1',
                'block',
                note='patch bundle rejected by verifier',
                details=feedback,
            )

            queue = self._read_queue(kb)
            events = self._read_events(kb)
            task = queue['tasks'][0]
            self.assertEqual(task['status'], 'blocked')
            self.assertEqual(task['blocked_feedback'], feedback)
            self.assertEqual(events['events'][0]['action'], 'block')
            self.assertEqual(events['events'][0]['details'], feedback)

            apply_lifecycle_action(kb, 'agent-task-1', 'retry')

            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(task['status'], 'queued')
            self.assertEqual(task['attempts'], 1)
            self.assertNotIn('blocked_feedback', task)

    def test_invalid_transition_raises(self):
        from wikify.maintenance.task_lifecycle import InvalidTaskTransition, apply_lifecycle_action

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb, status='done')

            with self.assertRaises(InvalidTaskTransition) as raised:
                apply_lifecycle_action(kb, 'agent-task-1', 'start')

            self.assertEqual(raised.exception.from_status, 'done')
            self.assertEqual(raised.exception.to_status, 'in_progress')


if __name__ == '__main__':
    unittest.main()
