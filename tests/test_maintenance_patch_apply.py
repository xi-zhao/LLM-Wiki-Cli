import json
import tempfile
import unittest
from pathlib import Path


class MaintenancePatchApplyTests(unittest.TestCase):
    def _write_proposal(self, kb: Path) -> Path:
        proposal = {
            'schema_version': 'wikify.patch-proposal.v1',
            'task_id': 'agent-task-1',
            'source_finding_id': 'broken-link:topics/a.md:7:Missing',
            'action': 'queue_link_repair',
            'target': 'topics/a.md',
            'write_scope': ['topics/a.md'],
            'planned_edits': [
                {
                    'operation': 'propose_content_patch',
                    'path': 'topics/a.md',
                    'action': 'queue_link_repair',
                    'instructions': ['repair link'],
                    'evidence': {},
                    'status': 'planned',
                }
            ],
            'acceptance_checks': ['link resolves'],
            'risk': 'medium',
            'preflight': {'write_scope_valid': True},
        }
        path = kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(proposal), encoding='utf-8')
        return path

    def _write_bundle(self, kb: Path, operations: list[dict] | None = None) -> Path:
        bundle = {
            'schema_version': 'wikify.patch-bundle.v1',
            'proposal_task_id': 'agent-task-1',
            'proposal_path': 'sorted/graph-patch-proposals/agent-task-1.json',
            'operations': operations or [
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

    def test_preflight_patch_bundle_validates_without_writing(self):
        from wikify.maintenance.patch_apply import preflight_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            proposal_path = self._write_proposal(kb)
            bundle_path = self._write_bundle(kb)

            result = preflight_patch_bundle(kb, proposal_path, bundle_path)

            self.assertEqual(result['schema_version'], 'wikify.patch-application-preflight.v1')
            self.assertTrue(result['ready'])
            self.assertFalse(result['writes_content'])
            self.assertEqual(result['summary']['operation_count'], 1)
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
            self.assertFalse((kb / 'sorted' / 'graph-patch-applications').exists())

    def test_apply_patch_bundle_replaces_text_and_writes_audit_record(self):
        from wikify.maintenance.patch_apply import apply_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            proposal_path = self._write_proposal(kb)
            bundle_path = self._write_bundle(kb)

            result = apply_patch_bundle(kb, proposal_path, bundle_path)

            self.assertEqual(result['schema_version'], 'wikify.patch-application.v1')
            self.assertEqual(result['task_id'], 'agent-task-1')
            self.assertEqual(result['status'], 'applied')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            application_path = Path(result['artifacts']['application'])
            self.assertTrue(application_path.exists())
            record = json.loads(application_path.read_text(encoding='utf-8'))
            self.assertEqual(record['schema_version'], 'wikify.patch-application.v1')
            self.assertEqual(record['operations'][0]['path'], 'topics/a.md')
            self.assertIn('before_hash', record['operations'][0])
            self.assertIn('after_hash', record['operations'][0])
            self.assertEqual(record['rollback']['status'], 'available')

    def test_apply_patch_bundle_rejects_out_of_scope_operation(self):
        from wikify.maintenance.patch_apply import PatchApplyError, apply_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')
            (kb / 'topics' / 'other.md').write_text('See [[Missing]].\n', encoding='utf-8')
            proposal_path = self._write_proposal(kb)
            bundle_path = self._write_bundle(
                kb,
                operations=[
                    {
                        'operation': 'replace_text',
                        'path': 'topics/other.md',
                        'find': '[[Missing]]',
                        'replace': '[[Existing]]',
                    }
                ],
            )

            with self.assertRaises(PatchApplyError) as raised:
                apply_patch_bundle(kb, proposal_path, bundle_path)

            self.assertEqual(raised.exception.code, 'patch_operation_out_of_scope')

    def test_apply_patch_bundle_rejects_ambiguous_source_text(self):
        from wikify.maintenance.patch_apply import PatchApplyError, apply_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('[[Missing]] and [[Missing]].\n', encoding='utf-8')
            proposal_path = self._write_proposal(kb)
            bundle_path = self._write_bundle(kb)

            with self.assertRaises(PatchApplyError) as raised:
                apply_patch_bundle(kb, proposal_path, bundle_path)

            self.assertEqual(raised.exception.code, 'patch_preflight_failed')
            self.assertEqual(raised.exception.details['occurrences'], 2)

    def test_apply_patch_bundle_rejects_multiple_operations_for_same_path(self):
        from wikify.maintenance.patch_apply import PatchApplyError, apply_patch_bundle

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('One [[Missing]] and one [[Other]].\n', encoding='utf-8')
            proposal_path = self._write_proposal(kb)
            bundle_path = self._write_bundle(
                kb,
                operations=[
                    {
                        'operation': 'replace_text',
                        'path': 'topics/a.md',
                        'find': '[[Missing]]',
                        'replace': '[[Existing]]',
                    },
                    {
                        'operation': 'replace_text',
                        'path': 'topics/a.md',
                        'find': '[[Other]]',
                        'replace': '[[Elsewhere]]',
                    },
                ],
            )

            with self.assertRaises(PatchApplyError) as raised:
                apply_patch_bundle(kb, proposal_path, bundle_path)

            self.assertEqual(raised.exception.code, 'patch_operation_conflict')
            self.assertEqual(target.read_text(encoding='utf-8'), 'One [[Missing]] and one [[Other]].\n')

    def test_rollback_application_restores_previous_text(self):
        from wikify.maintenance.patch_apply import apply_patch_bundle, rollback_application

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            proposal_path = self._write_proposal(kb)
            bundle_path = self._write_bundle(kb)
            application = apply_patch_bundle(kb, proposal_path, bundle_path)

            result = rollback_application(kb, application['artifacts']['application'])

            self.assertEqual(result['schema_version'], 'wikify.patch-rollback.v1')
            self.assertEqual(result['status'], 'rolled_back')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
            record = json.loads(Path(application['artifacts']['application']).read_text(encoding='utf-8'))
            self.assertEqual(record['status'], 'rolled_back')
            self.assertEqual(record['rollback']['status'], 'completed')

    def test_rollback_application_rejects_drifted_content(self):
        from wikify.maintenance.patch_apply import PatchRollbackError, apply_patch_bundle, rollback_application

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            proposal_path = self._write_proposal(kb)
            bundle_path = self._write_bundle(kb)
            application = apply_patch_bundle(kb, proposal_path, bundle_path)
            target.write_text('Drifted [[Existing]].\n', encoding='utf-8')

            with self.assertRaises(PatchRollbackError) as raised:
                rollback_application(kb, application['artifacts']['application'])

            self.assertEqual(raised.exception.code, 'patch_rollback_hash_mismatch')
            self.assertEqual(target.read_text(encoding='utf-8'), 'Drifted [[Existing]].\n')


if __name__ == '__main__':
    unittest.main()
