import tempfile
import unittest
from pathlib import Path


def build_temp_kb(root: Path):
    topic_dir = root / 'topics'
    parsed_dir = root / 'articles' / 'parsed'
    topic_dir.mkdir(parents=True)
    parsed_dir.mkdir(parents=True)
    (topic_dir / 'agent-loop.md').write_text(
        '\n'.join([
            '# Agent Loop',
            '',
            'See [Parsed Article](../articles/parsed/a.md).',
            'Missing concept: [[Concept Note]].',
            '',
        ]),
        encoding='utf-8',
    )
    (parsed_dir / 'a.md').write_text(
        '\n'.join([
            '# Parsed Article',
            '',
            'Back to [Agent Loop](../../topics/agent-loop.md).',
            '',
        ]),
        encoding='utf-8',
    )


class GraphExtractorTests(unittest.TestCase):
    def test_extract_nodes_for_markdown_objects(self):
        from wikify.graph.extractors import extract_nodes
        from wikify.markdown_index import scan_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_temp_kb(root)

            objects = scan_objects(root)
            nodes = extract_nodes(objects)

        node_ids = {node.id for node in nodes}
        self.assertIn('topics/agent-loop.md', node_ids)
        self.assertIn('articles/parsed/a.md', node_ids)

    def test_markdown_links_and_broken_wikilinks_become_edges(self):
        from wikify.graph.extractors import extract_edges, extract_nodes
        from wikify.markdown_index import scan_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_temp_kb(root)

            objects = scan_objects(root)
            nodes = extract_nodes(objects)
            edges = extract_edges(objects, nodes)

        edge_dicts = [edge.to_dict() for edge in edges]
        extracted = [edge for edge in edge_dicts if edge['provenance'] == 'EXTRACTED']
        ambiguous = [edge for edge in edge_dicts if edge['provenance'] == 'AMBIGUOUS']

        self.assertTrue(any(edge['type'] == 'markdown_link' for edge in extracted))
        self.assertTrue(any(edge['type'] == 'broken_link' for edge in ambiguous))
        self.assertTrue(any(edge['target'] == 'Concept Note' for edge in ambiguous))
        for edge in edge_dicts:
            for key in ['source', 'target', 'type', 'provenance', 'confidence', 'source_path', 'line', 'label']:
                self.assertIn(key, edge)

    def test_nodes_keep_path_ids_while_exposing_object_metadata(self):
        from wikify.graph.extractors import extract_edges, extract_nodes
        from wikify.markdown_index import scan_objects

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            topics = root / 'topics'
            parsed = root / 'articles' / 'parsed'
            topics.mkdir(parents=True)
            parsed.mkdir(parents=True)
            (topics / 'agent-loop.md').write_text(
                '\n'.join([
                    '---',
                    'schema_version: wikify.wiki-page.v1',
                    'id: page_agent_loop',
                    'type: wiki_page',
                    'title: Agent Loop',
                    'summary: Agent loop summary',
                    'source_refs: []',
                    'outbound_links: ["page_article"]',
                    'confidence: 0.8',
                    'review_status: generated',
                    '---',
                    '# Agent Loop',
                    '',
                    'See [Parsed Article](../articles/parsed/a.md).',
                    '',
                ]),
                encoding='utf-8',
            )
            (parsed / 'a.md').write_text('# Parsed Article\n', encoding='utf-8')

            objects = scan_objects(root)
            nodes = extract_nodes(objects)
            edges = extract_edges(objects, nodes)

        agent_node = next(node for node in nodes if node.relative_path == 'topics/agent-loop.md')
        agent_dict = agent_node.to_dict()
        self.assertEqual(agent_node.id, 'topics/agent-loop.md')
        self.assertEqual(agent_dict['object_id'], 'page_agent_loop')
        self.assertEqual(agent_dict['canonical_type'], 'wiki_page')
        self.assertTrue(
            any(edge.source == 'topics/agent-loop.md' and edge.target == 'articles/parsed/a.md' for edge in edges)
        )
        for edge in [edge.to_dict() for edge in edges]:
            for key in ['source', 'target', 'type', 'provenance', 'confidence', 'source_path', 'line', 'label']:
                self.assertIn(key, edge)


if __name__ == '__main__':
    unittest.main()
