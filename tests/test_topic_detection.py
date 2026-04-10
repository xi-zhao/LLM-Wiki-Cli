import importlib.util
import unittest
from pathlib import Path


WECHAT_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'ingest_wechat_direct_url.py'
WECHAT_SPEC = importlib.util.spec_from_file_location('ingest_wechat_direct_url_topics', WECHAT_PATH)
WECHAT = importlib.util.module_from_spec(WECHAT_SPEC)
assert WECHAT_SPEC and WECHAT_SPEC.loader
WECHAT_SPEC.loader.exec_module(WECHAT)

WEB_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'ingest_web_direct_url.py'
WEB_SPEC = importlib.util.spec_from_file_location('ingest_web_direct_url_topics', WEB_PATH)
WEB = importlib.util.module_from_spec(WEB_SPEC)
assert WEB_SPEC and WEB_SPEC.loader
WEB_SPEC.loader.exec_module(WEB)


class TopicDetectionTests(unittest.TestCase):
    def test_wechat_quantum_detection(self):
        topics = WECHAT.detect_topics(
            '量子计算赛道投资热度再起',
            '量子计算、超导量子、融资与政策信号正在共同推动赛道升温。',
        )
        self.assertIn('quantum-computing-industry.md', topics)

    def test_wechat_voice_detection(self):
        topics = WECHAT.detect_topics(
            'AI 语音赛道的角逐，可能已经结束了。',
            'VoxCPM 2 支持音色克隆、多语种、方言、端侧 AI 与小模型部署。',
        )
        self.assertIn('ai-voice-and-edge-models.md', topics)

    def test_web_llm_wiki_detection(self):
        topics = WEB.detect_web_topics(
            'LLM Wiki',
            'A pattern for building personal knowledge bases using LLMs. The agent incrementally builds and maintains a persistent wiki with cross-references and synthesis.',
        )
        self.assertIn('ai-research-writing.md', topics)
        self.assertIn('ai-coding-and-autoresearch.md', topics)


if __name__ == '__main__':
    unittest.main()
