import importlib
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
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

    def test_build_parser_accepts_maintain_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['maintain', '--policy', 'balanced', '--dry-run'])

        self.assertEqual(args.command, 'maintain')
        self.assertEqual(args.policy, 'balanced')
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_tasks_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['tasks', '--status', 'queued', '--limit', '1'])

        self.assertEqual(args.command, 'tasks')
        self.assertEqual(args.status, 'queued')
        self.assertEqual(args.limit, 1)

    def test_graph_command_writes_json_and_report_without_html(self):
        cli = importlib.import_module('wikify.cli')
        repo = Path(__file__).resolve().parents[1]
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir) / 'sample-kb'
                shutil.copytree(repo / 'sample-kb', kb)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'graph', '--no-html'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'graph')
                self.assertTrue((kb / 'graph' / 'graph.json').exists())
                self.assertTrue((kb / 'graph' / 'GRAPH_REPORT.md').exists())
                self.assertFalse((kb / 'graph' / 'graph.html').exists())
                self.assertIsNone(payload['result']['artifacts']['html'])
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_maintain_command_dry_run_writes_graph_only(self):
        cli = importlib.import_module('wikify.cli')
        repo = Path(__file__).resolve().parents[1]
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir) / 'sample-kb'
                shutil.copytree(repo / 'sample-kb', kb)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'maintain', '--dry-run'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'maintain')
                self.assertTrue((kb / 'graph' / 'graph.json').exists())
                self.assertFalse((kb / 'sorted' / 'graph-findings.json').exists())
                self.assertFalse((kb / 'sorted' / 'graph-maintenance-plan.json').exists())
                self.assertFalse((kb / 'sorted' / 'graph-maintenance-history.json').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_tasks_command_lists_tasks_after_maintain(self):
        cli = importlib.import_module('wikify.cli')
        repo = Path(__file__).resolve().parents[1]
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir) / 'sample-kb'
                shutil.copytree(repo / 'sample-kb', kb)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                with self.assertRaises(SystemExit) as raised:
                    cli.main(['--output', 'quiet', 'maintain'])
                self.assertEqual(raised.exception.code, 0)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'tasks', '--status', 'queued', '--limit', '2'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'tasks')
                self.assertLessEqual(payload['result']['summary']['task_count'], 2)
                self.assertTrue((kb / 'sorted' / 'graph-agent-tasks.json').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_tasks_command_refreshes_missing_queue(self):
        cli = importlib.import_module('wikify.cli')
        repo = Path(__file__).resolve().parents[1]
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir) / 'sample-kb'
                shutil.copytree(repo / 'sample-kb', kb)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'tasks', '--refresh', '--id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertTrue(payload['result']['refreshed'])
                self.assertEqual(payload['result']['task_queue']['tasks'][0]['id'], 'agent-task-1')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_tasks_command_missing_queue_returns_structured_error(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['WIKIFY_BASE'] = tmpdir
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'tasks'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'tasks')
                self.assertEqual(payload['error']['code'], 'agent_task_queue_missing')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb


if __name__ == '__main__':
    unittest.main()
