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

    def _write_json(self, path: Path, document: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

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

    def test_build_parser_accepts_sync_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['sync'])

        self.assertEqual(args.command, 'sync')
        self.assertIsNone(args.source)
        self.assertFalse(args.dry_run)

    def test_build_parser_accepts_sync_source_and_dry_run_options(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['sync', '--source', 'src_abc', '--dry-run'])

        self.assertEqual(args.command, 'sync')
        self.assertEqual(args.source, 'src_abc')
        self.assertTrue(args.dry_run)

    def test_build_parser_accepts_validate_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        default_args = parser.parse_args(['validate'])
        focused_args = parser.parse_args(['validate', '--path', 'topics/intro.md', '--strict', '--write-report'])

        self.assertEqual(default_args.command, 'validate')
        self.assertIsNone(default_args.path)
        self.assertFalse(default_args.strict)
        self.assertEqual(focused_args.command, 'validate')
        self.assertEqual(focused_args.path, 'topics/intro.md')
        self.assertTrue(focused_args.strict)
        self.assertTrue(focused_args.write_report)

    def test_build_parser_accepts_wikiize_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args([
            'wikiize',
            '--dry-run',
            '--queue-id',
            'queue_abc',
            '--item',
            'item_abc',
            '--source',
            'src_abc',
            '--limit',
            '2',
            '--agent-command',
            'python3 agent.py',
            '--timeout',
            '30',
        ])
        profile_args = parser.parse_args(['wikiize', '--agent-profile'])

        self.assertEqual(args.command, 'wikiize')
        self.assertTrue(args.dry_run)
        self.assertEqual(args.queue_id, 'queue_abc')
        self.assertEqual(args.item, 'item_abc')
        self.assertEqual(args.source, 'src_abc')
        self.assertEqual(args.limit, 2)
        self.assertEqual(args.agent_command, 'python3 agent.py')
        self.assertEqual(args.timeout, 30.0)
        self.assertEqual(profile_args.agent_profile, '@default')

    def test_build_parser_accepts_views_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['views', '--dry-run', '--no-html', '--section', 'sources'])

        self.assertEqual(args.command, 'views')
        self.assertTrue(args.dry_run)
        self.assertTrue(args.no_html)
        self.assertEqual(args.section, 'sources')

    def test_build_parser_accepts_agent_export_command(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        args = parser.parse_args(['agent', 'export', '--dry-run', '--max-full-chars', '24000', '--max-page-chars', '3000'])
        profile_args = parser.parse_args(['agent-profile', '--list'])

        self.assertEqual(args.command, 'agent')
        self.assertEqual(args.agent_action, 'export')
        self.assertTrue(args.dry_run)
        self.assertEqual(args.max_full_chars, 24000)
        self.assertEqual(args.max_page_chars, 3000)
        self.assertEqual(profile_args.command, 'agent-profile')

    def test_build_parser_accepts_agent_context_cite_and_related_commands(self):
        cli = importlib.import_module('wikify.cli')

        parser = cli.build_parser()
        context_args = parser.parse_args([
            'agent',
            'context',
            'agent context',
            '--dry-run',
            '--max-chars',
            '800',
            '--max-pages',
            '2',
            '--include-full-pages',
        ])
        cite_args = parser.parse_args(['agent', 'cite', 'Source Title', '--limit', '5'])
        related_args = parser.parse_args(['agent', 'related', 'agent context', '--limit', '5'])

        self.assertEqual(context_args.command, 'agent')
        self.assertEqual(context_args.agent_action, 'context')
        self.assertEqual(context_args.query, 'agent context')
        self.assertTrue(context_args.dry_run)
        self.assertEqual(context_args.max_chars, 800)
        self.assertEqual(context_args.max_pages, 2)
        self.assertTrue(context_args.include_full_pages)
        self.assertEqual(cite_args.agent_action, 'cite')
        self.assertEqual(cite_args.query, 'Source Title')
        self.assertEqual(cite_args.limit, 5)
        self.assertEqual(related_args.agent_action, 'related')
        self.assertEqual(related_args.target, 'agent context')
        self.assertEqual(related_args.limit, 5)

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

    def test_validate_command_returns_success_for_legacy_markdown_warnings(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                topics = base / 'topics'
                topics.mkdir()
                (topics / 'legacy.md').write_text('# Legacy\n', encoding='utf-8')
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'validate'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'validate')
                self.assertEqual(payload['result']['schema_version'], 'wikify.object-validation.v1')
                self.assertGreater(payload['result']['summary']['warning_count'], 0)
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_validate_command_strict_errors_return_exit_code_2(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                self._write_json(
                    base / 'artifacts' / 'objects' / 'wiki_pages' / 'page_intro.json',
                    {
                        'schema_version': 'wikify.wiki-page.v1',
                        'id': 'page_intro',
                        'type': 'wiki_page',
                        'title': 'Intro',
                        'summary': 'Intro summary',
                    },
                )
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'validate', '--strict'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'validate')
                self.assertEqual(payload['error']['code'], 'object_validation_failed')
                self.assertEqual(payload['error']['details']['validation']['schema_version'], 'wikify.object-validation.v1')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_validate_command_supports_focused_path(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                topics = base / 'topics'
                topics.mkdir()
                (topics / 'intro.md').write_text(
                    '\n'.join([
                        '---',
                        'schema_version: wikify.wiki-page.v1',
                        'id: page_intro',
                        'type: wiki_page',
                        'title: Intro',
                        'summary: Intro summary',
                        'body_path: topics/intro.md',
                        'source_refs: []',
                        'outbound_links: []',
                        'backlinks: []',
                        'created_at: 2026-04-29T00:00:00Z',
                        'updated_at: 2026-04-29T00:00:00Z',
                        'confidence: 0.8',
                        'review_status: generated',
                        '---',
                        '# Intro',
                        '',
                    ]),
                    encoding='utf-8',
                )
                (topics / 'other.md').write_text('# Other\n', encoding='utf-8')
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'validate', '--path', 'topics/intro.md'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['result']['schema_version'], 'wikify.object-validation.v1')
                self.assertTrue(payload['result']['path'].endswith('topics/intro.md'))
                self.assertEqual(payload['result']['summary']['object_count'], 1)
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_sync_command_dry_run_returns_json_without_writing_artifacts(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.sync import source_items_path
        from wikify.workspace import add_source, initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Note\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'sync', '--dry-run'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'sync')
                self.assertTrue(payload['result']['dry_run'])
                self.assertFalse(source_items_path(base).exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_sync_command_writes_artifacts_and_reports_new_items(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.sync import source_items_path, sync_report_path, ingest_queue_path
        from wikify.workspace import add_source, initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Note\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'sync'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'sync')
                self.assertEqual(payload['result']['summary']['item_status_counts']['new'], 1)
                self.assertTrue(source_items_path(base).is_file())
                self.assertTrue(sync_report_path(base).is_file())
                self.assertTrue(ingest_queue_path(base).is_file())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_sync_command_missing_source_returns_structured_error(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'sync', '--source', 'src_missing'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'sync')
                self.assertEqual(payload['error']['code'], 'sync_source_not_found')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_wikiize_command_dry_run_returns_json_without_writing_pages(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.sync import sync_workspace
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import wiki_pages_dir, wikiize_report_path

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Note\n\nQueued source.\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                sync_workspace(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'wikiize', '--dry-run'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'wikiize')
                self.assertTrue(payload['result']['dry_run'])
                self.assertEqual(payload['result']['summary']['planned_count'], 1)
                self.assertFalse(wiki_pages_dir(base).exists())
                self.assertFalse(wikiize_report_path(base).exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_wikiize_command_writes_generated_page_and_object(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.sync import sync_workspace
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import wikiize_report_path

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Note\n\nQueued source.\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                sync_workspace(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'wikiize'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'wikiize')
                self.assertEqual(payload['result']['summary']['completed_count'], 1)
                body_path = base / payload['result']['items'][0]['paths']['body_path']
                object_path = base / payload['result']['items'][0]['paths']['object_path']
                self.assertTrue(body_path.is_file())
                self.assertTrue(object_path.is_file())
                self.assertTrue(wikiize_report_path(base).is_file())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_wikiize_command_missing_artifacts_returns_structured_error(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'wikiize'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'wikiize')
                self.assertEqual(payload['error']['code'], 'wikiize_source_items_missing')
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_agent_export_command_dry_run_returns_json_without_writing_artifacts(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.agent import agent_report_path, page_index_path
        from wikify.sync import sync_workspace
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import run_wikiization

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Source Title\n\nAgent Context source.\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                sync_workspace(base)
                run_wikiization(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'agent', 'export', '--dry-run'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'agent.export')
                self.assertEqual(payload['result']['schema_version'], 'wikify.agent-export.v1')
                self.assertTrue(payload['result']['dry_run'])
                self.assertFalse((base / 'llms.txt').exists())
                self.assertFalse(page_index_path(base).exists())
                self.assertFalse(agent_report_path(base).exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_agent_export_command_writes_json_artifacts(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.sync import sync_workspace
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import run_wikiization

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Source Title\n\nAgent Context source.\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                sync_workspace(base)
                run_wikiization(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'agent', 'export'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'agent.export')
                self.assertTrue((base / 'llms.txt').is_file())
                self.assertIn('artifacts/agent/page-index.json', payload['result']['completion']['artifacts'])
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_agent_export_command_validation_errors_return_exit_code_2(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                self._write_json(
                    base / 'artifacts' / 'objects' / 'wiki_pages' / 'page_bad.json',
                    {
                        'schema_version': 'wikify.wiki-page.v1',
                        'id': 'page_bad',
                        'type': 'wiki_page',
                        'title': 'Bad',
                    },
                )
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'agent', 'export'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'agent.export')
                self.assertIn(payload['error']['code'], {'agent_validation_failed', 'agent_object_invalid'})
                self.assertFalse((base / 'llms.txt').exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_agent_context_command_writes_context_pack(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.agent import context_pack_dir
        from wikify.sync import sync_workspace
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import run_wikiization

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Source Title\n\nAgent Context source for query packs.\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                sync_workspace(base)
                run_wikiization(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'agent', 'context', 'agent context', '--dry-run', '--max-chars', '800'])

                self.assertEqual(raised.exception.code, 0)
                dry_payload = json.loads(stdout.getvalue())
                self.assertTrue(dry_payload['ok'])
                self.assertEqual(dry_payload['command'], 'agent.context')
                self.assertFalse(context_pack_dir(base).exists())

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'agent', 'context', 'agent context', '--max-chars', '800'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'agent.context')
                self.assertTrue(context_pack_dir(base).is_dir())
                artifacts = payload['result']['completion']['artifacts']
                self.assertTrue(any(path.startswith('artifacts/agent/context-packs/') for path in artifacts))
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_agent_cite_and_related_commands_return_json(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.objects import (
            make_citation_object,
            make_object_index,
            make_topic_object,
            object_document_path,
            object_index_path,
        )
        from wikify.sync import sync_workspace
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import run_wikiization

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Source Title\n\nAgent Context source for query packs.\n', encoding='utf-8')
                source = add_source(base, str(note), 'file')['source']
                sync_result = sync_workspace(base)
                item = sync_result['items'][0]
                run_wikiization(base)
                page_path = next((base / 'artifacts' / 'objects' / 'wiki_pages').glob('*.json'))
                page = json.loads(page_path.read_text(encoding='utf-8'))
                page['outbound_links'] = ['topic_agent_context']
                page_path.write_text(json.dumps(page, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                source_refs = [{
                    'source_id': source['source_id'],
                    'item_id': item['item_id'],
                    'locator': item.get('locator'),
                    'relative_path': item.get('relative_path'),
                    'confidence': 0.9,
                }]
                topic = make_topic_object(
                    object_id='topic_agent_context',
                    title='Agent Context',
                    summary='Durable context for agents.',
                    page_ids=[page['id']],
                    source_refs=source_refs,
                )
                citation = make_citation_object(
                    object_id='citation_source_title',
                    source_id=source['source_id'],
                    item_id=item['item_id'],
                    locator='sources/note.md#L1',
                    confidence=0.9,
                    snippet='Source Title',
                )
                self._write_json(object_document_path(base, 'topic', topic['id']), topic)
                self._write_json(object_document_path(base, 'citation', citation['id']), citation)
                self._write_json(object_index_path(base), make_object_index(base, [page, topic, citation]))
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'agent', 'cite', 'Source Title'])

                self.assertEqual(raised.exception.code, 0)
                cite_payload = json.loads(stdout.getvalue())
                self.assertTrue(cite_payload['ok'])
                self.assertEqual(cite_payload['command'], 'agent.cite')
                self.assertGreater(len(cite_payload['result']['evidence']), 0)

                stdout = io.StringIO()
                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'agent', 'related', 'agent context'])

                self.assertEqual(raised.exception.code, 0)
                related_payload = json.loads(stdout.getvalue())
                self.assertTrue(related_payload['ok'])
                self.assertEqual(related_payload['command'], 'agent.related')
                self.assertGreater(len(related_payload['result']['related']), 0)
                self.assertIn('signals', related_payload['result']['related'][0])
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_views_command_dry_run_returns_json_without_writing_views(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.sync import sync_workspace
        from wikify.views import views_manifest_path, views_report_path
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import run_wikiization

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Note\n\nQueued source.\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                sync_workspace(base)
                run_wikiization(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'views', '--dry-run', '--no-html'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'views')
                self.assertTrue(payload['result']['dry_run'])
                self.assertEqual(payload['result']['summary']['planned_html_count'], 0)
                self.assertIn('views/index.md', {view['path'] for view in payload['result']['views']})
                self.assertFalse((base / 'views' / 'index.md').exists())
                self.assertFalse(views_report_path(base).exists())
                self.assertFalse(views_manifest_path(base).exists())
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_views_command_writes_markdown_html_and_reports(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.sync import sync_workspace
        from wikify.views import views_manifest_path, views_report_path
        from wikify.workspace import add_source, initialize_workspace
        from wikify.wikiize import run_wikiization

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                note = base / 'sources' / 'note.md'
                note.write_text('# Note\n\nQueued source.\n', encoding='utf-8')
                add_source(base, str(note), 'file')
                sync_workspace(base)
                run_wikiization(base)
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'views'])

                self.assertEqual(raised.exception.code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload['ok'])
                self.assertEqual(payload['command'], 'views')
                self.assertEqual(payload['result']['status'], 'completed')
                self.assertEqual(payload['result']['summary']['generated_view_count'], len(payload['result']['views']))
                self.assertTrue((base / 'views' / 'index.md').is_file())
                self.assertTrue((base / 'views' / 'site' / 'index.html').is_file())
                self.assertTrue(views_report_path(base).is_file())
                self.assertTrue(views_manifest_path(base).is_file())
                self.assertIn('views/index.md', payload['result']['completion']['artifacts'])
                self.assertIn('views/site/index.html', payload['result']['completion']['artifacts'])
        finally:
            if original_wikify is None:
                os.environ.pop('WIKIFY_BASE', None)
            else:
                os.environ['WIKIFY_BASE'] = original_wikify
            if original_fokb is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original_fokb

    def test_views_command_validation_errors_return_exit_code_2(self):
        cli = importlib.import_module('wikify.cli')
        from wikify.workspace import initialize_workspace

        original_wikify = os.environ.get('WIKIFY_BASE')
        original_fokb = os.environ.get('FOKB_BASE')
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                base = Path(tmpdir) / 'personal-wiki'
                initialize_workspace(base)
                self._write_json(
                    base / 'artifacts' / 'objects' / 'wiki_pages' / 'page_bad.json',
                    {
                        'schema_version': 'wikify.wiki-page.v1',
                        'id': 'page_bad',
                        'type': 'wiki_page',
                        'title': 'Bad',
                    },
                )
                os.environ['WIKIFY_BASE'] = str(base)
                os.environ.pop('FOKB_BASE', None)
                stdout = io.StringIO()

                with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
                    cli.main(['--output', 'json', 'views'])

                self.assertEqual(raised.exception.code, 2)
                payload = json.loads(stdout.getvalue())
                self.assertFalse(payload['ok'])
                self.assertEqual(payload['command'], 'views')
                self.assertEqual(payload['error']['code'], 'views_validation_failed')
                self.assertEqual(payload['error']['details']['validation']['schema_version'], 'wikify.object-validation.v1')
                self.assertFalse((base / 'views' / 'index.md').exists())
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
