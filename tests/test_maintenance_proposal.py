import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceProposalTests(unittest.TestCase):
    def _write_queue(self, kb: Path, task: dict | None = None):
        task = task or {
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
            'status': 'queued',
        }
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 1},
            'tasks': [task],
        }
        target = kb / 'sorted' / 'graph-agent-tasks.json'
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(queue), encoding='utf-8')

    def test_build_and_write_patch_proposal(self):
        from wikify.maintenance.proposal import build_patch_proposal, write_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            proposal = build_patch_proposal(kb, 'agent-task-1')
            path = write_patch_proposal(kb, proposal)

            self.assertEqual(proposal['schema_version'], 'wikify.patch-proposal.v1')
            self.assertEqual(proposal['task_id'], 'agent-task-1')
            self.assertEqual(proposal['source_finding_id'], 'broken-link:topics/a.md:7:Missing')
            self.assertEqual(proposal['write_scope'], ['topics/a.md'])
            self.assertEqual(proposal['planned_edits'][0]['path'], 'topics/a.md')
            self.assertEqual(proposal['acceptance_checks'], ['link resolves'])
            self.assertEqual(proposal['risk'], 'medium')
            self.assertTrue(proposal['preflight']['write_scope_valid'])
            self.assertEqual(path, kb.resolve() / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json')
            self.assertTrue(path.exists())

    def test_build_patch_proposal_includes_purpose_context_and_rationale(self):
        from wikify.maintenance.proposal import build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'purpose.md').write_text(
                '\n'.join([
                    '# Agent Knowledge Memory',
                    '',
                    'Goal: keep graph maintenance auditable and useful for agent workflows.',
                    'Key question: which repairs improve long-term coherence?',
                ]),
                encoding='utf-8',
            )

            proposal = build_patch_proposal(kb, 'agent-task-1')

            self.assertTrue(proposal['purpose_context']['present'])
            self.assertEqual(proposal['purpose_context']['title'], 'Agent Knowledge Memory')
            self.assertIn('auditable', proposal['purpose_context']['excerpt'])
            self.assertTrue(proposal['rationale']['purpose_aware'])
            self.assertIn('Agent Knowledge Memory', proposal['rationale']['purpose_alignment'])
            self.assertIn('auditable', proposal['rationale']['purpose_alignment'])
            self.assertIn('does not expand write scope', proposal['rationale']['safety'])

    def test_build_patch_proposal_marks_missing_purpose_non_blocking(self):
        from wikify.maintenance.proposal import build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            proposal = build_patch_proposal(kb, 'agent-task-1')

            self.assertFalse(proposal['purpose_context']['present'])
            self.assertFalse(proposal['rationale']['purpose_aware'])
            self.assertIn('non-blocking', proposal['rationale']['purpose_alignment'])
            self.assertIn('does not alter write-scope validation', proposal['rationale']['safety'])

    def test_build_patch_proposal_does_not_write_artifacts(self):
        from wikify.maintenance.proposal import build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            build_patch_proposal(kb, 'agent-task-1')

            self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())

    def test_missing_write_scope_raises_proposal_error(self):
        from wikify.maintenance.proposal import ProposalError, build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            task = {
                'id': 'agent-task-1',
                'source_finding_id': 'orphan:a',
                'action': 'queue_orphan_attachment',
                'priority': 'normal',
                'target': 'topics/a.md',
                'evidence': {'source': 'topics/a.md'},
                'write_scope': [],
                'agent_instructions': ['attach orphan'],
                'acceptance_checks': ['has relationship'],
                'requires_user': False,
                'status': 'queued',
            }
            self._write_queue(kb, task)

            with self.assertRaises(ProposalError) as raised:
                build_patch_proposal(kb, 'agent-task-1')

            self.assertEqual(raised.exception.code, 'proposal_write_scope_missing')

    def test_out_of_scope_candidate_path_raises(self):
        from wikify.maintenance.proposal import OutOfScopeProposal, build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            task = {
                'id': 'agent-task-1',
                'source_finding_id': 'broken-link:a',
                'action': 'queue_link_repair',
                'priority': 'high',
                'target': 'topics/a.md',
                'evidence': {'source': 'topics/other.md'},
                'write_scope': ['topics/a.md'],
                'agent_instructions': ['repair link'],
                'acceptance_checks': ['link resolves'],
                'requires_user': False,
                'status': 'queued',
            }
            self._write_queue(kb, task)

            with self.assertRaises(OutOfScopeProposal) as raised:
                build_patch_proposal(kb, 'agent-task-1')

            self.assertEqual(raised.exception.path, 'topics/other.md')

    def test_out_of_scope_candidate_path_raises_even_when_purpose_exists(self):
        from wikify.maintenance.proposal import OutOfScopeProposal, build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'purpose.md').write_text(
                '# Agent Knowledge Memory\n\nGoal: keep proposed repairs aligned.',
                encoding='utf-8',
            )
            task = {
                'id': 'agent-task-1',
                'source_finding_id': 'broken-link:a',
                'action': 'queue_link_repair',
                'priority': 'high',
                'target': 'topics/a.md',
                'evidence': {'source': 'topics/other.md'},
                'write_scope': ['topics/a.md'],
                'agent_instructions': ['repair link'],
                'acceptance_checks': ['link resolves'],
                'requires_user': False,
                'status': 'queued',
            }
            self._write_queue(kb, task)

            with self.assertRaises(OutOfScopeProposal) as raised:
                build_patch_proposal(kb, 'agent-task-1')

            self.assertEqual(raised.exception.path, 'topics/other.md')


if __name__ == '__main__':
    unittest.main()
