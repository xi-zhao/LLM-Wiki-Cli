import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "fetch_web_article.py"
SPEC = importlib.util.spec_from_file_location("fetch_web_article", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FetchWebArticleTests(unittest.TestCase):
    def test_normalize_date_supports_english_month_names(self):
        self.assertEqual(MODULE.normalize_date("12 Mar 2026"), "2026-03-12")

    def test_extract_article_payload_from_html(self):
        html = """
        <html>
          <head>
            <title>Ignored Title</title>
            <meta property="og:title" content="Quantum-Centric Supercomputing" />
            <meta property="article:published_time" content="2026-03-26T10:30:00Z" />
            <meta name="author" content="IBM Research" />
          </head>
          <body>
            <article>
              <p>Quantum systems are moving into real HPC environments.</p>
              <p>IBM describes a reference architecture for hybrid orchestration.</p>
              <img src="/images/chart.png" alt="Chart" />
            </article>
          </body>
        </html>
        """

        payload = MODULE.extract_article_payload_from_html(html, "https://research.ibm.com/blog/test")

        self.assertEqual(payload["title"], "Quantum-Centric Supercomputing")
        self.assertEqual(payload["source_account"], "IBM Research")
        self.assertEqual(payload["publish_time"], "2026-03-26")
        self.assertIn("Quantum systems are moving into real HPC environments.", payload["content_text"])
        self.assertIn("IBM describes a reference architecture for hybrid orchestration.", payload["content_text"])
        self.assertEqual(len(payload["images"]), 1)
        self.assertEqual(payload["images"][0]["url"], "https://research.ibm.com/images/chart.png")


if __name__ == "__main__":
    unittest.main()
