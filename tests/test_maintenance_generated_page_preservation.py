import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceGeneratedPagePreservationTests(unittest.TestCase):
    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _write_generated_page_task(self, root: Path):
        source_refs = [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}]
        page_text = (
            '---\n'
            'body_path: wiki/pages/page_alpha.md\n'
            'id: page_alpha\n'
            'review_status: generated\n'
            'source_refs: [{"source_id": "src_notes", "item_id": "item_alpha", "confidence": 0.9}]\n'
            'type: wiki_page\n'
            '---\n'
            '# Alpha\n\nOriginal body.\n'
        )
        (root / 'wiki' / 'pages').mkdir(parents=True, exist_ok=True)
        (root / 'wiki' / 'pages' / 'page_alpha.md').write_text(page_text, encoding='utf-8')
        self._write_json(
            root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_alpha.json',
            {
                'schema_version': 'wikify.wiki-page.v1',
                'id': 'page_alpha',
                'type': 'wiki_page',
                'title': 'Alpha',
                'summary': 'Alpha summary.',
                'body_path': 'wiki/pages/page_alpha.md',
                'source_refs': source_refs,
                'outbound_links': [],
                'backlinks': [],
                'created_at': '2026-04-30T00:00:00Z',
                'updated_at': '2026-04-30T00:00:00Z',
                'confidence': 0.9,
                'review_status': 'generated',
            },
        )
        self._write_json(
            root / 'sorted' / 'graph-agent-tasks.json',
            {
                'schema_version': 'wikify.graph-agent-tasks.v1',
                'summary': {'task_count': 1},
                'tasks': [
                    {
                        'id': 'agent-task-1',
                        'source_finding_id': 'generated-drift',
                        'source_step_id': 'step-1',
                        'action': 'queue_generated_page_repair',
                        'priority': 'high',
                        'target': 'wiki/pages/page_alpha.md',
                        'evidence': {},
                        'write_scope': ['wiki/pages/page_alpha.md'],
                        'object_id': 'page_alpha',
                        'body_path': 'wiki/pages/page_alpha.md',
                        'source_refs': source_refs,
                        'review_status': 'generated',
                        'agent_instructions': ['repair generated page'],
                        'acceptance_checks': ['source refs preserved'],
                        'requires_user': False,
                        'status': 'queued',
                    }
                ],
            },
        )

    def _bundle(self, *, find: str, replace: str) -> dict:
        return {
            'schema_version': 'wikify.patch-bundle.v1',
            'proposal_task_id': 'agent-task-1',
            'proposal_path': 'sorted/graph-patch-proposals/agent-task-1.json',
            'operations': [
                {
                    'operation': 'replace_text',
                    'path': 'wiki/pages/page_alpha.md',
                    'find': find,
                    'replace': replace,
                    'rationale': 'test patch',
                }
            ],
        }

    def test_generated_page_proposal_and_request_include_preservation_context(self):
        from wikify.maintenance.bundle_request import build_bundle_request
        from wikify.maintenance.preservation import PRESERVATION_SCHEMA_VERSION
        from wikify.maintenance.proposal import build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_generated_page_task(root)

            proposal = build_patch_proposal(root, 'agent-task-1')
            request = build_bundle_request(root, 'agent-task-1')

            self.assertEqual(proposal['preservation']['schema_version'], PRESERVATION_SCHEMA_VERSION)
            self.assertTrue(proposal['preservation']['required'])
            self.assertEqual(proposal['preservation']['pages'][0]['object_id'], 'page_alpha')
            self.assertTrue(request['safety']['generated_page_preservation']['required'])
            instructions = ' '.join(request['agent_instructions'])
            self.assertIn('source_refs', instructions)
            self.assertIn('review_status', instructions)

    def test_preservation_rejects_source_refs_or_review_status_changes(self):
        from wikify.maintenance.preservation import (
            GeneratedPagePreservationError,
            build_preservation_context,
            validate_patch_bundle_preservation,
        )
        from wikify.maintenance.proposal import build_patch_proposal

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_generated_page_task(root)
            proposal = build_patch_proposal(root, 'agent-task-1')

            context = build_preservation_context(root, ['wiki/pages/page_alpha.md'])
            self.assertEqual(context['schema_version'], 'wikify.generated-page-preservation.v1')
            validate_patch_bundle_preservation(
                root,
                proposal,
                self._bundle(find='Original body.', replace='Updated body.'),
            )

            with self.assertRaises(GeneratedPagePreservationError) as raised:
                validate_patch_bundle_preservation(
                    root,
                    proposal,
                    self._bundle(find='review_status: generated', replace='review_status: approved'),
                )
            self.assertEqual(raised.exception.code, 'generated_page_preservation_failed')

            with self.assertRaises(GeneratedPagePreservationError) as raised:
                validate_patch_bundle_preservation(
                    root,
                    proposal,
                    self._bundle(
                        find='source_refs: [{"source_id": "src_notes", "item_id": "item_alpha", "confidence": 0.9}]\n',
                        replace='',
                    ),
                )
            self.assertEqual(raised.exception.code, 'generated_page_preservation_failed')


if __name__ == '__main__':
    unittest.main()
