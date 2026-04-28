import importlib
import os
import unittest
from pathlib import Path


class WikifyCliTests(unittest.TestCase):
    def test_discover_base_prefers_wikify_base(self):
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            os.environ['WIKIFY_BASE'] = '/tmp/wikify-base'
            os.environ['FOKB_BASE'] = '/tmp/fokb-base'
            config = importlib.import_module('wikify.config')

            self.assertEqual(config.discover_base(), Path('/tmp/wikify-base').resolve())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_discover_base_falls_back_to_fokb_base(self):
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            os.environ.pop('WIKIFY_BASE', None)
            os.environ['FOKB_BASE'] = '/tmp/fokb-base'
            config = importlib.import_module('wikify.config')

            self.assertEqual(config.discover_base(), Path('/tmp/fokb-base').resolve())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_build_parser_uses_wikify_program_name(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()

        self.assertEqual(parser.prog, 'wikify')

    def test_build_parser_accepts_graph_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['graph', '--scope', 'all', '--no-html'])

        self.assertEqual(args.command, 'graph')
        self.assertEqual(args.scope, 'all')
        self.assertTrue(args.no_html)


if __name__ == '__main__':
    unittest.main()
