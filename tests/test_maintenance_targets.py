import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceTargetsTests(unittest.TestCase):
    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _write_generated_page_fixture(self, root: Path, *, include_views: bool = True):
        source_refs = [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}]
        page_object = {
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
        }
        self._write_json(root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_alpha.json', page_object)
        (root / 'wiki' / 'pages').mkdir(parents=True, exist_ok=True)
        (root / 'wiki' / 'pages' / 'page_alpha.md').write_text(
            '---\n'
            'schema_version: wikify.wiki-page.v1\n'
            'id: page_alpha\n'
            'type: wiki_page\n'
            'body_path: wiki/pages/page_alpha.md\n'
            'source_refs: [{"source_id": "src_notes", "item_id": "item_alpha", "confidence": 0.9}]\n'
            'review_status: generated\n'
            '---\n'
            '# Alpha\n',
            encoding='utf-8',
        )
        if include_views:
            self._write_json(
                root / '.wikify' / 'views' / 'view-manifest.json',
                {
                    'schema_version': 'wikify.views-manifest.v1',
                    'generated_at': '2026-04-30T00:00:00Z',
                    'files': {
                        'views/pages.md': {
                            'sha256': 'abc',
                            'kind': 'markdown',
                            'generated_at': '2026-04-30T00:00:00Z',
                        }
                    },
                },
            )
        self._write_json(
            root / 'artifacts' / 'agent' / 'page-index.json',
            {
                'schema_version': 'wikify.page-index.v1',
                'pages': [{'id': 'page_alpha', 'body_path': 'wiki/pages/page_alpha.md'}],
            },
        )
        return source_refs

    def test_load_targets_indexes_generated_wiki_page_by_object_id_and_body_path(self):
        from wikify.maintenance.targets import (
            MAINTENANCE_TARGETS_SCHEMA_VERSION,
            load_maintenance_targets,
            resolve_target,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_refs = self._write_generated_page_fixture(root)

            targets = load_maintenance_targets(root)

            self.assertEqual(targets['schema_version'], MAINTENANCE_TARGETS_SCHEMA_VERSION)
            by_id = resolve_target(targets, 'page_alpha')
            by_path = resolve_target(targets, 'wiki/pages/page_alpha.md')
            for target in [by_id, by_path]:
                self.assertEqual(target['target_kind'], 'wiki_page')
                self.assertEqual(target['target_family'], 'personal_wiki_page')
                self.assertEqual(target['object_id'], 'page_alpha')
                self.assertEqual(target['object_type'], 'wiki_page')
                self.assertEqual(target['body_path'], 'wiki/pages/page_alpha.md')
                self.assertEqual(target['object_path'], 'artifacts/objects/wiki_pages/page_alpha.json')
                self.assertEqual(target['source_refs'], source_refs)
                self.assertEqual(target['review_status'], 'generated')
                self.assertEqual(target['write_scope'], ['wiki/pages/page_alpha.md'])

    def test_load_targets_warns_when_optional_views_are_missing(self):
        from wikify.maintenance.targets import load_maintenance_targets, resolve_target

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_generated_page_fixture(root, include_views=False)

            targets = load_maintenance_targets(root)

            self.assertIn('views_missing', {warning['code'] for warning in targets['warnings']})
            target = resolve_target(targets, 'page_alpha')
            self.assertEqual(target['object_id'], 'page_alpha')
            self.assertEqual(target['review_status'], 'generated')

    def test_load_targets_degrades_for_legacy_markdown_workspace(self):
        from wikify.maintenance.targets import load_maintenance_targets, resolve_target

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'topics').mkdir(parents=True, exist_ok=True)
            (root / 'topics' / 'a.md').write_text('# A\n', encoding='utf-8')

            targets = load_maintenance_targets(root)
            target = resolve_target(targets, 'topics/a.md')

            self.assertEqual(target['target_kind'], 'legacy_path')
            self.assertEqual(target['target_family'], 'legacy_markdown')
            self.assertEqual(target['write_scope'], ['topics/a.md'])


if __name__ == '__main__':
    unittest.main()
