import importlib.util
import unittest
from pathlib import Path


WECHAT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'ingest_wechat_direct_url.py'
WECHAT_SPEC = importlib.util.spec_from_file_location('ingest_wechat_passthrough', WECHAT_PATH)
WECHAT = importlib.util.module_from_spec(WECHAT_SPEC)
assert WECHAT_SPEC and WECHAT_SPEC.loader
WECHAT_SPEC.loader.exec_module(WECHAT)

WEB_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'ingest_web_direct_url.py'
WEB_SPEC = importlib.util.spec_from_file_location('ingest_web_passthrough', WEB_PATH)
WEB = importlib.util.module_from_spec(WEB_SPEC)
assert WEB_SPEC and WEB_SPEC.loader
WEB_SPEC.loader.exec_module(WEB)


class IngestTopicPassthroughTests(unittest.TestCase):
    def test_wechat_detect_topics_returns_list(self):
        topics = WECHAT.detect_topics('AI 语音赛道的角逐，可能已经结束了。', 'VoxCPM 2 与端侧 AI、小模型、多语种、方言。')
        self.assertIsInstance(topics, list)
        self.assertIn('ai-voice-and-edge-models.md', topics)

    def test_web_detect_topics_returns_list(self):
        topics = WEB.detect_web_topics('LLM Wiki', 'A persistent wiki with agents, prompts, synthesis, knowledge base and research workflow.')
        self.assertIsInstance(topics, list)
        self.assertIn('ai-research-writing.md', topics)


if __name__ == '__main__':
    unittest.main()
