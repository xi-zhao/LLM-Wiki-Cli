import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'ingest_result_enricher.py'
SPEC = importlib.util.spec_from_file_location('ingest_result_enricher', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class IngestResultEnricherTests(unittest.TestCase):
    def test_assess_extraction_quality_detects_chrome_noise(self):
        parsed = '# 标题：llm-wiki\n\nYou signed in with another tab or window. Reload to refresh your session.\n'
        quality, reasons = MODULE.assess_extraction_quality(parsed)
        self.assertEqual(quality, 'low')
        self.assertIn('chrome_noise_detected', reasons)

    def test_assess_routing_quality_when_topic_missing(self):
        quality, reasons = MODULE.assess_routing_quality([], [])
        self.assertEqual(quality, 'low')
        self.assertIn('no_topics_detected', reasons)

    def test_assess_routing_quality_when_topics_unchanged(self):
        quality, reasons = MODULE.assess_routing_quality(['a.md'], [{'topic': 'a.md', 'status': 'no_change'}])
        self.assertEqual(quality, 'medium')
        self.assertIn('topics_unchanged', reasons)

    def test_derive_lifecycle_status_integrated(self):
        payload = {
            'files': {'raw': 'a', 'parsed': 'b', 'brief': 'c'},
            'updated_topics': [{'topic': 'topic1', 'status': 'updated'}],
            'generated_digests': [],
        }
        status = MODULE.derive_lifecycle_status(payload, 'high', 'high')
        self.assertEqual(status, 'integrated')


if __name__ == '__main__':
    unittest.main()
