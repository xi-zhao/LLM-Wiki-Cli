import importlib
import io
import json
import os
import shutil
import sys
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

    def _write_bundle_request_fixture(self, kb: Path):
        from wikify.maintenance.bundle_request import build_bundle_request, write_bundle_request
        from wikify.maintenance.proposal import write_patch_proposal

        self._write_run_task_queue(kb)
        (kb / 'topics').mkdir()
        target = kb / 'topics' / 'a.md'
        target.write_text('See [[Missing]].\n', encoding='utf-8')
        request = build_bundle_request(kb, 'agent-task-1')
        write_patch_proposal(kb, request['proposal'])
        request_path = write_bundle_request(kb, request)
        return request_path, target

    def _write_stdout_bundle_agent(self, kb: Path):
        script = kb / 'stdout_bundle_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": "sorted/graph-patch-proposals/agent-task-1.json",',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": "topics/a.md",',
                '            "find": "[[Missing]]",',
                '            "replace": "[[Existing]]",',
                '            "rationale": "resolve broken wikilink"',
                '        }',
                '    ]',
                '}',
                'print(json.dumps(bundle))',
            ]),
            encoding='utf-8',
        )
        return script

    def _write_sample_link_repair_agent(self, kb: Path):
        script = kb / 'sample_link_repair_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'target = request["targets"][0]',
                'edit = request["proposal"]["planned_edits"][0]',
                'missing = edit["evidence"]["target"]',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": request["proposal_path"],',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": target["path"],',
                '            "find": f"[[{missing}]]",',
                '            "replace": "[[agent-knowledge-loops]]",',
                '            "rationale": "resolve sample broken wikilink"',
                '        }',
                '    ]',
                '}',
                'print(json.dumps(bundle))',
            ]),
            encoding='utf-8',
        )
        return script

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

    def test_build_parser_accepts_produce_bundle_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'produce-bundle',
            '--request-path',
            'sorted/graph-patch-bundle-requests/agent-task-1.json',
            '--agent-command',
            'python3 agent.py',
            '--timeout',
            '30',
            '--dry-run',
        ])

        self.assertEqual(args.command, 'produce-bundle')
        self.assertEqual(args.request_path, 'sorted/graph-patch-bundle-requests/agent-task-1.json')
        self.assertEqual(args.agent_command, 'python3 agent.py')
        self.assertEqual(args.timeout, 30.0)
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_verify_bundle_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'verify-bundle',
            '--proposal-path',
            'sorted/graph-patch-proposals/agent-task-1.json',
            '--bundle-path',
            'sorted/graph-patch-bundles/agent-task-1.json',
            '--verifier-command',
            'python3 verifier.py',
            '--verifier-timeout',
            '30',
            '--dry-run',
        ])

        self.assertEqual(args.command, 'verify-bundle')
        self.assertEqual(args.proposal_path, 'sorted/graph-patch-proposals/agent-task-1.json')
        self.assertEqual(args.bundle_path, 'sorted/graph-patch-bundles/agent-task-1.json')
        self.assertEqual(args.verifier_command, 'python3 verifier.py')
        self.assertEqual(args.verifier_timeout, 30.0)
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
            '--agent-command',
            'python3 agent.py',
            '--verifier-command',
            'python3 verifier.py',
            '--producer-timeout',
            '30',
            '--verifier-timeout',
            '45',
            '--dry-run',
        ])

        self.assertEqual(args.command, 'run-task')
        self.assertEqual(args.id, 'agent-task-1')
        self.assertEqual(args.agent_command, 'python3 agent.py')
        self.assertEqual(args.verifier_command, 'python3 verifier.py')
        self.assertEqual(args.producer_timeout, 30.0)
        self.assertEqual(args.verifier_timeout, 45.0)
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_run_tasks_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'run-tasks',
            '--status',
            'queued',
            '--action',
            'queue_link_repair',
            '--id',
            'agent-task-1',
            '--limit',
            '3',
            '--agent-command',
            'python3 agent.py',
            '--verifier-command',
            'python3 verifier.py',
            '--producer-timeout',
            '30',
            '--verifier-timeout',
            '45',
            '--continue-on-error',
            '--dry-run',
        ])

        self.assertEqual(args.command, 'run-tasks')
        self.assertEqual(args.status, 'queued')
        self.assertEqual(args.action, 'queue_link_repair')
        self.assertEqual(args.id, 'agent-task-1')
        self.assertEqual(args.limit, 3)
        self.assertEqual(args.agent_command, 'python3 agent.py')
        self.assertEqual(args.verifier_command, 'python3 verifier.py')
        self.assertEqual(args.producer_timeout, 30.0)
        self.assertEqual(args.verifier_timeout, 45.0)
        self.assertTrue(args.continue_on_error)
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_maintain_run_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'maintain-run',
            '--policy',
            'balanced',
            '--status',
            'queued',
            '--action',
            'queue_link_repair',
            '--id',
            'agent-task-1',
            '--limit',
            '3',
            '--agent-command',
            'python3 agent.py',
            '--verifier-command',
            'python3 verifier.py',
            '--producer-timeout',
            '30',
            '--verifier-timeout',
            '45',
            '--continue-on-error',
            '--dry-run',
        ])

        self.assertEqual(args.command, 'maintain-run')
        self.assertEqual(args.policy, 'balanced')
        self.assertEqual(args.status, 'queued')
        self.assertEqual(args.action, 'queue_link_repair')
        self.assertEqual(args.id, 'agent-task-1')
        self.assertEqual(args.limit, 3)
        self.assertEqual(args.agent_command, 'python3 agent.py')
        self.assertEqual(args.verifier_command, 'python3 verifier.py')
        self.assertEqual(args.producer_timeout, 30.0)
        self.assertEqual(args.verifier_timeout, 45.0)
        self.assertTrue(args.continue_on_error)
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_maintain_loop_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'maintain-loop',
            '--policy',
            'balanced',
            '--status',
            'queued',
            '--action',
            'queue_link_repair',
            '--id',
            'agent-task-1',
            '--limit',
            '3',
            '--max-rounds',
            '4',
            '--task-budget',
            '12',
            '--agent-command',
            'python3 agent.py',
            '--verifier-command',
            'python3 verifier.py',
            '--producer-timeout',
            '30',
            '--verifier-timeout',
            '45',
            '--continue-on-error',
            '--dry-run',
        ])

        self.assertEqual(args.command, 'maintain-loop')
        self.assertEqual(args.policy, 'balanced')
        self.assertEqual(args.status, 'queued')
        self.assertEqual(args.action, 'queue_link_repair')
        self.assertEqual(args.id, 'agent-task-1')
        self.assertEqual(args.limit, 3)
        self.assertEqual(args.max_rounds, 4)
        self.assertEqual(args.task_budget, 12)
        self.assertEqual(args.agent_command, 'python3 agent.py')
        self.assertEqual(args.verifier_command, 'python3 verifier.py')
        self.assertEqual(args.producer_timeout, 30.0)
        self.assertEqual(args.verifier_timeout, 45.0)
        self.assertTrue(args.continue_on_error)
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_agent_profile_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        set_args = parser.parse_args([
            'agent-profile',
            '--set',
            'default',
            '--agent-command',
            'python3 agent.py',
            '--producer-timeout',
            '30',
            '--description',
            'local adapter',
        ])
        list_args = parser.parse_args(['agent-profile', '--list'])
        show_args = parser.parse_args(['agent-profile', '--show', 'default'])
        unset_args = parser.parse_args(['agent-profile', '--unset', 'default'])
        set_default_args = parser.parse_args(['agent-profile', '--set-default', 'default'])
        show_default_args = parser.parse_args(['agent-profile', '--show-default'])
        clear_default_args = parser.parse_args(['agent-profile', '--clear-default'])

        self.assertEqual(set_args.command, 'agent-profile')
        self.assertEqual(set_args.set, 'default')
        self.assertEqual(set_args.agent_command, 'python3 agent.py')
        self.assertEqual(set_args.producer_timeout, 30.0)
        self.assertEqual(set_args.description, 'local adapter')
        self.assertTrue(list_args.list)
        self.assertEqual(show_args.show, 'default')
        self.assertEqual(unset_args.unset, 'default')
        self.assertEqual(set_default_args.set_default, 'default')
        self.assertTrue(show_default_args.show_default)
        self.assertTrue(clear_default_args.clear_default)

    def test_build_parser_accepts_agent_profile_on_automation_commands(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        produce_args = parser.parse_args([
            'produce-bundle',
            '--request-path',
            'sorted/graph-patch-bundle-requests/agent-task-1.json',
            '--agent-profile',
            'default',
        ])
        run_task_args = parser.parse_args(['run-task', '--id', 'agent-task-1', '--agent-profile', 'default'])
        run_tasks_args = parser.parse_args(['run-tasks', '--agent-profile', 'default'])
        maintain_run_args = parser.parse_args(['maintain-run', '--agent-profile', 'default'])
        maintain_loop_args = parser.parse_args(['maintain-loop', '--agent-profile', 'default'])
        verify_args = parser.parse_args([
            'verify-bundle',
            '--proposal-path',
            'sorted/graph-patch-proposals/agent-task-1.json',
            '--bundle-path',
            'sorted/graph-patch-bundles/agent-task-1.json',
            '--verifier-profile',
            'reviewer',
        ])
        bare_profile_args = parser.parse_args(['maintain-run', '--agent-profile'])
        bare_loop_profile_args = parser.parse_args(['maintain-loop', '--agent-profile'])
        bare_verifier_profile_args = parser.parse_args([
            'run-task',
            '--id',
            'agent-task-1',
            '--verifier-profile',
        ])

        self.assertEqual(produce_args.agent_profile, 'default')
        self.assertEqual(run_task_args.agent_profile, 'default')
        self.assertEqual(run_tasks_args.agent_profile, 'default')
        self.assertEqual(maintain_run_args.agent_profile, 'default')
        self.assertEqual(maintain_loop_args.agent_profile, 'default')
        self.assertEqual(verify_args.verifier_profile, 'reviewer')
        self.assertEqual(bare_profile_args.agent_profile, '@default')
        self.assertEqual(bare_loop_profile_args.agent_profile, '@default')
        self.assertEqual(bare_verifier_profile_args.verifier_profile, '@default')

    def test_build_parser_accepts_workspace_and_source_commands(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        init_args = parser.parse_args(['init', '/tmp/personal-wiki'])
        add_args = parser.parse_args(['source', 'add', 'https://example.com/a', '--type', 'url'])
        list_args = parser.parse_args(['source', 'list'])
        show_args = parser.parse_args(['source', 'show', 'src_123'])

        self.assertEqual(init_args.command, 'init')
        self.assertEqual(init_args.base, '/tmp/personal-wiki')
        self.assertEqual(add_args.command, 'source')
        self.assertEqual(add_args.source_action, 'add')
        self.assertEqual(add_args.locator, 'https://example.com/a')
        self.assertEqual(add_args.type, 'url')
        self.assertEqual(list_args.source_action, 'list')
        self.assertEqual(show_args.source_action, 'show')
        self.assertEqual(show_args.target, 'src_123')

    def test_init_command_creates_workspace_without_hidden_pipeline_outputs(self):
        cli = importlib.import_module('wikify.cli')

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / 'personal-wiki'
            stdout = io.StringIO()

            with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                cli.main(['--output', 'json', 'init', str(base)])

            self.assertEqual(raised.exception.code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload['ok'])
            self.assertEqual(payload['command'], 'init')
            self.assertEqual(payload['result']['workspace']['schema_version'], 'wikify.workspace.v1')
            self.assertTrue((base / 'wikify.json').exists())
            self.assertTrue((base / '.wikify' / 'registry' / 'sources.json').exists())
            self.assertTrue((base / 'sources').is_dir())
            self.assertTrue((base / 'wiki').is_dir())
            self.assertTrue((base / 'artifacts').is_dir())
            self.assertTrue((base / 'views').is_dir())
            self.assertFalse((base / 'graph').exists())
            self.assertFalse((base / 'sorted').exists())

    def test_source_add_requires_initialized_workspace(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['WIKIFY_BASE'] = tmpdir
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'source', 'add', 'missing.md', '--type', 'file'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'source.add')
                self.assertEqual(payload['error']['code'], 'workspace_missing')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_source_commands_add_list_and_show_registry_records(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                note = base / 'sources' / 'note.md'

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'init', str(base)])
                self.assertEqual(raised.exception.code, 0)

                note.write_text('# Note\n', encoding='utf-8')
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'source', 'add', str(note), '--type', 'file'])
                self.assertEqual(raised.exception.code, 0)
                add_payload = json.loads(stdout.getvalue())
                self.assertEqual(add_payload['command'], 'source.add')
                self.assertEqual(add_payload['result']['status'], 'added')
                self.assertEqual(add_payload['result']['source']['last_sync_status'], 'never_synced')
                source_id = add_payload['result']['source']['source_id']

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'source', 'add', str(note), '--type', 'file'])
                self.assertEqual(raised.exception.code, 0)
                duplicate_payload = json.loads(stdout.getvalue())
                self.assertEqual(duplicate_payload['result']['status'], 'existing')
                self.assertEqual(duplicate_payload['result']['source']['source_id'], source_id)

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'source', 'list'])
                self.assertEqual(raised.exception.code, 0)
                list_payload = json.loads(stdout.getvalue())
                self.assertEqual(list_payload['command'], 'source.list')
                self.assertEqual(list_payload['result']['summary']['source_count'], 1)
                self.assertEqual(list_payload['result']['sources'][0]['source_id'], source_id)

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'source', 'show', source_id])
                self.assertEqual(raised.exception.code, 0)
                show_payload = json.loads(stdout.getvalue())
                self.assertEqual(show_payload['command'], 'source.show')
                self.assertEqual(show_payload['result']['source']['source_id'], source_id)
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

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
                (kb / 'topics').mkdir()
                (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')
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
                self.assertTrue((kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json').exists())
                self.assertEqual(
                    payload['result']['artifacts']['patch_bundle_request'],
                    str(kb.resolve() / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'),
                )
                self.assertEqual(
                    payload['result']['summary']['suggested_bundle_path'],
                    str(kb.resolve() / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'),
                )
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

    def test_run_task_command_with_agent_command_produces_applies_and_marks_done(self):
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
                script = self._write_stdout_bundle_agent(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'run-task',
                        '--id',
                        'agent-task-1',
                        '--agent-command',
                        f'{sys.executable} {script}',
                        '--producer-timeout',
                        '30',
                    ])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                self.assertEqual(payload['result']['status'], 'completed')
                self.assertIn('bundle_producer', [step['name'] for step in payload['result']['steps']])
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
                self.assertTrue((kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json').exists())
                self.assertTrue((kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json').exists())
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

    def test_run_tasks_command_with_agent_command_processes_selected_tasks(self):
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
                script = self._write_stdout_bundle_agent(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'run-tasks',
                        '--limit',
                        '1',
                        '--agent-command',
                        f'{sys.executable} {script}',
                    ])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                self.assertEqual(payload['command'], 'run-tasks')
                self.assertEqual(payload['result']['schema_version'], 'wikify.agent-task-batch-run.v1')
                self.assertEqual(payload['result']['status'], 'completed')
                self.assertEqual(payload['result']['summary']['selected_count'], 1)
                self.assertEqual(payload['result']['summary']['completed_count'], 1)
                self.assertEqual(payload['result']['items'][0]['task_id'], 'agent-task-1')
                self.assertTrue(payload['result']['items'][0]['ok'])
                self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
                self.assertEqual(queue['tasks'][0]['status'], 'done')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_maintain_run_command_with_agent_command_refreshes_and_processes_selected_tasks(self):
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
                script = self._write_sample_link_repair_agent(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'maintain-run',
                        '--action',
                        'queue_link_repair',
                        '--limit',
                        '1',
                        '--agent-command',
                        f'{sys.executable} {script}',
                    ])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                target = kb / 'topics' / 'topics-moc.md'
                self.assertEqual(payload['command'], 'maintain-run')
                self.assertEqual(payload['result']['schema_version'], 'wikify.maintenance-run.v1')
                self.assertEqual(payload['result']['status'], 'completed')
                self.assertEqual(payload['result']['batch']['summary']['selected_count'], 1)
                self.assertEqual(payload['result']['batch']['summary']['completed_count'], 1)
                self.assertEqual(queue['tasks'][0]['status'], 'done')
                self.assertIn('[[agent-knowledge-loops]]', target.read_text(encoding='utf-8'))
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_agent_profile_command_sets_profile_and_maintain_run_uses_it(self):
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
                script = self._write_sample_link_repair_agent(kb)
                set_stdout = io.StringIO()
                run_stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(set_stdout):
                    cli.main([
                        '--output',
                        'json',
                        'agent-profile',
                        '--set',
                        'default',
                        '--agent-command',
                        f'{sys.executable} {script}',
                        '--producer-timeout',
                        '30',
                    ])
                self.assertEqual(raised.exception.code, 0)

                with self.assertRaises(SystemExit) as raised, redirect_stdout(run_stdout):
                    cli.main([
                        '--output',
                        'json',
                        'maintain-run',
                        '--action',
                        'queue_link_repair',
                        '--limit',
                        '1',
                        '--agent-profile',
                        'default',
                    ])

                set_payload = json.loads(set_stdout.getvalue())
                run_payload = json.loads(run_stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                self.assertTrue(set_payload['ok'])
                self.assertEqual(set_payload['result']['profile']['name'], 'default')
                self.assertEqual(run_payload['result']['status'], 'completed')
                self.assertEqual(run_payload['result']['execution']['agent_profile'], 'default')
                self.assertEqual(queue['tasks'][0]['status'], 'done')
                self.assertTrue((kb / 'wikify-agent-profiles.json').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_default_agent_profile_can_be_used_with_bare_agent_profile_flag(self):
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
                script = self._write_sample_link_repair_agent(kb)
                run_stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised:
                    cli.main([
                        '--output',
                        'quiet',
                        'agent-profile',
                        '--set',
                        'default',
                        '--agent-command',
                        f'{sys.executable} {script}',
                        '--producer-timeout',
                        '30',
                    ])
                self.assertEqual(raised.exception.code, 0)
                with self.assertRaises(SystemExit) as raised:
                    cli.main(['--output', 'quiet', 'agent-profile', '--set-default', 'default'])
                self.assertEqual(raised.exception.code, 0)

                with self.assertRaises(SystemExit) as raised, redirect_stdout(run_stdout):
                    cli.main([
                        '--output',
                        'json',
                        'maintain-run',
                        '--action',
                        'queue_link_repair',
                        '--limit',
                        '1',
                        '--agent-profile',
                    ])

                payload = json.loads(run_stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                profile_doc = json.loads((kb / 'wikify-agent-profiles.json').read_text(encoding='utf-8'))
                self.assertEqual(raised.exception.code, 0)
                self.assertEqual(profile_doc['default_profile'], 'default')
                self.assertEqual(payload['result']['status'], 'completed')
                self.assertEqual(payload['result']['execution']['agent_profile'], 'default')
                self.assertEqual(queue['tasks'][0]['status'], 'done')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_maintain_loop_command_uses_bare_default_profile_until_no_tasks(self):
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
                script = self._write_sample_link_repair_agent(kb)
                run_stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised:
                    cli.main([
                        '--output',
                        'quiet',
                        'agent-profile',
                        '--set',
                        'default',
                        '--agent-command',
                        f'{sys.executable} {script}',
                    ])
                self.assertEqual(raised.exception.code, 0)
                with self.assertRaises(SystemExit) as raised:
                    cli.main(['--output', 'quiet', 'agent-profile', '--set-default', 'default'])
                self.assertEqual(raised.exception.code, 0)

                with self.assertRaises(SystemExit) as raised, redirect_stdout(run_stdout):
                    cli.main([
                        '--output',
                        'json',
                        'maintain-loop',
                        '--action',
                        'queue_link_repair',
                        '--limit',
                        '1',
                        '--max-rounds',
                        '3',
                        '--task-budget',
                        '3',
                        '--agent-profile',
                    ])

                payload = json.loads(run_stdout.getvalue())
                queue = json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))
                target = kb / 'topics' / 'topics-moc.md'
                self.assertEqual(raised.exception.code, 0)
                self.assertEqual(payload['command'], 'maintain-loop')
                self.assertEqual(payload['result']['schema_version'], 'wikify.maintenance-loop.v1')
                self.assertEqual(payload['result']['status'], 'completed')
                self.assertEqual(payload['result']['stop_reason'], 'no_tasks')
                self.assertEqual(payload['result']['summary']['round_count'], 2)
                self.assertEqual(payload['result']['execution']['agent_profile'], 'default')
                self.assertEqual([task for task in queue['tasks'] if task['action'] == 'queue_link_repair'], [])
                self.assertIn('[[agent-knowledge-loops]]', target.read_text(encoding='utf-8'))
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_bare_agent_profile_without_default_is_structured_error(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['WIKIFY_BASE'] = tmpdir
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'maintain-run', '--agent-profile'])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(raised.exception.code, 2)
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'maintain-run')
                self.assertEqual(payload['error']['code'], 'agent_profile_config_missing')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_agent_command_and_profile_conflict_is_structured(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.environ['WIKIFY_BASE'] = tmpdir
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'produce-bundle',
                        '--request-path',
                        'missing.json',
                        '--agent-command',
                        'python3 agent.py',
                        '--agent-profile',
                        'default',
                    ])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(raised.exception.code, 2)
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'produce-bundle')
                self.assertEqual(payload['error']['code'], 'agent_profile_ambiguous')
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
                self.assertEqual(payload['result']['suggested_bundle_path'], str(kb.resolve() / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'))
                self.assertNotIn('suggested_patch_bundle', payload['result']['artifacts'])
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

    def test_produce_bundle_command_writes_stdout_bundle(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                request_path, target = self._write_bundle_request_fixture(kb)
                script = self._write_stdout_bundle_agent(kb)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'produce-bundle',
                        '--request-path',
                        str(request_path),
                        '--agent-command',
                        f'{sys.executable} {script}',
                    ])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                bundle_path = kb.resolve() / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'produce-bundle')
                self.assertEqual(payload['result']['status'], 'bundle_ready')
                self.assertEqual(payload['result']['artifacts']['patch_bundle'], str(bundle_path))
                self.assertTrue(bundle_path.exists())
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

    def test_produce_bundle_command_dry_run_does_not_execute(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                request_path, _ = self._write_bundle_request_fixture(kb)
                sentinel = kb / 'sentinel.txt'
                script = kb / 'sentinel_agent.py'
                script.write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("ran")\n', encoding='utf-8')
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'produce-bundle',
                        '--request-path',
                        str(request_path),
                        '--agent-command',
                        f'{sys.executable} {script}',
                        '--dry-run',
                    ])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload['result']['status'], 'dry_run')
                self.assertFalse(payload['result']['executed'])
                self.assertFalse(sentinel.exists())
                self.assertFalse((kb / 'sorted' / 'graph-patch-bundles').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_produce_bundle_command_errors_are_structured(self):
        cli = importlib.import_module('wikify.cli')
        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                kb = Path(tmpdir)
                os.environ['WIKIFY_BASE'] = str(kb)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main([
                        '--output',
                        'json',
                        'produce-bundle',
                        '--request-path',
                        'sorted/graph-patch-bundle-requests/missing.json',
                        '--agent-command',
                        f'{sys.executable} missing_agent.py',
                    ])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'produce-bundle')
                self.assertEqual(payload['error']['code'], 'bundle_producer_request_not_found')
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
