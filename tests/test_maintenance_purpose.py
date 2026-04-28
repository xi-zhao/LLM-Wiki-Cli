import tempfile
import unittest
from pathlib import Path


class MaintenancePurposeTests(unittest.TestCase):
    def test_load_purpose_context_reads_purpose_md(self):
        from wikify.maintenance.purpose import load_purpose_context

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'purpose.md').write_text(
                '\n'.join([
                    '# Research Memory',
                    '',
                    'Goal: preserve decisions that help agents maintain the wiki.',
                    'Key question: which repairs increase long-term coherence?',
                    '',
                    'The wiki should favor auditable structure over hidden generation.',
                ]),
                encoding='utf-8',
            )

            context = load_purpose_context(kb)

            self.assertEqual(context['schema_version'], 'wikify.purpose-context.v1')
            self.assertTrue(context['present'])
            self.assertEqual(context['relative_path'], 'purpose.md')
            self.assertEqual(context['title'], 'Research Memory')
            self.assertIn('preserve decisions', context['excerpt'])
            self.assertEqual(context['goal_lines'], ['Goal: preserve decisions that help agents maintain the wiki.'])
            self.assertEqual(context['question_lines'], ['Key question: which repairs increase long-term coherence?'])

    def test_load_purpose_context_prefers_purpose_md_over_wikify_purpose(self):
        from wikify.maintenance.purpose import load_purpose_context

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            (kb / 'purpose.md').write_text('# Primary\n\nGoal: primary.', encoding='utf-8')
            (kb / 'wikify-purpose.md').write_text('# Secondary\n\nGoal: secondary.', encoding='utf-8')

            context = load_purpose_context(kb)

            self.assertEqual(context['relative_path'], 'purpose.md')
            self.assertEqual(context['title'], 'Primary')

    def test_missing_purpose_is_non_blocking(self):
        from wikify.maintenance.purpose import load_purpose_context

        with tempfile.TemporaryDirectory() as tmpdir:
            context = load_purpose_context(Path(tmpdir))

            self.assertFalse(context['present'])
            self.assertIn('purpose.md', context['candidates'])
            self.assertIn('wikify-purpose.md', context['candidates'])
            self.assertEqual(context['excerpt'], '')


if __name__ == '__main__':
    unittest.main()
