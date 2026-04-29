import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceE2ETests(unittest.TestCase):
    def _read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding='utf-8'))

    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def test_source_to_agent_context_to_maintenance_task_flow(self):
        from wikify.agent import run_agent_context, run_agent_export
        from wikify.maintenance.patch_apply import PatchApplyError, preflight_patch_bundle
        from wikify.maintenance.proposal import build_patch_proposal, write_patch_proposal
        from wikify.maintenance.runner import run_maintenance
        from wikify.sync import sync_workspace
        from wikify.views import run_view_generation
        from wikify.wikiize import run_wikiization
        from wikify.workspace import add_source, initialize_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_workspace(root)
            source_path = root / 'sources' / 'source.md'
            source_path.write_text(
                '# Source Title\n\n'
                'Agent Context should remain durable and source-backed.\n\n'
                'Maintenance should catch [[Missing Target]] from generated pages.\n',
                encoding='utf-8',
            )
            add_source(root, str(source_path), 'file')
            sync_workspace(root)
            wikiize_result = run_wikiization(root)
            run_view_generation(root, include_html=False)
            run_agent_export(root)
            context_pack = run_agent_context(root, 'Agent Context', max_chars=2000, max_pages=2)
            maintenance = run_maintenance(root, policy='balanced', dry_run=False)

            self.assertEqual(wikiize_result['summary']['completed_count'], 1)
            self.assertEqual(context_pack['status'], 'completed')
            self.assertTrue((root / 'llms.txt').exists())
            self.assertTrue((root / 'artifacts' / 'agent' / 'page-index.json').exists())
            self.assertTrue((root / 'views' / 'index.md').exists())
            self.assertTrue((root / 'sorted' / 'graph-findings.json').exists())
            self.assertTrue((root / 'sorted' / 'graph-agent-tasks.json').exists())

            task_queue = self._read_json(root / 'sorted' / 'graph-agent-tasks.json')
            self.assertEqual(task_queue['schema_version'], 'wikify.graph-agent-tasks.v1')
            self.assertGreaterEqual(task_queue['summary']['task_count'], 1)
            metadata_task = next(
                task
                for task in task_queue['tasks']
                if any(task.get(key) for key in ('object_id', 'body_path', 'view_path', 'agent_artifact_path'))
            )
            for key in [
                'id',
                'source_finding_id',
                'action',
                'target',
                'evidence',
                'write_scope',
                'agent_instructions',
                'acceptance_checks',
                'requires_user',
                'status',
            ]:
                self.assertIn(key, metadata_task)
            self.assertEqual(metadata_task['body_path'], metadata_task['target'])
            self.assertEqual(metadata_task['review_status'], 'generated')
            self.assertIn('object_id', metadata_task)
            self.assertEqual(maintenance['targets']['schema_version'], 'wikify.maintenance-targets.v1')

            proposal = build_patch_proposal(root, metadata_task['id'])
            proposal_path = write_patch_proposal(root, proposal)
            bundle = {
                'schema_version': 'wikify.patch-bundle.v1',
                'proposal_task_id': metadata_task['id'],
                'proposal_path': f'sorted/graph-patch-proposals/{metadata_task["id"]}.json',
                'operations': [
                    {
                        'operation': 'replace_text',
                        'path': metadata_task['body_path'],
                        'find': 'review_status: generated',
                        'replace': 'review_status: approved',
                        'rationale': 'unsafe preservation test',
                    }
                ],
            }
            bundle_path = root / 'sorted' / 'graph-patch-bundles' / f'{metadata_task["id"]}.json'
            self._write_json(bundle_path, bundle)

            with self.assertRaises(PatchApplyError) as raised:
                preflight_patch_bundle(root, proposal_path, bundle_path)

            self.assertEqual(raised.exception.code, 'generated_page_preservation_failed')


if __name__ == '__main__':
    unittest.main()
