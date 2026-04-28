import unittest


class GraphRelevanceTests(unittest.TestCase):
    def _node(self, node_id: str, node_type: str, title: str | None = None):
        from wikify.graph.model import GraphNode

        return GraphNode(
            id=node_id,
            path=f'/kb/{node_id}',
            relative_path=node_id,
            type=node_type,
            title=title or node_id,
            label=title or node_id,
        )

    def _edge(self, source: str, target: str, source_path: str, line: int = 1):
        from wikify.graph.model import GraphEdge

        return GraphEdge(
            source=source,
            target=target,
            type='markdown_link',
            provenance='EXTRACTED',
            confidence=1.0,
            source_path=source_path,
            line=line,
            label='link',
        )

    def test_compute_relevance_scores_explainable_signals(self):
        from wikify.graph.relevance import compute_relevance

        nodes = [
            self._node('topics/a.md', 'topics', 'A'),
            self._node('articles/parsed/a.md', 'parsed', 'A Source'),
            self._node('topics/b.md', 'topics', 'B'),
            self._node('topics/c.md', 'topics', 'C'),
        ]
        edges = [
            self._edge('topics/a.md', 'articles/parsed/a.md', 'topics/a.md'),
            self._edge('topics/a.md', 'topics/c.md', 'shared/source.md'),
            self._edge('articles/parsed/a.md', 'topics/c.md', 'shared/source.md'),
            self._edge('topics/b.md', 'topics/c.md', 'topics/b.md'),
        ]

        relevance = compute_relevance(nodes, edges)

        self.assertEqual(relevance['schema_version'], 'wikify.graph-relevance.v1')
        self.assertGreaterEqual(relevance['summary']['pair_count'], 1)

        pair = next(
            item
            for item in relevance['pairs']
            if item['source'] == 'topics/a.md' and item['target'] == 'articles/parsed/a.md'
        )
        self.assertGreater(pair['score'], 0)
        self.assertIn(pair['confidence'], {'medium', 'high'})
        self.assertEqual(pair['signals']['direct_link']['count'], 1)
        self.assertEqual(pair['signals']['source_overlap']['shared_count'], 1)
        self.assertGreater(pair['signals']['common_neighbors']['score'], 0)
        self.assertGreater(pair['signals']['type_affinity']['score'], 0)

        by_node = relevance['by_node']['topics/a.md']
        self.assertEqual(by_node['top_related'][0]['id'], 'articles/parsed/a.md')
        self.assertEqual(by_node['max_confidence'], pair['confidence'])
        self.assertEqual(by_node['top_related'][0]['signals']['direct_link'], 1)


if __name__ == '__main__':
    unittest.main()
