import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ingest_wechat_direct_url.py"
SPEC = importlib.util.spec_from_file_location("ingest_wechat_direct_url", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class IngestWeChatDirectUrlTests(unittest.TestCase):
    def test_publish_line_with_location_is_treated_as_noise(self):
        self.assertTrue(MODULE.looks_like_publish_line("2026年4月3日 16:29 安徽", ""))

    def test_core_points_skip_publish_line_with_location(self):
        lines = [
            "2026年4月3日 16:29 安徽",
            "作为 OpenAI 创始成员、特斯拉前 AI 总监，Karpathy 的 token 消耗量肯定不小。",
            "这很反直觉。大家谈 AI 编程、谈 Copilot、谈 Cursor，好像 LLM 就是为写代码而生的。",
        ]

        core_points = MODULE.pick_core_points(lines, "Andrej Karpathy 最近分享了他用 LLM 构建个人知识库的方法。")

        self.assertNotIn("2026年4月3日 16:29 安徽", core_points)
        self.assertTrue(core_points)

    def test_compress_clausey_line_keeps_english_sentence_natural(self):
        text = (
            "As quantum computing continues to advance, high-accuracy QCSC algorithms like SQD will "
            "be available at a scale that is challenging for the most advanced classical computing "
            "methods, driving urgency for domain scientists to integrate quantum into their toolkits."
        )

        compact = MODULE.compress_clausey_line(text, 110)

        self.assertNotIn("等问题。", compact)
        self.assertTrue(compact.endswith("…"))


if __name__ == "__main__":
    unittest.main()
