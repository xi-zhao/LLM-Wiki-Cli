import json
import tempfile
import unittest
from pathlib import Path


class ObjectValidationTests(unittest.TestCase):
    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def _valid_page(self, **overrides) -> dict:
        page = {
            'schema_version': 'wikify.wiki-page.v1',
            'id': 'page_intro',
            'type': 'wiki_page',
            'title': 'Intro',
            'summary': 'Intro summary',
            'body_path': 'topics/intro.md',
            'source_refs': [],
            'outbound_links': [],
            'backlinks': [],
            'created_at': '2026-04-29T00:00:00Z',
            'updated_at': '2026-04-29T00:00:00Z',
            'confidence': 0.8,
            'review_status': 'generated',
        }
        page.update(overrides)
        return page

    def _record_codes(self, result: dict) -> list[str]:
        return [record['code'] for record in result['records']]

    def test_valid_json_object_artifact_passes(self):
        from wikify.object_validation import validate_workspace_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_json(root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_intro.json', self._valid_page())

            result = validate_workspace_objects(root)

        self.assertEqual(result['schema_version'], 'wikify.object-validation.v1')
        self.assertEqual(result['summary']['error_count'], 0)
        self.assertEqual(result['summary']['warning_count'], 0)
        self.assertEqual(result['summary']['object_count'], 1)

    def test_valid_markdown_object_front_matter_passes(self):
        from wikify.object_validation import validate_workspace_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topics = root / 'topics'
            topics.mkdir()
            (topics / 'intro.md').write_text(
                '\n'.join([
                    '---',
                    'schema_version: wikify.wiki-page.v1',
                    'id: page_intro',
                    'type: wiki_page',
                    'title: Intro',
                    'summary: Intro summary',
                    'body_path: topics/intro.md',
                    'source_refs: []',
                    'outbound_links: []',
                    'backlinks: []',
                    'created_at: 2026-04-29T00:00:00Z',
                    'updated_at: 2026-04-29T00:00:00Z',
                    'confidence: 0.8',
                    'review_status: generated',
                    '---',
                    '# Intro',
                    '',
                ]),
                encoding='utf-8',
            )

            result = validate_workspace_objects(root)

        self.assertEqual(result['summary']['error_count'], 0)
        self.assertEqual(result['summary']['warning_count'], 0)
        self.assertEqual(result['summary']['object_count'], 1)

    def test_legacy_markdown_without_front_matter_warns_in_default_mode(self):
        from wikify.object_validation import validate_workspace_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topics = root / 'topics'
            topics.mkdir()
            (topics / 'legacy.md').write_text('# Legacy\n', encoding='utf-8')

            result = validate_workspace_objects(root)

        self.assertEqual(result['summary']['error_count'], 0)
        self.assertGreater(result['summary']['warning_count'], 0)
        self.assertTrue(all(record['severity'] == 'warning' for record in result['records']))

    def test_strict_declared_page_missing_required_field_fails(self):
        from wikify.object_validation import validate_workspace_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topics = root / 'topics'
            topics.mkdir()
            (topics / 'intro.md').write_text(
                '\n'.join([
                    '---',
                    'schema_version: wikify.wiki-page.v1',
                    'id: page_intro',
                    'type: wiki_page',
                    'title: Intro',
                    'summary: Intro summary',
                    'body_path: topics/intro.md',
                    'outbound_links: []',
                    'backlinks: []',
                    'created_at: 2026-04-29T00:00:00Z',
                    'updated_at: 2026-04-29T00:00:00Z',
                    'confidence: 0.8',
                    'review_status: generated',
                    '---',
                    '# Intro',
                    '',
                ]),
                encoding='utf-8',
            )

            result = validate_workspace_objects(root, strict=True)

        record = result['records'][0]
        self.assertEqual(record['code'], 'object_required_field_missing')
        self.assertEqual(record['field'], 'source_refs')
        self.assertEqual(record['severity'], 'error')

    def test_duplicate_ids_unresolved_links_and_invalid_schema_are_errors(self):
        from wikify.object_validation import validate_workspace_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_json(root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_intro.json', self._valid_page(outbound_links=['page_missing']))
            self._write_json(root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_intro_duplicate.json', self._valid_page(title='Duplicate'))
            self._write_json(
                root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_bad_schema.json',
                self._valid_page(id='page_bad_schema', confidence=1.5, review_status='unknown', type='topics'),
            )

            result = validate_workspace_objects(root, strict=True)

        codes = self._record_codes(result)
        self.assertIn('object_duplicate_id', codes)
        self.assertIn('object_link_unresolved', codes)
        self.assertIn('object_schema_invalid', codes)

    def test_unresolved_source_and_item_refs_are_errors_when_indexes_exist(self):
        from wikify.object_validation import validate_workspace_objects
        from wikify.sync import source_items_path
        from wikify.workspace import add_source, initialize_workspace

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_workspace(root)
            source = add_source(root, 'https://example.com/source', 'url')['source']
            self._write_json(
                source_items_path(root),
                {
                    'schema_version': 'wikify.source-items.v1',
                    'workspace_id': 'wk_test',
                    'generated_at': '2026-04-29T00:00:00Z',
                    'summary': {'item_count': 0, 'item_status_counts': {}},
                    'items': {},
                },
            )
            self._write_json(
                root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_source_missing.json',
                self._valid_page(id='page_source_missing', source_refs=[{'source_id': 'src_missing'}]),
            )
            self._write_json(
                root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_item_missing.json',
                self._valid_page(id='page_item_missing', source_refs=[{'source_id': source['source_id'], 'item_id': 'item_missing'}]),
            )

            result = validate_workspace_objects(root, strict=True)

        source_ref_records = [record for record in result['records'] if record['code'] == 'object_source_ref_unresolved']
        self.assertEqual(len(source_ref_records), 2)

    def test_invalid_front_matter_returns_structured_record(self):
        from wikify.object_validation import validate_workspace_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topics = root / 'topics'
            topics.mkdir()
            (topics / 'bad.md').write_text('---\ntags:\n  - topic\n---\n# Bad\n', encoding='utf-8')

            result = validate_workspace_objects(root, strict=True)

        self.assertIn('object_frontmatter_invalid', self._record_codes(result))

    def test_write_validation_report_and_record_fields(self):
        from wikify.object_validation import validate_workspace_objects, validation_report_path, write_validation_report

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_json(root / 'artifacts' / 'objects' / 'wiki_pages' / 'page_intro.json', self._valid_page(outbound_links=['page_missing']))

            result = validate_workspace_objects(root, strict=True)
            report = write_validation_report(root, result)

            self.assertEqual(report, validation_report_path(root))
            self.assertTrue((root / 'artifacts' / 'objects' / 'validation.json').is_file())
            for record in result['records']:
                self.assertEqual(
                    set(record),
                    {'code', 'message', 'path', 'object_id', 'field', 'severity', 'details'},
                )


if __name__ == '__main__':
    unittest.main()
