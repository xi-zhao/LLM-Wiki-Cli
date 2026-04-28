import json
import shutil
import tempfile
import unittest
from pathlib import Path


class GraphBuilderTests(unittest.TestCase):
    def test_build_graph_artifacts_writes_json_report_and_html(self):
        from wikify.graph.builder import build_graph_artifacts

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir) / 'sample-kb'
            shutil.copytree(repo / 'sample-kb', kb)

            result = build_graph_artifacts(kb, include_html=True)

            graph_json = kb / 'graph' / 'graph.json'
            report = kb / 'graph' / 'GRAPH_REPORT.md'
            html = kb / 'graph' / 'graph.html'
            self.assertTrue(graph_json.exists())
            self.assertTrue(report.exists())
            self.assertTrue(html.exists())

            graph = json.loads(graph_json.read_text(encoding='utf-8'))
            self.assertEqual(graph['schema_version'], 'wikify.graph.v1')
            self.assertIn('nodes', graph)
            self.assertIn('edges', graph)
            self.assertIn('analytics', graph)
            for key in ['node_count', 'edge_count', 'community_count', 'orphan_count', 'central_nodes']:
                self.assertIn(key, graph['analytics'])

            report_text = report.read_text(encoding='utf-8')
            self.assertIn('# Wikify Graph Report', report_text)
            self.assertIn('God Nodes', report_text)
            self.assertIn('Communities', report_text)
            self.assertIn('Orphans', report_text)
            self.assertIn('Suggested Questions', report_text)

            self.assertEqual(result['artifacts']['json'], str(graph_json.resolve()))
            self.assertEqual(result['artifacts']['report'], str(report.resolve()))
            self.assertEqual(result['artifacts']['html'], str(html.resolve()))
            self.assertGreaterEqual(result['summary']['node_count'], 1)

    def test_build_graph_artifacts_can_skip_html(self):
        from wikify.graph.builder import build_graph_artifacts

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir) / 'sample-kb'
            shutil.copytree(repo / 'sample-kb', kb)

            result = build_graph_artifacts(kb, include_html=False)

            self.assertTrue((kb / 'graph' / 'graph.json').exists())
            self.assertTrue((kb / 'graph' / 'GRAPH_REPORT.md').exists())
            self.assertFalse((kb / 'graph' / 'graph.html').exists())
            self.assertIsNone(result['artifacts']['html'])


if __name__ == '__main__':
    unittest.main()
