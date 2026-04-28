import json
import sys
import tempfile
import unittest
from pathlib import Path


class MaintenanceBatchRunnerTests(unittest.TestCase):
    def _write_queue(self, kb: Path, tasks: list[dict]):
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': len(tasks)},
            'tasks': tasks,
        }
        path = kb / 'sorted' / 'graph-agent-tasks.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(queue), encoding='utf-8')
        return path

    def _task(self, task_id: str, target: str, missing: str, status: str = 'queued'):
        return {
            'id': task_id,
            'source_finding_id': f'broken-link:{target}:1:{missing}',
            'source_step_id': f'step-{task_id}',
            'action': 'queue_link_repair',
            'priority': 'high',
            'target': target,
            'evidence': {'source': target, 'line': 1, 'target': missing},
            'write_scope': [target],
            'agent_instructions': ['repair link'],
            'acceptance_checks': ['link resolves'],
            'requires_user': False,
            'status': status,
        }

    def _write_target(self, kb: Path, relative_path: str, missing: str):
        path = kb / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'See [[{missing}]].\n', encoding='utf-8')
        return path

    def _write_target_text(self, kb: Path, relative_path: str, text: str):
        path = kb / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def _write_agent(self, kb: Path):
        script = kb / 'batch_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'target = request["targets"][0]',
                'missing = target["content"].split("[[", 1)[1].split("]]", 1)[0]',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": request["proposal_path"],',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": target["path"],',
                '            "find": f"[[{missing}]]",',
                '            "replace": f"[[Existing{missing[-1]}]]",',
                '            "rationale": "resolve broken wikilink"',
                '        }',
                '    ]',
                '}',
                'print(json.dumps(bundle))',
            ]),
            encoding='utf-8',
        )
        return script

    def _read_queue(self, kb: Path):
        return json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))

    def test_run_agent_tasks_with_agent_command_completes_selected_tasks(self):
        from wikify.maintenance.batch_runner import run_agent_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_target(kb, 'topics/a.md', 'Missing1')
            self._write_target(kb, 'topics/b.md', 'Missing2')
            self._write_queue(
                kb,
                [
                    self._task('agent-task-1', 'topics/a.md', 'Missing1'),
                    self._task('agent-task-2', 'topics/b.md', 'Missing2'),
                ],
            )
            script = self._write_agent(kb)

            result = run_agent_tasks(
                kb,
                limit=2,
                agent_command=[sys.executable, str(script)],
            )

            queue = self._read_queue(kb)
            self.assertEqual(result['schema_version'], 'wikify.agent-task-batch-run.v1')
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['summary']['selected_count'], 2)
            self.assertEqual(result['summary']['completed_count'], 2)
            self.assertEqual(result['summary']['failed_count'], 0)
            self.assertEqual([item['task_id'] for item in result['items']], ['agent-task-1', 'agent-task-2'])
            self.assertTrue(all(item['ok'] for item in result['items']))
            self.assertEqual((kb / 'topics' / 'a.md').read_text(encoding='utf-8'), 'See [[Existing1]].\n')
            self.assertEqual((kb / 'topics' / 'b.md').read_text(encoding='utf-8'), 'See [[Existing2]].\n')
            self.assertEqual([task['status'] for task in queue['tasks']], ['done', 'done'])

    def test_run_agent_tasks_defaults_to_queued_limit_five(self):
        from wikify.maintenance.batch_runner import run_agent_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            tasks = []
            for index in range(6):
                task_id = f'agent-task-{index + 1}'
                missing = f'Missing{index + 1}'
                target = f'topics/{index + 1}.md'
                self._write_target(kb, target, missing)
                tasks.append(self._task(task_id, target, missing))
            tasks.append(self._task('agent-task-done', 'topics/done.md', 'MissingDone', status='done'))
            self._write_queue(kb, tasks)

            result = run_agent_tasks(kb, dry_run=True)

            self.assertEqual(result['status'], 'dry_run')
            self.assertEqual(result['selection']['status'], 'queued')
            self.assertEqual(result['selection']['limit'], 5)
            self.assertEqual(result['summary']['selected_count'], 5)
            self.assertEqual([item['task_id'] for item in result['items']], [f'agent-task-{index}' for index in range(1, 6)])

    def test_run_agent_tasks_returns_no_tasks_for_empty_selection(self):
        from wikify.maintenance.batch_runner import run_agent_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb, [self._task('agent-task-1', 'topics/a.md', 'Missing1', status='done')])

            result = run_agent_tasks(kb)

            self.assertEqual(result['status'], 'no_tasks')
            self.assertEqual(result['summary']['selected_count'], 0)
            self.assertEqual(result['items'], [])

    def test_run_agent_tasks_dry_run_writes_nothing(self):
        from wikify.maintenance.batch_runner import run_agent_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_target(kb, 'topics/a.md', 'Missing1')
            self._write_queue(kb, [self._task('agent-task-1', 'topics/a.md', 'Missing1')])
            script = self._write_agent(kb)

            result = run_agent_tasks(kb, dry_run=True, agent_command=[sys.executable, str(script)])

            self.assertEqual(result['status'], 'dry_run')
            self.assertEqual(result['summary']['selected_count'], 1)
            self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundles').exists())
            self.assertFalse((kb / 'sorted' / 'graph-agent-task-events.json').exists())
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'queued')
            self.assertEqual((kb / 'topics' / 'a.md').read_text(encoding='utf-8'), 'See [[Missing1]].\n')

    def test_run_agent_tasks_stops_on_first_failure_by_default(self):
        from wikify.maintenance.batch_runner import run_agent_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_target_text(kb, 'topics/a.md', '[[Missing1]] and [[Missing1]].\n')
            self._write_target(kb, 'topics/b.md', 'Missing2')
            self._write_queue(
                kb,
                [
                    self._task('agent-task-1', 'topics/a.md', 'Missing1'),
                    self._task('agent-task-2', 'topics/b.md', 'Missing2'),
                ],
            )
            script = self._write_agent(kb)

            result = run_agent_tasks(kb, agent_command=[sys.executable, str(script)])

            queue = self._read_queue(kb)
            self.assertEqual(result['status'], 'stopped_on_error')
            self.assertEqual(result['summary']['failed_count'], 1)
            self.assertTrue(result['summary']['stopped'])
            self.assertEqual([item['task_id'] for item in result['items']], ['agent-task-1'])
            self.assertFalse(result['items'][0]['ok'])
            self.assertEqual(result['items'][0]['error']['code'], 'patch_preflight_failed')
            self.assertEqual([task['status'] for task in queue['tasks']], ['proposed', 'queued'])
            self.assertEqual((kb / 'topics' / 'b.md').read_text(encoding='utf-8'), 'See [[Missing2]].\n')

    def test_run_agent_tasks_continue_on_error_runs_later_tasks(self):
        from wikify.maintenance.batch_runner import run_agent_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_target_text(kb, 'topics/a.md', '[[Missing1]] and [[Missing1]].\n')
            self._write_target(kb, 'topics/b.md', 'Missing2')
            self._write_queue(
                kb,
                [
                    self._task('agent-task-1', 'topics/a.md', 'Missing1'),
                    self._task('agent-task-2', 'topics/b.md', 'Missing2'),
                ],
            )
            script = self._write_agent(kb)

            result = run_agent_tasks(kb, agent_command=[sys.executable, str(script)], continue_on_error=True)

            queue = self._read_queue(kb)
            self.assertEqual(result['status'], 'completed_with_errors')
            self.assertEqual(result['summary']['failed_count'], 1)
            self.assertEqual(result['summary']['completed_count'], 1)
            self.assertFalse(result['summary']['stopped'])
            self.assertEqual([item['task_id'] for item in result['items']], ['agent-task-1', 'agent-task-2'])
            self.assertFalse(result['items'][0]['ok'])
            self.assertTrue(result['items'][1]['ok'])
            self.assertEqual([task['status'] for task in queue['tasks']], ['proposed', 'done'])
            self.assertEqual((kb / 'topics' / 'b.md').read_text(encoding='utf-8'), 'See [[Existing2]].\n')


if __name__ == '__main__':
    unittest.main()
