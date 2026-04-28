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
    def _write_apply_fixture(self, kb: Path):
        (kb / 'topics').mkdir(parents=True)
        target = kb / 'topics' / 'a.md'
        target.write_text('See [[Missing]].\n', encoding='utf-8')
        proposal = {
            'schema_version': 'wikify.patch-proposal.v1',
            'task_id': 'agent-task-1',
            'source_finding_id': 'broken-link:topics/a.md:7:Missing',
            'action': 'queue_link_repair',
            'target': 'topics/a.md',
            'write_scope': ['topics/a.md'],
            'planned_edits': [
                {
                    'operation': 'propose_content_patch',
                    'path': 'topics/a.md',
                    'action': 'queue_link_repair',
                    'instructions': ['repair link'],
                    'evidence': {},
                    'status': 'planned',
                }
            ],
            'acceptance_checks': ['link resolves'],
            'risk': 'medium',
            'preflight': {'write_scope_valid': True},
        }
        proposal_path = kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json'
        proposal_path.parent.mkdir(parents=True)
        proposal_path.write_text(json.dumps(proposal), encoding='utf-8')
        bundle = {
            'schema_version': 'wikify.patch-bundle.v1',
            'proposal_task_id': 'agent-task-1',
            'proposal_path': 'sorted/graph-patch-proposals/agent-task-1.json',
            'operations': [
                {
                    'operation': 'replace_text',
                    'path': 'topics/a.md',
                    'find': '[[Missing]]',
                    'replace': '[[Existing]]',
                }
            ],
        }
        bundle_path = kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
        bundle_path.parent.mkdir(parents=True)
        bundle_path.write_text(json.dumps(bundle), encoding='utf-8')
        return proposal_path, bundle_path, target

    def _write_run_task_queue(self, kb: Path):
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 1},
            'tasks': [
                {
                    'id': 'agent-task-1',
                    'source_finding_id': 'broken-link:topics/a.md:1:Missing',
                    'source_step_id': 'step-1',
                    'action': 'queue_link_repair',
                    'priority': 'high',
                    'target': 'topics/a.md',
                    'evidence': {'source': 'topics/a.md', 'line': 1, 'target': 'Missing'},
                    'write_scope': ['topics/a.md'],
                    'agent_instructions': ['repair link'],
                    'acceptance_checks': ['link resolves'],
                    'requires_user': False,
                    'status': 'queued',
                }
            ],
        }
        path = kb / 'sorted' / 'graph-agent-tasks.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(queue), encoding='utf-8')
        return path

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

    def test_build_parser_accepts_propose_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['propose', '--task-id', 'agent-task-1', '--dry-run'])

        self.assertEqual(args.command, 'propose')
        self.assertEqual(args.task_id, 'agent-task-1')
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_bundle_request_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['bundle-request', '--task-id', 'agent-task-1', '--dry-run'])

        self.assertEqual(args.command, 'bundle-request')
        self.assertEqual(args.task_id, 'agent-task-1')
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_apply_and_rollback_commands(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        apply_args = parser.parse_args([
            'apply',
            '--proposal-path',
            'sorted/graph-patch-proposals/agent-task-1.json',
            '--bundle-path',
            'sorted/graph-patch-bundles/agent-task-1.json',
            '--dry-run',
        ])
        rollback_args = parser.parse_args([
            'rollback',
            '--application-path',
            'sorted/graph-patch-applications/app.json',
            '--dry-run',
        ])

        self.assertEqual(apply_args.command, 'apply')
        self.assertTrue(apply_args.dry_run)
        self.assertEqual(rollback_args.command, 'rollback')
        self.assertTrue(rollback_args.dry_run)

    def test_build_parser_accepts_run_task_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'run-task',
            '--id',
            'agent-task-1',
            '--bundle-path',
            'sorted/graph-patch-bundles/agent-task-1.json',
            '--dry-run',
        ])

        self.assertEqual(args.command, 'run-task')
        self.assertEqual(args.id, 'agent-task-1')
        self.assertTrue(args.dry_run)

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

    def test_propose_command_writes_proposal_after_maintain(self):
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
                    cli.main(['--output', 'json', 'propose', '--task-id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                proposal_path = kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json'
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'propose')
                self.assertTrue(payload['result']['summary']['written'])
                self.assertEqual(payload['result']['proposal']['schema_version'], 'wikify.patch-proposal.v1')
                self.assertTrue(proposal_path.exists())
                self.assertEqual(queue['tasks'][0]['status'], 'queued')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_propose_command_dry_run_does_not_write_proposal(self):
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
                    cli.main(['--output', 'json', 'propose', '--task-id', 'agent-task-1', '--dry-run'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertTrue(payload['result']['dry_run'])
                self.assertFalse(payload['result']['summary']['written'])
                self.assertIsNone(payload['result']['artifacts']['patch_proposal'])
                self.assertFalse((kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_propose_command_missing_queue_returns_structured_error(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['WIKIFY_BASE'] = tmpdir
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'propose', '--task-id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'propose')
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

    def test_propose_command_proposal_errors_are_structured(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                queue = {
                    'schema_version': 'wikify.graph-agent-tasks.v1',
                    'summary': {'task_count': 1},
                    'tasks': [
                        {
                            'id': 'agent-task-1',
                            'source_finding_id': 'broken-link:a',
                            'action': 'queue_link_repair',
                            'priority': 'high',
                            'target': 'topics/a.md',
                            'evidence': {'source': 'topics/other.md'},
                            'write_scope': ['topics/a.md'],
                            'agent_instructions': ['repair link'],
                            'acceptance_checks': ['link resolves'],
                            'requires_user': False,
                            'status': 'queued',
                        },
                    ],
                }
                target = kb / 'sorted' / 'graph-agent-tasks.json'
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps(queue), encoding='utf-8')
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'propose', '--task-id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['error']['code'], 'proposal_out_of_scope')
                self.assertEqual(payload['error']['details']['path'], 'topics/other.md')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_apply_command_dry_run_does_not_write_content_or_record(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                proposal_path, bundle_path, target = self._write_apply_fixture(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'apply',
                        '--proposal-path',
                        str(proposal_path),
                        '--bundle-path',
                        str(bundle_path),
                        '--dry-run',
                    ])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'apply')
                self.assertTrue(payload['result']['dry_run'])
                self.assertTrue(payload['result']['ready'])
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
                self.assertFalse((kb / 'sorted' / 'graph-patch-applications').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_apply_and_rollback_commands_change_and_restore_content(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                proposal_path, bundle_path, target = self._write_apply_fixture(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'apply',
                        '--proposal-path',
                        str(proposal_path),
                        '--bundle-path',
                        str(bundle_path),
                    ])

                self.assertEqual(raised.exception.code, 0)
                apply_payload = json.loads(stdout.getvalue())
                application_path = apply_payload['result']['artifacts']['application']
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'rollback',
                        '--application-path',
                        application_path,
                        '--dry-run',
                    ])

                self.assertEqual(raised.exception.code, 0)
                dry_run_payload = json.loads(stdout.getvalue())
                self.assertTrue(dry_run_payload['result']['dry_run'])
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'rollback',
                        '--application-path',
                        application_path,
                    ])

                self.assertEqual(raised.exception.code, 0)
                rollback_payload = json.loads(stdout.getvalue())
                self.assertEqual(rollback_payload['command'], 'rollback')
                self.assertEqual(rollback_payload['result']['status'], 'rolled_back')
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_apply_command_patch_errors_are_structured(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                proposal_path, bundle_path, target = self._write_apply_fixture(kb)
                target.write_text('[[Missing]] and [[Missing]].\n', encoding='utf-8')
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'apply',
                        '--proposal-path',
                        str(proposal_path),
                        '--bundle-path',
                        str(bundle_path),
                    ])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'apply')
                self.assertEqual(payload['error']['code'], 'patch_preflight_failed')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_run_task_command_waits_for_missing_bundle(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                self._write_run_task_queue(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'run-task', '--id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'run-task')
                self.assertEqual(payload['result']['schema_version'], 'wikify.agent-task-run.v1')
                self.assertEqual(payload['result']['status'], 'waiting_for_patch_bundle')
                self.assertIn('generate_patch_bundle', payload['result']['next_actions'])
                self.assertEqual(queue['tasks'][0]['status'], 'proposed')
                self.assertTrue((kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_run_task_command_with_bundle_applies_and_marks_done(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                self._write_run_task_queue(kb)
                _, _, target = self._write_apply_fixture(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'run-task', '--id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                self.assertEqual(payload['result']['status'], 'completed')
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
                self.assertEqual(queue['tasks'][0]['status'], 'done')
                self.assertTrue(Path(payload['result']['artifacts']['application']).exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_run_task_command_errors_are_structured(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['WIKIFY_BASE'] = tmpdir
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'run-task', '--id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'run-task')
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

    def test_bundle_request_command_dry_run_writes_nothing(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                self._write_run_task_queue(kb)
                (kb / 'topics').mkdir()
                target = kb / 'topics' / 'a.md'
                target.write_text('See [[Missing]].\n', encoding='utf-8')
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'bundle-request', '--task-id', 'agent-task-1', '--dry-run'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'bundle-request')
                self.assertTrue(payload['result']['dry_run'])
                self.assertEqual(payload['result']['request']['schema_version'], 'wikify.patch-bundle-request.v1')
                self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())
                self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())
                self.assertEqual(queue['tasks'][0]['status'], 'queued')
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_bundle_request_command_writes_request_and_proposal(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                self._write_run_task_queue(kb)
                (kb / 'topics').mkdir()
                target = kb / 'topics' / 'a.md'
                target.write_text('See [[Missing]].\n', encoding='utf-8')
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'bundle-request', '--task-id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                request_path = kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'
                proposal_path = kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json'
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'bundle-request')
                self.assertFalse(payload['result']['dry_run'])
                self.assertTrue(payload['result']['summary']['written'])
                self.assertTrue(request_path.exists())
                self.assertTrue(proposal_path.exists())
                self.assertEqual(queue['tasks'][0]['status'], 'queued')
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')

        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_bundle_request_command_errors_are_structured(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['WIKIFY_BASE'] = tmpdir
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'bundle-request', '--task-id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'bundle-request')
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

    def test_tasks_command_lifecycle_marks_proposed(self):
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
                    cli.main([
                        '--output',
                        'json',
                        'tasks',
                        '--id',
                        'agent-task-1',
                        '--mark-proposed',
                        '--proposal-path',
                        'sorted/graph-patch-proposals/agent-task-1.json',
                    ])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['result']['task']['status'], 'proposed')
                self.assertEqual(queue['tasks'][0]['status'], 'proposed')
                self.assertEqual(events['events'][0]['action'], 'mark_proposed')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_tasks_command_lifecycle_requires_id_and_valid_transition(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                queue = {
                    'schema_version': 'wikify.graph-agent-tasks.v1',
                    'summary': {'task_count': 1},
                    'tasks': [
                        {
                            'id': 'agent-task-1',
                            'source_finding_id': 'done-task',
                            'action': 'queue_link_repair',
                            'priority': 'normal',
                            'target': 'topics/a.md',
                            'evidence': {},
                            'write_scope': ['topics/a.md'],
                            'agent_instructions': [],
                            'acceptance_checks': [],
                            'requires_user': False,
                            'status': 'done',
                        },
                    ],
                }
                target = kb / 'sorted' / 'graph-agent-tasks.json'
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps(queue), encoding='utf-8')
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'tasks', '--start', '--id', 'agent-task-1'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['error']['code'], 'invalid_agent_task_transition')

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'tasks', '--mark-done'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['error']['code'], 'agent_task_id_required')
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
