import unittest
from pathlib import Path
import tempfile


class MarkdownIndexTests(unittest.TestCase):
    def test_scan_objects_reads_sample_kb_supported_scopes(self):
        from wikify.markdown_index import scan_objects

        base = Path(__file__).resolve().parents[1] / 'sample-kb'

        objects = scan_objects(base, scope='all')
        object_types = {obj.type for obj in objects}

        self.assertIn('topics', object_types)
        self.assertIn('parsed', object_types)
        self.assertIn('briefs', object_types)
        self.assertIn('sorted', object_types)
        self.assertIn('sources', object_types)

    def test_scan_objects_returns_normalized_object_shape(self):
        from wikify.markdown_index import scan_objects

        base = Path(__file__).resolve().parents[1] / 'sample-kb'

        objects = scan_objects(base, scope='topics')

        self.assertTrue(objects)
        first = objects[0]
        self.assertEqual(first.type, 'topics')
        self.assertTrue(first.path.is_absolute())
        self.assertFalse(first.relative_path.startswith('/'))
        self.assertTrue(first.title)
        self.assertTrue(first.text)
        self.assertIsInstance(first.lines, list)
        self.assertTrue(all(isinstance(line, tuple) and len(line) == 2 for line in first.lines))

    def test_scan_objects_reads_front_matter_metadata(self):
        from wikify.markdown_index import scan_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topic_dir = root / 'topics'
            topic_dir.mkdir()
            (topic_dir / 'agent-loop.md').write_text(
                '\n'.join([
                    '---',
                    'schema_version: wikify.wiki-page.v1',
                    'id: page_agent_loop',
                    'type: wiki_page',
                    'title: Agent Loop',
                    'summary: Agent loop summary',
                    'source_refs: [{"source_id": "src_1"}]',
                    'outbound_links: ["page_other"]',
                    'confidence: 0.8',
                    'review_status: generated',
                    '---',
                    '# Heading Fallback',
                    '',
                ]),
                encoding='utf-8',
            )

            obj = scan_objects(root, scope='topics')[0]

        self.assertEqual(obj.metadata['id'], 'page_agent_loop')
        self.assertEqual(obj.object_id, 'page_agent_loop')
        self.assertEqual(obj.canonical_type, 'wiki_page')
        self.assertEqual(obj.title, 'Agent Loop')

    def test_scan_objects_keeps_heading_title_without_front_matter(self):
        from wikify.markdown_index import scan_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topic_dir = root / 'topics'
            topic_dir.mkdir()
            (topic_dir / 'plain.md').write_text('# Plain Heading\n', encoding='utf-8')

            obj = scan_objects(root, scope='topics')[0]

        self.assertEqual(obj.metadata, {})
        self.assertIsNone(obj.object_id)
        self.assertEqual(obj.canonical_type, 'topic')
        self.assertEqual(obj.title, 'Plain Heading')

    def test_scan_objects_ignores_templates(self):
        from wikify.markdown_index import scan_objects

        base = Path(__file__).resolve().parents[1]

        objects = scan_objects(base, scope='topics')

        self.assertNotIn('topics/_template.md', {obj.relative_path for obj in objects})


if __name__ == '__main__':
    unittest.main()
