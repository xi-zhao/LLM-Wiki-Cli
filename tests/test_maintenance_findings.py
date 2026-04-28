import unittest


class MaintenanceFindingsTests(unittest.TestCase):
    def test_build_findings_derives_actionable_graph_findings(self):
        from wikify.maintenance.findings import build_findings, summarize_findings

        graph = {
            'schema_version': 'wikify.graph.v1',
            'analytics': {
                'node_count': 4,
                'edge_count': 3,
                'broken_links': [
                    {
                        'source': 'topics/a.md',
                        'target': 'Missing',
                        'line': 7,
                        'label': 'unresolved_wikilink',
                    }
                ],
                'orphans': [
                    {'id': 'sources/index.md', 'title': 'Sources', 'type': 'sources'}
                ],
                'central_nodes': [
                    {'id': 'topics/a.md', 'title': 'A', 'type': 'topics', 'degree': 12}
                ],
                'communities': [
                    {
                        'id': 'community-1',
                        'nodes': ['topics/a.md', 'articles/parsed/a.md', 'sorted/a.md'],
                        'size': 3,
                    }
                ],
            },
        }

        findings = build_findings(graph)

        self.assertEqual(
            {finding['type'] for finding in findings},
            {'broken_link', 'orphan_node', 'god_node', 'mature_community'},
        )
        for finding in findings:
            for key in [
                'id',
                'type',
                'severity',
                'title',
                'subject',
                'evidence',
                'recommended_action',
                'can_auto_apply',
                'policy_minimum',
            ]:
                self.assertIn(key, finding)

        summary = summarize_findings(findings)

        self.assertEqual(summary['finding_count'], 4)
        self.assertEqual(summary['by_type']['broken_link'], 1)
        self.assertEqual(summary['by_type']['orphan_node'], 1)
        self.assertEqual(summary['by_type']['god_node'], 1)
        self.assertEqual(summary['by_type']['mature_community'], 1)
        self.assertEqual(summary['by_severity']['warning'], 1)
        self.assertEqual(summary['by_severity']['info'], 3)


if __name__ == '__main__':
    unittest.main()
