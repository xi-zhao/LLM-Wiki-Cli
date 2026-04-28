import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceTaskReaderTests(unittest.TestCase):
    def _write_queue(self, kb: Path):
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 3},
            'tasks': [
                {
                    'id': 'agent-task-1',
                    'source_finding_id': 'broken-link:a',
                    'action': 'queue_link_repair',
                    'priority': 'high',
                    'target': 'topics/a.md',
                    'evidence': {'line': 7},
                    'write_scope': ['topics/a.md'],
                    'agent_instructions': ['repair link'],
                    'acceptance_checks': ['link resolves'],
                    'requires_user': False,
                    'status': 'queued',
                },
                {
                    'id': 'agent-task-2',
                    'source_finding_id': 'orphan:b',
                    'action': 'queue_orphan_attachment',
                    'priority': 'normal',
                    'target': 'sources/b.md',
                    'evidence': {},
                    'write_scope': ['sources/b.md'],
                    'agent_instructions': ['attach orphan'],
                    'acceptance_checks': ['has relationship'],
                    'requires_user': False,
                    'status': 'queued',
                },
                {
                    'id': 'agent-task-3',
                    'source_finding_id': 'digest:c',
                    'action': 'queue_digest_refresh',
                    'priority': 'normal',
                    'target': 'topics/c.md',
                    'evidence': {},
                    'write_scope': ['topics/c.md'],
                    'agent_instructions': ['review digest'],
                    'acceptance_checks': ['proposal exists'],
                    'requires_user': False,
                    'status': 'blocked',
                },
            ],
        }
        target = kb / 'sorted' / 'graph-agent-tasks.json'
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(queue), encoding='utf-8')

    def test_load_task_queue_and_select_tasks(self):
        from wikify.maintenance.task_reader import load_task_queue, select_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            queue = load_task_queue(kb)
            selected = select_tasks(queue, status='queued', action='queue_link_repair')

            self.assertEqual(queue['schema_version'], 'wikify.graph-agent-tasks.v1')
            self.assertEqual(selected['schema_version'], 'wikify.agent-task-selection.v1')
            self.assertEqual(selected['source_schema_version'], 'wikify.graph-agent-tasks.v1')
            self.assertEqual(selected['summary']['total_task_count'], 3)
            self.assertEqual(selected['summary']['task_count'], 1)
            self.assertEqual(selected['tasks'][0]['id'], 'agent-task-1')

    def test_select_tasks_supports_id_and_limit(self):
        from wikify.maintenance.task_reader import load_task_queue, select_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            queue = load_task_queue(kb)
            by_id = select_tasks(queue, task_id='agent-task-2')
            limited = select_tasks(queue, status='queued', limit=1)

            self.assertEqual([task['id'] for task in by_id['tasks']], ['agent-task-2'])
            self.assertEqual(len(limited['tasks']), 1)
            self.assertEqual(limited['summary']['task_count'], 1)

    def test_missing_queue_and_missing_id_raise_typed_errors(self):
        from wikify.maintenance.task_reader import (
            TaskNotFound,
            TaskQueueNotFound,
            load_task_queue,
            select_tasks,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            with self.assertRaises(TaskQueueNotFound):
                load_task_queue(kb)

            self._write_queue(kb)
            queue = load_task_queue(kb)
            with self.assertRaises(TaskNotFound):
                select_tasks(queue, task_id='missing-task')
            with self.assertRaises(ValueError):
                select_tasks(queue, limit=-1)


if __name__ == '__main__':
    unittest.main()
