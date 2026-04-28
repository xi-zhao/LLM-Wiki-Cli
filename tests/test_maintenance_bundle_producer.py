import json
import sys
import tempfile
import unittest
from pathlib import Path


class MaintenanceBundleProducerTests(unittest.TestCase):
    def _write_queue(self, kb: Path):
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
                    'status': 'queued',
                }
            ],
        }
        path = kb / 'sorted' / 'graph-agent-tasks.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(queue), encoding='utf-8')

    def _write_request_fixture(self, kb: Path) -> Path:
        from wikify.maintenance.bundle_request import build_bundle_request, write_bundle_request
        from wikify.maintenance.proposal import write_patch_proposal

        self._write_queue(kb)
        (kb / 'topics').mkdir()
        (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')
        request = build_bundle_request(kb, 'agent-task-1')
        write_patch_proposal(kb, request['proposal'])
        return write_bundle_request(kb, request)

    def _write_stdout_agent(self, directory: Path) -> Path:
        script = directory / 'stdout_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import os',
                'import sys',
                'request = json.load(sys.stdin)',
                'assert os.environ["WIKIFY_PATCH_BUNDLE_REQUEST"] == request["request_path"]',
                'assert os.environ["WIKIFY_PATCH_BUNDLE"] == request["suggested_bundle_path"]',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": "sorted/graph-patch-proposals/agent-task-1.json",',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": "topics/a.md",',
                '            "find": "[[Missing]]",',
                '            "replace": "[[Existing]]",',
                '            "rationale": "resolve broken wikilink"',
                '        }',
                '    ]',
                '}',
                'print(json.dumps(bundle))',
            ]),
            encoding='utf-8',
        )
        return script

    def _write_file_agent(self, directory: Path) -> Path:
        script = directory / 'file_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import os',
                'import sys',
                'request = json.load(sys.stdin)',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": "sorted/graph-patch-proposals/agent-task-1.json",',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": "topics/a.md",',
                '            "find": "[[Missing]]",',
                '            "replace": "[[Existing]]",',
                '            "rationale": "resolve broken wikilink"',
                '        }',
                '    ]',
                '}',
                'target = os.environ["WIKIFY_PATCH_BUNDLE"]',
                'os.makedirs(os.path.dirname(target), exist_ok=True)',
                'with open(target, "w", encoding="utf-8") as handle:',
                '    json.dump(bundle, handle)',
            ]),
            encoding='utf-8',
        )
        return script

    def test_produce_patch_bundle_from_stdout_json(self):
        from wikify.maintenance.bundle_producer import produce_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            request_path = self._write_request_fixture(kb)
            script = self._write_stdout_agent(kb)

            result = produce_patch_bundle(kb, request_path, [sys.executable, str(script)])

            bundle_path = kb.resolve() / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
            self.assertEqual(result['schema_version'], 'wikify.patch-bundle-production.v1')
            self.assertEqual(result['status'], 'bundle_ready')
            self.assertEqual(result['artifacts']['patch_bundle'], str(bundle_path))
            self.assertTrue(bundle_path.exists())
            self.assertEqual(result['preflight']['summary']['operation_count'], 1)
            self.assertEqual((kb / 'topics' / 'a.md').read_text(encoding='utf-8'), 'See [[Missing]].\n')

    def test_produce_patch_bundle_accepts_command_written_bundle(self):
        from wikify.maintenance.bundle_producer import produce_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            request_path = self._write_request_fixture(kb)
            script = self._write_file_agent(kb)

            result = produce_patch_bundle(kb, request_path, [sys.executable, str(script)])

            self.assertEqual(result['status'], 'bundle_ready')
            self.assertEqual(result['output_mode'], 'file')
            self.assertTrue((kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json').exists())

    def test_produce_patch_bundle_dry_run_does_not_execute_command(self):
        from wikify.maintenance.bundle_producer import produce_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            request_path = self._write_request_fixture(kb)
            script = kb / 'sentinel_agent.py'
            sentinel = kb / 'sentinel.txt'
            script.write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("ran")\n', encoding='utf-8')

            result = produce_patch_bundle(kb, request_path, [sys.executable, str(script)], dry_run=True)

            self.assertEqual(result['status'], 'dry_run')
            self.assertFalse(result['executed'])
            self.assertFalse(sentinel.exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundles').exists())

    def test_produce_patch_bundle_command_failure_is_structured(self):
        from wikify.maintenance.bundle_producer import BundleProducerError, produce_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            request_path = self._write_request_fixture(kb)
            script = kb / 'failing_agent.py'
            script.write_text('import sys\nprint("nope", file=sys.stderr)\nsys.exit(7)\n', encoding='utf-8')

            with self.assertRaises(BundleProducerError) as raised:
                produce_patch_bundle(kb, request_path, [sys.executable, str(script)])

            self.assertEqual(raised.exception.code, 'bundle_producer_command_failed')
            self.assertEqual(raised.exception.details['returncode'], 7)


if __name__ == '__main__':
    unittest.main()
