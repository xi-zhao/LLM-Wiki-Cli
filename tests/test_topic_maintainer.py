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

    def test_ensure_topic_file_obsidian_friendly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_topics_dir = MODULE.TOPICS_DIR
            original_sorted_dir = MODULE.SORTED_DIR
            try:
                MODULE.TOPICS_DIR = Path(tmpdir)
                MODULE.SORTED_DIR = Path(tmpdir) / 'sorted'
                MODULE.SORTED_DIR.mkdir()
                path = MODULE.ensure_topic_file('demo-topic.md')
                text = path.read_text(encoding='utf-8')
                moc_text = (MODULE.TOPICS_DIR / 'topics-moc.md').read_text(encoding='utf-8')
            finally:
                MODULE.TOPICS_DIR = original_topics_dir
                MODULE.SORTED_DIR = original_sorted_dir
        self.assertIn('type: topic', text)
        self.assertIn('## 笔记关系', text)
        self.assertIn('[[demo-topic-digest]]', text)
        self.assertIn('# Topics MOC', moc_text)
        self.assertIn('[[demo-topic|demo-topic]]', moc_text)

    def test_maintain_topic_adds_obsidian_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_topics_dir = MODULE.TOPICS_DIR
            original_sorted_dir = MODULE.SORTED_DIR
            try:
                MODULE.TOPICS_DIR = Path(tmpdir) / 'topics'
                MODULE.SORTED_DIR = Path(tmpdir) / 'sorted'
                MODULE.TOPICS_DIR.mkdir(parents=True)
                MODULE.SORTED_DIR.mkdir()
                parsed_path = Path(tmpdir) / 'sample-parsed.md'
                parsed_path.write_text(
                    '# 标题：测试文章\n\n## 核心结论\n1. 结论A\n\n## 关键事实 / 证据\n- 证据A\n',
                    encoding='utf-8',
                )
                result = MODULE.maintain_topic('demo-topic.md', str(parsed_path))
                text = (MODULE.TOPICS_DIR / 'demo-topic.md').read_text(encoding='utf-8')
                moc_text = (MODULE.TOPICS_DIR / 'topics-moc.md').read_text(encoding='utf-8')
            finally:
                MODULE.TOPICS_DIR = original_topics_dir
                MODULE.SORTED_DIR = original_sorted_dir
        self.assertEqual(result['status'], 'updated')
        self.assertIn('moc_path', result)
        self.assertIn('type: topic', text)
        self.assertIn('## 关联笔记（Obsidian）', text)
        self.assertIn('[[sample-parsed|测试文章]]', text)
        self.assertIn('[[demo-topic|demo-topic]]', moc_text)


    def test_build_topics_moc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_topics_dir = MODULE.TOPICS_DIR
            original_sorted_dir = MODULE.SORTED_DIR
            try:
                MODULE.TOPICS_DIR = Path(tmpdir) / 'topics'
                MODULE.SORTED_DIR = Path(tmpdir) / 'sorted'
                MODULE.TOPICS_DIR.mkdir(parents=True)
                MODULE.SORTED_DIR.mkdir(parents=True)
                (MODULE.TOPICS_DIR / 'demo-topic.md').write_text('# Topic: Demo Topic\n', encoding='utf-8')
                (MODULE.SORTED_DIR / 'demo-topic-digest.md').write_text('# Digest\n', encoding='utf-8')
                moc = MODULE.build_topics_moc()
            finally:
                MODULE.TOPICS_DIR = original_topics_dir
                MODULE.SORTED_DIR = original_sorted_dir
        self.assertIn('# Topics MOC', moc)
        self.assertIn('[[demo-topic|Demo Topic]]', moc)
        self.assertIn('[[demo-topic-digest]]', moc)


if __name__ == '__main__':
    unittest.main()
