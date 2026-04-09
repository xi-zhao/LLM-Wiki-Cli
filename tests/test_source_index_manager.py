import importlib.util
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


if __name__ == '__main__':
    unittest.main()
