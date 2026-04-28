import hashlib
import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceBundleRequestTests(unittest.TestCase):
    def _write_queue(self, kb: Path, task: dict | None = None):
        task = task or {
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
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 1},
            'tasks': [task],
        }
        path = kb / 'sorted' / 'graph-agent-tasks.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(queue), encoding='utf-8')
        return path

    def test_build_bundle_request_includes_snapshot_and_contract(self):
        from wikify.maintenance.bundle_request import build_bundle_request

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            content = 'See [[Missing]].\n'
            target.write_text(content, encoding='utf-8')

            request = build_bundle_request(kb, 'agent-task-1')

            self.assertEqual(request['schema_version'], 'wikify.patch-bundle-request.v1')
            self.assertEqual(request['task_id'], 'agent-task-1')
            self.assertEqual(
                request['suggested_bundle_path'],
                str(kb.resolve() / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'),
            )
            self.assertEqual(request['allowed_operations'][0]['operation'], 'replace_text')
            self.assertEqual(request['proposal']['write_scope'], ['topics/a.md'])
            self.assertEqual(request['targets'][0]['path'], 'topics/a.md')
            self.assertEqual(request['targets'][0]['sha256'], hashlib.sha256(content.encode('utf-8')).hexdigest())
            self.assertEqual(request['targets'][0]['content'], content)
            self.assertFalse(request['targets'][0]['truncated'])

    def test_write_bundle_request_writes_artifact(self):
        from wikify.maintenance.bundle_request import build_bundle_request, write_bundle_request

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')

            request = build_bundle_request(kb, 'agent-task-1')
            path = write_bundle_request(kb, request)

            self.assertEqual(path, kb.resolve() / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json')
            self.assertTrue(path.exists())
            written = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(written['schema_version'], 'wikify.patch-bundle-request.v1')
            self.assertEqual(written['task_id'], 'agent-task-1')

    def test_build_bundle_request_does_not_write_artifacts(self):
        from wikify.maintenance.bundle_request import build_bundle_request

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')

            build_bundle_request(kb, 'agent-task-1')

            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())

    def test_build_bundle_request_missing_target_raises_structured_error(self):
        from wikify.maintenance.bundle_request import BundleRequestError, build_bundle_request

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            with self.assertRaises(BundleRequestError) as raised:
                build_bundle_request(kb, 'agent-task-1')

            self.assertEqual(raised.exception.code, 'bundle_request_target_not_found')
            self.assertEqual(raised.exception.details['path'], 'topics/a.md')


if __name__ == '__main__':
    unittest.main()
