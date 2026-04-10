import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'source_index_manager.py'
SPEC = importlib.util.spec_from_file_location('source_index_manager', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SourceIndexManagerTests(unittest.TestCase):
    def test_normalize_status_known(self):
        self.assertEqual(MODULE.normalize_status('integrated'), 'integrated')

    def test_normalize_status_default(self):
        self.assertEqual(MODULE.normalize_status(''), 'briefed')

    def test_parse_rows(self):
        text = '| 标题 | 来源账号 | 日期 | URL | 标签 | 相关主题 | 类型 | 完整性 | 置信度 | 复用级别 | 跟进需求 | 状态 |\n|------|----------|------|-----|------|----------|------|--------|--------|----------|----------|------|\n| A | B | 2026-01-01 | u | t | x | 研究 | complete | high | high | yes | integrated |\n'
        rows = MODULE.parse_rows(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'integrated')

    def test_build_obsidian_source_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_parsed_dir = MODULE.PARSED_DIR
            original_sorted_dir = MODULE.SORTED_DIR
            try:
                MODULE.PARSED_DIR = Path(tmpdir) / 'parsed'
                MODULE.SORTED_DIR = Path(tmpdir) / 'sorted'
                MODULE.PARSED_DIR.mkdir(parents=True)
                MODULE.SORTED_DIR.mkdir(parents=True)
                (MODULE.PARSED_DIR / '2026-04-10_note.md').write_text('# 标题：测试来源\n', encoding='utf-8')
                (MODULE.SORTED_DIR / 'demo-topic-digest.md').write_text('# Digest\n', encoding='utf-8')
                text = MODULE.build_obsidian_source_index([
                    {'title': '测试来源', 'topics': 'demo-topic.md', 'status': 'integrated', 'date': '2026-04-10'}
                ], {'briefed': 0, 'integrated': 1, 'digested': 0, 'needs_review': 0})
            finally:
                MODULE.PARSED_DIR = original_parsed_dir
                MODULE.SORTED_DIR = original_sorted_dir
        self.assertIn('# Sources Index', text)
        self.assertIn('[[2026-04-10_note|测试来源]]', text)
        self.assertIn('[[demo-topic-digest]]', text)
        self.assertIn('[[demo-topic]]', text)


if __name__ == '__main__':
    unittest.main()
