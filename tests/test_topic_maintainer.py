import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'topic_maintainer.py'
SPEC = importlib.util.spec_from_file_location('topic_maintainer', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class TopicMaintainerTests(unittest.TestCase):
    def test_infer_title_from_parsed_file(self):
        text = '# 标题：测试文章\n\n## 核心结论\n1. 结论A\n'
        self.assertEqual(MODULE.infer_title(text, 'fallback'), '测试文章')

    def test_append_unique_bullet(self):
        section = '- A\n'
        updated = MODULE.append_unique_bullet(section, 'B')
        self.assertIn('- A', updated)
        self.assertIn('- B', updated)
        self.assertEqual(MODULE.append_unique_bullet(updated, 'B').count('- B'), 1)

    def test_extract_numbered_section(self):
        text = '## 核心结论\n1. 结论A\n2. 结论B\n\n## 其他\n- x\n'
        self.assertEqual(MODULE.extract_numbered_section(text, '核心结论'), ['结论A', '结论B'])


if __name__ == '__main__':
    unittest.main()
