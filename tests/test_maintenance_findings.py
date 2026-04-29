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
                'relevance': {
                    'schema_version': 'wikify.graph-relevance.v1',
                    'by_node': {
                        'topics/a.md': {
                            'max_score': 8.5,
                            'max_confidence': 'high',
                            'top_related': [
                                {
                                    'id': 'articles/parsed/a.md',
                                    'score': 8.5,
                                    'confidence': 'high',
                                    'signals': {
                                        'direct_link': 1,
                                        'source_overlap': 1,
                                        'common_neighbors': 1,
                                        'type_affinity': 1.0,
                                    },
                                }
                            ],
                        },
                        'sources/index.md': {
                            'max_score': 1.0,
                            'max_confidence': 'low',
                            'top_related': [
                                {
                                    'id': 'topics/a.md',
                                    'score': 1.0,
                                    'confidence': 'low',
                                    'signals': {
                                        'direct_link': 0,
                                        'source_overlap': 0,
                                        'common_neighbors': 0,
                                        'type_affinity': 1.0,
                                    },
                                }
                            ],
                        },
                    },
                },
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

        by_subject = {finding['subject']: finding for finding in findings}
        self.assertEqual(by_subject['topics/a.md']['relevance']['max_confidence'], 'high')
        self.assertEqual(by_subject['sources/index.md']['relevance']['max_confidence'], 'low')
        self.assertFalse(by_subject['sources/index.md']['relevance']['priority_signal'])

        summary = summarize_findings(findings)

        self.assertEqual(summary['finding_count'], 4)
        self.assertEqual(summary['by_type']['broken_link'], 1)
        self.assertEqual(summary['by_type']['orphan_node'], 1)
        self.assertEqual(summary['by_type']['god_node'], 1)
        self.assertEqual(summary['by_type']['mature_community'], 1)
        self.assertEqual(summary['by_severity']['warning'], 1)
        self.assertEqual(summary['by_severity']['info'], 3)

    def test_build_findings_enriches_generated_page_targets(self):
        from wikify.maintenance.findings import build_findings

        graph = {
            'schema_version': 'wikify.graph.v1',
            'analytics': {
                'node_count': 1,
                'edge_count': 1,
                'broken_links': [
                    {
                        'source': 'wiki/pages/page_alpha.md',
                        'target': 'Missing',
                        'line': 5,
                        'label': 'unresolved_wikilink',
                    }
                ],
            },
        }
        targets = {
            'schema_version': 'wikify.maintenance-targets.v1',
            'by_object_id': {},
            'by_path': {
                'wiki/pages/page_alpha.md': {
                    'target_kind': 'wiki_page',
                    'target_family': 'personal_wiki_page',
                    'object_id': 'page_alpha',
                    'object_type': 'wiki_page',
                    'body_path': 'wiki/pages/page_alpha.md',
                    'object_path': 'artifacts/objects/wiki_pages/page_alpha.json',
                    'source_refs': [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}],
                    'review_status': 'generated',
                    'write_scope': ['wiki/pages/page_alpha.md'],
                }
            },
        }

        findings = build_findings(graph, targets=targets)

        finding = findings[0]
        self.assertEqual(finding['target_family'], 'personal_wiki_page')
        self.assertEqual(finding['object_id'], 'page_alpha')
        self.assertEqual(finding['object_type'], 'wiki_page')
        self.assertEqual(finding['body_path'], 'wiki/pages/page_alpha.md')
        self.assertEqual(finding['source_refs'][0]['source_id'], 'src_notes')
        self.assertEqual(finding['review_status'], 'generated')
        self.assertEqual(finding['write_scope'], ['wiki/pages/page_alpha.md'])


if __name__ == '__main__':
    unittest.main()
