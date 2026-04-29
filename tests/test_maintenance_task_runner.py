import json
import sys
import tempfile
import unittest
from pathlib import Path


class MaintenanceTaskRunnerTests(unittest.TestCase):
    def _write_queue(self, kb: Path, status: str = 'queued'):
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
                    'status': status,
                }
            ],
        }
        path = kb / 'sorted' / 'graph-agent-tasks.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(queue), encoding='utf-8')
        return path

    def _write_bundle(self, kb: Path):
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
                    'rationale': 'resolve broken wikilink',
                }
            ],
        }
        path = kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(bundle), encoding='utf-8')
        return path

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
                '    "proposal_path": request["proposal_path"],',
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

    def _write_repair_bundle_agent(self, kb: Path):
        script = kb / 'repair_bundle_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'assert request["repair_context"]["available"] is True',
                'assert request["repair_context"]["feedback"]["summary"] == "rejected"',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": request["proposal_path"],',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": "topics/a.md",',
                '            "find": "[[Missing]]",',
                '            "replace": "[[Existing]]",',
                '            "rationale": "repair verifier rejection"',
                '        }',
                '    ]',
                '}',
                'print(json.dumps(bundle))',
            ]),
            encoding='utf-8',
        )
        return script

    def _write_verifier(self, kb: Path, accepted: bool = True):
        script = kb / ('accept_verifier.py' if accepted else 'reject_verifier.py')
        verdict = {
            'schema_version': 'wikify.patch-bundle-verdict.v1',
            'accepted': accepted,
            'summary': 'accepted' if accepted else 'rejected',
            'findings': [] if accepted else [{'severity': 'high', 'message': 'test rejection'}],
        }
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'assert request["schema_version"] == "wikify.patch-bundle-verification-request.v1"',
                f'print(json.dumps({verdict!r}))',
            ]),
            encoding='utf-8',
        )
        return script

    def _read_queue(self, kb: Path):
        return json.loads((kb / 'sorted' / 'graph-agent-tasks.json').read_text(encoding='utf-8'))

    def _write_rejected_default_bundle(self, kb: Path):
        bundle = {
            'schema_version': 'wikify.patch-bundle.v1',
            'proposal_task_id': 'agent-task-1',
            'proposal_path': 'sorted/graph-patch-proposals/agent-task-1.json',
            'operations': [
                {
                    'operation': 'replace_text',
                    'path': 'topics/a.md',
                    'find': '[[Missing]]',
                    'replace': '[[Rejected]]',
                    'rationale': 'previous rejected repair',
                }
            ],
        }
        path = kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(bundle), encoding='utf-8')
        return path

    def _write_blocked_feedback_queue(self, kb: Path):
        feedback = {
            'source': 'bundle_verifier',
            'reason': 'patch_bundle_verification_rejected',
            'summary': 'rejected',
            'findings': [{'severity': 'high', 'message': 'bad replacement'}],
            'verification_path': str(kb / 'sorted' / 'graph-patch-verifications' / 'agent-task-1.json'),
            'verdict': {'accepted': False, 'summary': 'rejected'},
        }
        self._write_queue(kb, status='blocked')
        queue = self._read_queue(kb)
        queue['tasks'][0]['blocked_feedback'] = feedback
        (kb / 'sorted' / 'graph-agent-tasks.json').write_text(json.dumps(queue), encoding='utf-8')
        return feedback

    def _write_generated_page_assets(self, kb: Path):
        source_refs = [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}]
        (kb / 'wiki' / 'pages').mkdir(parents=True)
        (kb / 'wiki' / 'pages' / 'page_alpha.md').write_text(
            '---\n'
            'body_path: wiki/pages/page_alpha.md\n'
            'id: page_alpha\n'
            'review_status: generated\n'
            'source_refs: [{"source_id": "src_notes", "item_id": "item_alpha", "confidence": 0.9}]\n'
            'type: wiki_page\n'
            '---\n'
            '# Alpha\n\nOriginal body.\n',
            encoding='utf-8',
        )
        object_path = kb / 'artifacts' / 'objects' / 'wiki_pages' / 'page_alpha.json'
        object_path.parent.mkdir(parents=True)
        object_path.write_text(
            json.dumps({
                'schema_version': 'wikify.wiki-page.v1',
                'id': 'page_alpha',
                'type': 'wiki_page',
                'body_path': 'wiki/pages/page_alpha.md',
                'source_refs': source_refs,
                'review_status': 'generated',
            }),
            encoding='utf-8',
        )

    def _write_generated_page_queue(self, kb: Path, status: str = 'queued'):
        queue = {
            'schema_version': 'wikify.graph-agent-tasks.v1',
            'summary': {'task_count': 1},
            'tasks': [
                {
                    'id': 'agent-task-1',
                    'source_finding_id': 'generated-drift',
                    'source_step_id': 'step-1',
                    'action': 'queue_generated_page_repair',
                    'priority': 'high',
                    'target': 'wiki/pages/page_alpha.md',
                    'evidence': {},
                    'write_scope': ['wiki/pages/page_alpha.md'],
                    'object_id': 'page_alpha',
                    'body_path': 'wiki/pages/page_alpha.md',
                    'source_refs': [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}],
                    'review_status': 'generated',
                    'agent_instructions': ['repair generated page'],
                    'acceptance_checks': ['source refs preserved'],
                    'requires_user': False,
                    'status': status,
                }
            ],
        }
        path = kb / 'sorted' / 'graph-agent-tasks.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(queue), encoding='utf-8')
        return path

    def _write_generated_page_unsafe_bundle(self, kb: Path):
        bundle = {
            'schema_version': 'wikify.patch-bundle.v1',
            'proposal_task_id': 'agent-task-1',
            'proposal_path': 'sorted/graph-patch-proposals/agent-task-1.json',
            'operations': [
                {
                    'operation': 'replace_text',
                    'path': 'wiki/pages/page_alpha.md',
                    'find': 'review_status: generated',
                    'replace': 'review_status: approved',
                    'rationale': 'unsafe metadata change',
                }
            ],
        }
        path = kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(bundle), encoding='utf-8')
        return path

    def _write_generated_page_repair_agent(self, kb: Path):
        script = kb / 'generated_page_repair_agent.py'
        script.write_text(
            '\n'.join([
                'import json',
                'import sys',
                'request = json.load(sys.stdin)',
                'assert request["repair_context"]["available"] is True',
                'assert request["safety"]["generated_page_preservation"]["required"] is True',
                'instructions = " ".join(request["agent_instructions"])',
                'assert "source_refs" in instructions',
                'assert "review_status" in instructions',
                'bundle = {',
                '    "schema_version": "wikify.patch-bundle.v1",',
                '    "proposal_task_id": request["task_id"],',
                '    "proposal_path": request["proposal_path"],',
                '    "operations": [',
                '        {',
                '            "operation": "replace_text",',
                '            "path": "wiki/pages/page_alpha.md",',
                '            "find": "Original body.",',
                '            "replace": "Repaired body.",',
                '            "rationale": "repair generated page body"',
                '        }',
                '    ]',
                '}',
                'print(json.dumps(bundle))',
            ]),
            encoding='utf-8',
        )
        return script

    def test_run_agent_task_dry_run_waits_for_bundle_without_writes(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')

            result = run_agent_task(kb, 'agent-task-1', dry_run=True)

            self.assertEqual(result['schema_version'], 'wikify.agent-task-run.v1')
            self.assertTrue(result['dry_run'])
            self.assertEqual(result['status'], 'waiting_for_patch_bundle')
            self.assertIn('generate_patch_bundle', result['next_actions'])
            self.assertEqual(result['artifacts']['patch_bundle_request'], None)
            self.assertEqual(
                result['summary']['bundle_request_path'],
                str(kb.resolve() / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'),
            )
            self.assertEqual(
                result['summary']['suggested_bundle_path'],
                str(kb.resolve() / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'),
            )
            self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())
            self.assertFalse((kb / 'sorted' / 'graph-agent-task-events.json').exists())
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'queued')

    def test_run_agent_task_missing_bundle_writes_proposal_marks_proposed_and_writes_request(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')

            result = run_agent_task(kb, 'agent-task-1')

            proposal_path = kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json'
            request_path = kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'
            expected_request_path = kb.resolve() / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'
            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(result['status'], 'waiting_for_patch_bundle')
            self.assertEqual(result['steps'][0]['name'], 'proposal')
            self.assertEqual(result['steps'][0]['status'], 'written')
            self.assertEqual(result['steps'][1]['name'], 'lifecycle')
            self.assertEqual(result['steps'][1]['status'], 'marked_proposed')
            self.assertEqual(result['steps'][2]['name'], 'bundle_request')
            self.assertEqual(result['steps'][2]['status'], 'written')
            self.assertTrue(proposal_path.exists())
            self.assertTrue(request_path.exists())
            self.assertEqual(result['artifacts']['patch_bundle_request'], str(expected_request_path))
            self.assertEqual(result['summary']['bundle_request_path'], str(expected_request_path))
            self.assertEqual(task['status'], 'proposed')
            self.assertEqual(task['proposal_path'], 'sorted/graph-patch-proposals/agent-task-1.json')
            self.assertEqual(events['events'][0]['action'], 'mark_proposed')

    def test_run_agent_task_bundle_request_failure_keeps_proposed_state(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(kb, 'agent-task-1')

            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(raised.exception.code, 'bundle_request_target_not_found')
            self.assertEqual(raised.exception.details['phase'], 'bundle_request')
            self.assertEqual(raised.exception.details['path'], 'topics/a.md')
            self.assertEqual(task['status'], 'proposed')
            self.assertTrue((kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())

    def test_run_agent_task_with_bundle_applies_patch_and_marks_done(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            self._write_bundle(kb)

            result = run_agent_task(kb, 'agent-task-1')

            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            task = self._read_queue(kb)['tasks'][0]
            application_path = Path(result['artifacts']['application'])
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            self.assertTrue((kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json').exists())
            self.assertTrue(application_path.exists())
            self.assertEqual(task['status'], 'done')
            self.assertEqual([event['action'] for event in events['events']], ['mark_proposed', 'mark_done'])

    def test_run_agent_task_with_verifier_acceptance_applies_patch(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            self._write_bundle(kb)
            verifier = self._write_verifier(kb, accepted=True)

            result = run_agent_task(kb, 'agent-task-1', verifier_command=[sys.executable, str(verifier)])

            self.assertEqual(result['status'], 'completed')
            self.assertIn('bundle_verifier', [step['name'] for step in result['steps']])
            self.assertEqual(result['steps'][-3]['name'], 'bundle_verifier')
            self.assertEqual(result['steps'][-3]['status'], 'accepted')
            self.assertTrue(Path(result['artifacts']['verification']).exists())
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'done')

    def test_run_agent_task_with_verifier_rejection_blocks_apply(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            self._write_bundle(kb)
            verifier = self._write_verifier(kb, accepted=False)

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(kb, 'agent-task-1', verifier_command=[sys.executable, str(verifier)])

            self.assertEqual(raised.exception.code, 'patch_bundle_verification_rejected')
            self.assertEqual(raised.exception.details['phase'], 'bundle_verifier')
            self.assertTrue(Path(raised.exception.details['verification_path']).exists())
            self.assertTrue(Path(raised.exception.details['agent_tasks']).exists())
            self.assertTrue(Path(raised.exception.details['task_events']).exists())
            self.assertEqual(raised.exception.details['verdict']['accepted'], False)
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
            self.assertFalse((kb / 'sorted' / 'graph-patch-applications').exists())
            queue = self._read_queue(kb)
            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            task = queue['tasks'][0]
            feedback = task['blocked_feedback']
            block_event = events['events'][-1]
            self.assertEqual(task['status'], 'blocked')
            self.assertEqual(feedback['source'], 'bundle_verifier')
            self.assertEqual(feedback['summary'], 'rejected')
            self.assertEqual(feedback['verification_path'], raised.exception.details['verification_path'])
            self.assertEqual(feedback['verdict']['accepted'], False)
            self.assertEqual(feedback['findings'], [{'severity': 'high', 'message': 'test rejection'}])
            self.assertEqual([event['action'] for event in events['events']], ['mark_proposed', 'block'])
            self.assertEqual(block_event['details'], feedback)

    def test_run_agent_task_with_agent_command_produces_bundle_applies_and_marks_done(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            script = self._write_stdout_bundle_agent(kb)

            result = run_agent_task(kb, 'agent-task-1', agent_command=[sys.executable, str(script)])

            request_path = kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json'
            bundle_path = kb / 'sorted' / 'graph-patch-bundles' / 'agent-task-1.json'
            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(result['status'], 'completed')
            self.assertIn('bundle_producer', [step['name'] for step in result['steps']])
            self.assertEqual(result['artifacts']['patch_bundle_request'], str(request_path.resolve()))
            self.assertEqual(result['artifacts']['bundle'], str(bundle_path.resolve()))
            self.assertTrue(request_path.exists())
            self.assertTrue(bundle_path.exists())
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            self.assertEqual(task['status'], 'done')
            self.assertEqual([event['action'] for event in events['events']], ['mark_proposed', 'mark_done'])

    def test_run_agent_task_dry_run_with_agent_command_does_not_execute_or_write(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            (kb / 'topics' / 'a.md').write_text('See [[Missing]].\n', encoding='utf-8')
            sentinel = kb / 'sentinel.txt'
            script = kb / 'sentinel_agent.py'
            script.write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("ran")\n', encoding='utf-8')

            result = run_agent_task(kb, 'agent-task-1', dry_run=True, agent_command=[sys.executable, str(script)])

            self.assertEqual(result['status'], 'waiting_for_patch_bundle')
            self.assertIn('bundle_producer', [step['name'] for step in result['steps']])
            self.assertFalse(sentinel.exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-proposals').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundle-requests').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundles').exists())
            self.assertFalse((kb / 'sorted' / 'graph-agent-task-events.json').exists())
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'queued')

    def test_run_agent_task_with_existing_bundle_does_not_execute_agent_command(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            self._write_bundle(kb)
            sentinel = kb / 'sentinel.txt'
            script = kb / 'sentinel_agent.py'
            script.write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("ran")\n', encoding='utf-8')

            result = run_agent_task(kb, 'agent-task-1', agent_command=[sys.executable, str(script)])

            self.assertEqual(result['status'], 'completed')
            self.assertNotIn('bundle_producer', [step['name'] for step in result['steps']])
            self.assertFalse(sentinel.exists())
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'done')

    def test_run_agent_task_repairs_blocked_verifier_task_with_agent_command(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_blocked_feedback_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            rejected_bundle = self._write_rejected_default_bundle(kb)
            agent = self._write_repair_bundle_agent(kb)
            verifier = self._write_verifier(kb, accepted=True)

            result = run_agent_task(
                kb,
                'agent-task-1',
                agent_command=[sys.executable, str(agent)],
                verifier_command=[sys.executable, str(verifier)],
            )

            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            queue = self._read_queue(kb)
            repaired_bundle = json.loads(rejected_bundle.read_text(encoding='utf-8'))
            request = json.loads((kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json').read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'completed')
            self.assertIn('bundle_producer', [step['name'] for step in result['steps']])
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            self.assertEqual(repaired_bundle['operations'][0]['replace'], '[[Existing]]')
            self.assertTrue(request['repair_context']['available'])
            self.assertEqual(queue['tasks'][0]['status'], 'done')
            self.assertNotIn('blocked_feedback', queue['tasks'][0])
            self.assertEqual([event['action'] for event in events['events']], ['retry', 'mark_proposed', 'mark_done'])

    def test_run_agent_task_repairs_retried_verifier_task_from_event_feedback(self):
        from wikify.maintenance.task_lifecycle import apply_lifecycle_action
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb, status='proposed')
            feedback = {
                'source': 'bundle_verifier',
                'summary': 'rejected',
                'findings': [{'severity': 'high', 'message': 'bad replacement'}],
                'verification_path': str(kb / 'sorted' / 'graph-patch-verifications' / 'agent-task-1.json'),
                'verdict': {'accepted': False, 'summary': 'rejected'},
            }
            apply_lifecycle_action(kb, 'agent-task-1', 'block', details=feedback)
            apply_lifecycle_action(kb, 'agent-task-1', 'retry')
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            rejected_bundle = self._write_rejected_default_bundle(kb)
            agent = self._write_repair_bundle_agent(kb)
            verifier = self._write_verifier(kb, accepted=True)

            result = run_agent_task(
                kb,
                'agent-task-1',
                agent_command=[sys.executable, str(agent)],
                verifier_command=[sys.executable, str(verifier)],
            )

            repaired_bundle = json.loads(rejected_bundle.read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(repaired_bundle['operations'][0]['replace'], '[[Existing]]')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Existing]].\n')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'done')

    def test_run_agent_task_repair_rejection_refreshes_blocked_feedback_without_apply(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_blocked_feedback_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            self._write_rejected_default_bundle(kb)
            agent = self._write_repair_bundle_agent(kb)
            verifier = self._write_verifier(kb, accepted=False)

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(
                    kb,
                    'agent-task-1',
                    agent_command=[sys.executable, str(agent)],
                    verifier_command=[sys.executable, str(verifier)],
                )

            queue = self._read_queue(kb)
            events = json.loads((kb / 'sorted' / 'graph-agent-task-events.json').read_text(encoding='utf-8'))
            task = queue['tasks'][0]
            self.assertEqual(raised.exception.code, 'patch_bundle_verification_rejected')
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
            self.assertFalse((kb / 'sorted' / 'graph-patch-applications').exists())
            self.assertEqual(task['status'], 'blocked')
            self.assertEqual(task['blocked_feedback']['summary'], 'rejected')
            self.assertEqual([event['action'] for event in events['events']], ['retry', 'mark_proposed', 'block'])

    def test_run_agent_task_preservation_failure_reports_apply_phase_without_writing(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_generated_page_assets(kb)
            self._write_generated_page_queue(kb)
            self._write_generated_page_unsafe_bundle(kb)
            page = kb / 'wiki' / 'pages' / 'page_alpha.md'
            before = page.read_text(encoding='utf-8')

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(kb, 'agent-task-1')

            self.assertEqual(raised.exception.code, 'generated_page_preservation_failed')
            self.assertEqual(raised.exception.details['phase'], 'apply')
            self.assertEqual(page.read_text(encoding='utf-8'), before)
            self.assertFalse((kb / 'sorted' / 'graph-patch-applications').exists())
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'proposed')

    def test_run_agent_task_repair_request_preserves_generated_page_constraints(self):
        from wikify.maintenance.task_runner import run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_generated_page_assets(kb)
            self._write_generated_page_queue(kb, status='blocked')
            queue = self._read_queue(kb)
            queue['tasks'][0]['blocked_feedback'] = {
                'source': 'bundle_verifier',
                'reason': 'patch_bundle_verification_rejected',
                'summary': 'rejected',
                'findings': [{'severity': 'high', 'message': 'body is not good enough'}],
                'verification_path': str(kb / 'sorted' / 'graph-patch-verifications' / 'agent-task-1.json'),
                'verdict': {'accepted': False, 'summary': 'rejected'},
            }
            (kb / 'sorted' / 'graph-agent-tasks.json').write_text(json.dumps(queue), encoding='utf-8')
            self._write_generated_page_unsafe_bundle(kb)
            agent = self._write_generated_page_repair_agent(kb)

            result = run_agent_task(kb, 'agent-task-1', agent_command=[sys.executable, str(agent)])

            request = json.loads((kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json').read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'completed')
            self.assertTrue(request['repair_context']['available'])
            self.assertTrue(request['safety']['generated_page_preservation']['required'])
            self.assertIn('Repaired body.', (kb / 'wiki' / 'pages' / 'page_alpha.md').read_text(encoding='utf-8'))
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'done')

    def test_run_agent_task_agent_command_failure_is_structured(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('See [[Missing]].\n', encoding='utf-8')
            script = kb / 'failing_agent.py'
            script.write_text('import sys\nprint("nope", file=sys.stderr)\nsys.exit(7)\n', encoding='utf-8')

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(kb, 'agent-task-1', agent_command=[sys.executable, str(script)])

            self.assertEqual(raised.exception.code, 'bundle_producer_command_failed')
            self.assertEqual(raised.exception.details['phase'], 'bundle_producer')
            self.assertEqual(raised.exception.details['returncode'], 7)
            self.assertTrue((kb / 'sorted' / 'graph-patch-proposals' / 'agent-task-1.json').exists())
            self.assertTrue((kb / 'sorted' / 'graph-patch-bundle-requests' / 'agent-task-1.json').exists())
            self.assertFalse((kb / 'sorted' / 'graph-patch-bundles').exists())
            self.assertEqual(target.read_text(encoding='utf-8'), 'See [[Missing]].\n')
            self.assertEqual(self._read_queue(kb)['tasks'][0]['status'], 'proposed')

    def test_run_agent_task_apply_failure_keeps_proposed_state(self):
        from wikify.maintenance.task_runner import TaskRunError, run_agent_task

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            self._write_queue(kb)
            (kb / 'topics').mkdir()
            target = kb / 'topics' / 'a.md'
            target.write_text('[[Missing]] and [[Missing]].\n', encoding='utf-8')
            self._write_bundle(kb)

            with self.assertRaises(TaskRunError) as raised:
                run_agent_task(kb, 'agent-task-1')

            task = self._read_queue(kb)['tasks'][0]
            self.assertEqual(raised.exception.code, 'patch_preflight_failed')
            self.assertEqual(raised.exception.details['phase'], 'apply')
            self.assertEqual(task['status'], 'proposed')
            self.assertEqual(target.read_text(encoding='utf-8'), '[[Missing]] and [[Missing]].\n')
            self.assertFalse((kb / 'sorted' / 'graph-patch-applications').exists())


if __name__ == '__main__':
    unittest.main()
