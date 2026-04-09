import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ingest_web_direct_url.py"
SPEC = importlib.util.spec_from_file_location("ingest_web_direct_url", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class IngestWebDirectUrlTests(unittest.TestCase):
    def test_detect_web_tags_prefers_web_over_wechat(self):
        tags = MODULE.detect_web_tags(
            "Quantum-Centric Supercomputing",
            "IBM Research describes quantum computing, HPC integration, and reference architecture.",
            "IBM Research",
            "https://research.ibm.com/blog/test",
        )

        self.assertIn("网页", tags)
        self.assertIn("IBM", tags)
        self.assertIn("量子计算", tags)
        self.assertNotIn("微信公众号", tags)

    def test_detect_web_tags_avoid_substring_false_positives(self):
        tags = MODULE.detect_web_tags(
            "Quantum-Centric Supercomputing",
            "The runtime focuses on error correction decoding and cloud storage orchestration.",
            "IBM Research",
            "https://research.ibm.com/blog/test",
        )

        self.assertNotIn("RAG", tags)
        self.assertNotIn("AI 编程", tags)

    def test_detect_web_topics_avoid_decoding_false_positive(self):
        topics = MODULE.detect_web_topics(
            "Quantum-Centric Supercomputing",
            "The classical runtime handles error correction decoding for quantum workloads.",
        )

        self.assertNotIn("ai-coding-and-autoresearch.md", topics)

    def test_parse_body_lines_filters_web_chrome(self):
        raw_text = "\n".join(
            [
                "12 Mar 2026",
                "Technical note",
                "7 minute read",
                "Quantum computing has reached a stage where it is now comparable to leading classical methods.",
                "Application layer",
                "Start using our 100+ qubit systems",
                "View pricing",
            ]
        )

        lines = MODULE.parse_body_lines(
            raw_text,
            "Unveiling the first reference architecture for quantum-centric supercomputing",
            "IBM Research",
            "2026-03-12",
        )

        self.assertEqual(
            lines,
            [
                "Quantum computing has reached a stage where it is now comparable to leading classical methods.",
                "Application layer",
            ],
        )

    def test_detect_type_does_not_treat_incidental_how_to_as_tutorial(self):
        article_type = MODULE.detect_type(
            "Unveiling the first reference architecture for quantum-centric supercomputing",
            (
                "Recent joint work between Cleveland Clinic and IBM demonstrated a quantum-centric "
                "supercomputing workflow. The middleware facilitates communication about how to handle "
                "outputs for iterative workload executions."
            ),
        )

        self.assertEqual(article_type, "研究")


if __name__ == "__main__":
    unittest.main()
