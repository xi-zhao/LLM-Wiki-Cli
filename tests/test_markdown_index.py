import unittest
from pathlib import Path


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

    def test_scan_objects_ignores_templates(self):
        from wikify.markdown_index import scan_objects

        base = Path(__file__).resolve().parents[1]

        objects = scan_objects(base, scope='topics')

        self.assertNotIn('topics/_template.md', {obj.relative_path for obj in objects})


if __name__ == '__main__':
    unittest.main()
