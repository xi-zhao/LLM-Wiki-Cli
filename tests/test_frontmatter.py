import unittest


class FrontMatterTests(unittest.TestCase):
    def test_split_front_matter_parses_scalars_and_json_flow_values(self):
        from wikify.frontmatter import split_front_matter

        text = '\n'.join([
            '---',
            'schema_version: wikify.wiki-page.v1',
            'id: page_intro',
            'title: Intro',
            'count: 3',
            'confidence: 0.75',
            'generated: true',
            'empty:',
            'outbound_links: ["page_a", "page_b"]',
            'source_refs: [{"source_id": "src_1", "item_id": "item_1"}]',
            '---',
            '# Intro',
            '',
        ])

        metadata, body = split_front_matter(text)

        self.assertEqual(metadata['schema_version'], 'wikify.wiki-page.v1')
        self.assertEqual(metadata['id'], 'page_intro')
        self.assertEqual(metadata['count'], 3)
        self.assertEqual(metadata['confidence'], 0.75)
        self.assertEqual(metadata['generated'], True)
        self.assertEqual(metadata['empty'], '')
        self.assertEqual(metadata['outbound_links'], ['page_a', 'page_b'])
        self.assertEqual(metadata['source_refs'], [{'source_id': 'src_1', 'item_id': 'item_1'}])
        self.assertEqual(body, '# Intro\n')

    def test_serialize_and_render_round_trip(self):
        from wikify.frontmatter import render_markdown_with_front_matter, serialize_front_matter, split_front_matter

        metadata = {
            'id': 'page_intro',
            'schema_version': 'wikify.wiki-page.v1',
            'confidence': 0.8,
            'outbound_links': ['page_a'],
            'source_refs': [{'source_id': 'src_1'}],
        }

        front_matter = serialize_front_matter(metadata)
        self.assertLess(front_matter.index('confidence:'), front_matter.index('id:'))
        self.assertIn('outbound_links: ["page_a"]', front_matter)
        self.assertIn('source_refs: [{"source_id": "src_1"}]', front_matter)

        rendered = render_markdown_with_front_matter(metadata, '# Intro\n')
        parsed, body = split_front_matter(rendered)

        self.assertEqual(parsed, metadata)
        self.assertEqual(body, '# Intro\n')

    def test_invalid_front_matter_raises_structured_error(self):
        from wikify.frontmatter import FrontMatterError, split_front_matter

        with self.assertRaises(FrontMatterError) as missing_delimiter:
            split_front_matter('---\nid: page_intro\n# Intro\n')
        self.assertEqual(missing_delimiter.exception.code, 'object_frontmatter_invalid')

        with self.assertRaises(FrontMatterError) as unsupported_list:
            split_front_matter('---\ntags:\n  - topic\n---\n# Intro\n')
        self.assertEqual(unsupported_list.exception.code, 'object_frontmatter_invalid')


if __name__ == '__main__':
    unittest.main()
