import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'ingest_any_url.py'
SPEC = importlib.util.spec_from_file_location('ingest_any_url', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class IngestAnyUrlTests(unittest.TestCase):
    def test_detect_source_type_wechat(self):
        self.assertEqual(
            MODULE.detect_source_type('https://mp.weixin.qq.com/s/uobH2YIudbZdix41pbhI7g'),
            'wechat',
        )

    def test_detect_source_type_web(self):
        self.assertEqual(
            MODULE.detect_source_type('https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f'),
            'web',
        )

    def test_parse_json_output_reads_last_json_line(self):
        payload = MODULE.parse_json_output('line1\n{"ok":true}\n')
        self.assertEqual(payload, {'ok': True})

    def test_infer_topic_candidates_dedupes(self):
        topics = MODULE.infer_topic_candidates(
            {
                'topics': ['ai-coding-and-autoresearch.md', 'ai-coding-and-autoresearch.md'],
                'related_topics': ['ai-research-writing.md'],
            }
        )
        self.assertEqual(topics, ['ai-coding-and-autoresearch.md', 'ai-research-writing.md'])


if __name__ == '__main__':
    unittest.main()
