import json
import sys
import tempfile
import unittest
from pathlib import Path


class MaintenanceBundleVerifierTests(unittest.TestCase):
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

    def _write_proposal_and_bundle(self, kb: Path):
        from wikify.maintenance.bundle_request import build_bundle_request
        from wikify.maintenance.proposal import write_patch_proposal

        self._write_queue(kb)
        (kb / 'topics').mkdir()
        target = kb / 'topics' / 'a.md'
        target.write_text('See [[Missing]].\n', encoding='utf-8')
        request = build_bundle_request(kb, 'agent-task-1')
        proposal_path = write_patch_proposal(kb, request['proposal'])
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
        bundle_path = kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
        bundle_path.parent.mkdir(parents=True)
        bundle_path.write_text(json.dumps(bundle), encoding='utf-8')
        return proposal_path, bundle_path, target

    def _write_verifier(self, kb: Path, *, accepted=True, body: str | None = None) -> Path:
        script = kb / ('accept_verifier.py' if accepted else 'reject_verifier.py')
        verdict = {
            'schema_version': 'wikify.patch-bundle-verdict.v1',
            'accepted': accepted,
            'summary': 'looks safe' if accepted else 'replacement does not satisfy policy',
            'findings': [] if accepted else [{'severity': 'high', 'message': 'rejecting for test'}],
        }
        script.write_text(
            body
            or '\n'.join([
                'import json',
                'import os',
                'import sys',
                'request = json.load(sys.stdin)',
                'assert request["schema_version"] == "wikify.patch-bundle-verification-request.v1"',
                'assert request["preflight"]["ready"] is True',
                'assert os.environ["WIKIFY_PATCH_PROPOSAL"] == request["proposal_path"]',
                'assert os.environ["WIKIFY_PATCH_BUNDLE"] == request["bundle_path"]',
                f'print(json.dumps({verdict!r}))',
            ]),
            encoding='utf-8',
        )
        return script

    def test_verify_patch_bundle_accepts_and_writes_artifact(self):
        from wikify.maintenance.bundle_verifier import verify_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            proposal_path, bundle_path, target = self._write_proposal_and_bundle(kb)
            script = self._write_verifier(kb, accepted=True)

            result = verify_patch_bundle(kb, proposal_path, bundle_path, [sys.executable, str(script)])

            verification_path = Path(result['artifacts']['verification'])
            self.assertEqual(result['schema_version'], 'wikify.patch-bundle-verification.v1')
            self.assertEqual(result['status'], 'accepted')
            self.assertTrue(result['verdict']['accepted'])
            self.assertEqual(result['preflight']['summary']['operation_count'], 1)
            self.assertTrue(verification_path.exists())
            self.assertEqual(json.loads(verification_path.read_text(encoding='utf-8'))['status'], 'accepted')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')

    def test_verify_patch_bundle_rejection_is_structured_and_audited(self):
        from wikify.maintenance.bundle_verifier import BundleVerifierError, verify_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            proposal_path, bundle_path, target = self._write_proposal_and_bundle(kb)
            script = self._write_verifier(kb, accepted=False)

            with self.assertRaises(BundleVerifierError) as raised:
                verify_patch_bundle(kb, proposal_path, bundle_path, [sys.executable, str(script)])

            verification_path = Path(raised.exception.details['verification_path'])
            self.assertEqual(raised.exception.code, 'patch_bundle_verification_rejected')
            self.assertTrue(verification_path.exists())
            self.assertEqual(json.loads(verification_path.read_text(encoding='utf-8'))['status'], 'rejected')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')

    def test_verify_patch_bundle_invalid_output_is_structured(self):
        from wikify.maintenance.bundle_verifier import BundleVerifierError, verify_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            proposal_path, bundle_path, _target = self._write_proposal_and_bundle(kb)
            script = self._write_verifier(kb, body='print("not json")\n')

            with self.assertRaises(BundleVerifierError) as raised:
                verify_patch_bundle(kb, proposal_path, bundle_path, [sys.executable, str(script)])

            self.assertEqual(raised.exception.code, 'bundle_verifier_invalid_output')

    def test_verify_patch_bundle_dry_run_does_not_execute_or_write(self):
        from wikify.maintenance.bundle_verifier import verify_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            proposal_path, bundle_path, _target = self._write_proposal_and_bundle(kb)
            sentinel = kb / 'sentinel.txt'
            script = kb / 'sentinel_verifier.py'
            script.write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("ran")\n', encoding='utf-8')

            result = verify_patch_bundle(kb, proposal_path, bundle_path, [sys.executable, str(script)], dry_run=True)

            self.assertEqual(result['status'], 'dry_run')
            self.assertFalse(result['executed'])
            self.assertFalse(sentinel.exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-verifications').exists())


if __name__ == '__main__':
    unittest.main()
