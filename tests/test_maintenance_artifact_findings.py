import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceArtifactFindingsTests(unittest.TestCase):
    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _write_fixture(self, root: Path):
        source_refs = [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}]
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
        (root / 'wiki' / 'pages').mkdir(parents=True, exist_ok=True)
        (root / 'wiki' / 'pages' / 'page_alpha.md').write_text('# Alpha\n', encoding='utf-8')
        self._write_json(
            root / 'artifacts' / 'objects' / 'validation.json',
            {
                'schema_version': 'wikify.object-validation.v1',
                'status': 'warnings',
                'summary': {'object_count': 1, 'record_count': 1, 'error_count': 0, 'warning_count': 1},
                'records': [
                    {
                        'code': 'source_refs_missing_item',
                        'message': 'source ref item is missing',
                        'path': 'wiki/pages/page_alpha.md',
                        'object_id': 'page_alpha',
                        'field': 'source_refs',
                        'severity': 'warning',
                        'details': {},
                    }
                ],
            },
        )
        self._write_json(
            root / '.wikify' / 'queues' / 'wikiization-tasks.json',
            {
                'schema_version': 'wikify.wikiization-tasks.v1',
                'generated_at': '2026-04-30T00:00:00Z',
                'summary': {'task_count': 1, 'by_reason': {'generated_page_drifted': 1}},
                'tasks': [
                    {
                        'id': 'wiki-task-alpha',
                        'reason_code': 'generated_page_drifted',
                        'target_paths': {'body_path': 'wiki/pages/page_alpha.md'},
                        'status': 'queued',
                    }
                ],
            },
        )
        self._write_json(
            root / '.wikify' / 'queues' / 'view-tasks.json',
            {
                'schema_version': 'wikify.view-tasks.v1',
                'generated_at': '2026-04-30T00:00:00Z',
                'summary': {'task_count': 1, 'by_reason': {'generated_view_drifted': 1}},
                'tasks': [
                    {
                        'id': 'view-task-alpha',
                        'target_paths': {'view_path': 'views/sources/src_notes.md'},
                        'reason_code': 'generated_view_drifted',
                        'status': 'queued',
                    }
                ],
            },
        )

    def test_build_findings_adds_validation_wikiization_view_and_agent_export_targets(self):
        from wikify.maintenance.findings import build_findings
        from wikify.maintenance.targets import load_maintenance_targets

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_fixture(root)
            targets = load_maintenance_targets(root)
            graph = {'schema_version': 'wikify.graph.v1', 'analytics': {'node_count': 1, 'edge_count': 1}}

            findings = build_findings(graph, targets=targets)

            by_type = {finding['type']: finding for finding in findings}
            self.assertEqual(by_type['object_validation_record']['recommended_action'], 'queue_object_validation_repair')
            self.assertEqual(by_type['object_validation_record']['object_id'], 'page_alpha')
            self.assertEqual(by_type['generated_page_drift']['recommended_action'], 'queue_generated_page_repair')
            self.assertEqual(by_type['generated_page_drift']['body_path'], 'wiki/pages/page_alpha.md')
            self.assertEqual(by_type['view_task']['recommended_action'], 'queue_view_regeneration')
            self.assertEqual(by_type['view_task']['view_path'], 'views/sources/src_notes.md')
            self.assertEqual(by_type['view_task']['regeneration_command'], 'wikify views')
            agent_missing = next(
                finding
                for finding in findings
                if finding['type'] == 'agent_export_missing'
                and finding.get('agent_artifact_path') == 'artifacts/agent/page-index.json'
            )
            self.assertEqual(agent_missing['recommended_action'], 'queue_agent_export_refresh')
            self.assertEqual(agent_missing['regeneration_command'], 'wikify agent export')


if __name__ == '__main__':
    unittest.main()
