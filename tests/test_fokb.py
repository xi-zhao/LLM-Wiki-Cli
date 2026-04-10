import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'fokb.py'
SPEC = importlib.util.spec_from_file_location('fokb', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FokbTests(unittest.TestCase):
    def test_discover_base(self):
        self.assertTrue(str(MODULE.BASE).endswith('file-organizer'))

    def test_discover_base_from_env(self):
        original = os.environ.get('FOKB_BASE')
        try:
            os.environ['FOKB_BASE'] = '/tmp/fokb-sample'
            self.assertEqual(MODULE.discover_base(), Path('/tmp/fokb-sample').resolve())
            self.assertTrue(str(MODULE.SCRIPTS).endswith('file-organizer/scripts'))
        finally:
            if original is None:
                os.environ.pop('FOKB_BASE', None)
            else:
                os.environ['FOKB_BASE'] = original

    def test_build_parser_ingest(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['ingest', 'https://example.com'])
        self.assertEqual(args.command, 'ingest')
        self.assertEqual(args.url, 'https://example.com')
        self.assertEqual(args.output, 'json')

    def test_build_parser_output_pretty(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['--output', 'pretty', 'status'])
        self.assertEqual(args.output, 'pretty')
        self.assertEqual(args.command, 'status')

    def test_build_parser_init(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['init'])
        self.assertEqual(args.command, 'init')

    def test_build_parser_check(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['check'])
        self.assertEqual(args.command, 'check')

    def test_build_parser_search(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['search', 'quantum', '--scope', 'topics'])
        self.assertEqual(args.command, 'search')
        self.assertEqual(args.scope, 'topics')

    def test_build_parser_query(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['query', 'quantum', '--max-chars', '500'])
        self.assertEqual(args.command, 'query')
        self.assertEqual(args.max_chars, 500)

    def test_build_parser_writeback(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['writeback', 'quantum', '--title', 'Quantum Notes'])
        self.assertEqual(args.command, 'writeback')
        self.assertEqual(args.title, 'Quantum Notes')

    def test_build_parser_synthesize(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['synthesize', 'quantum', '--mode', 'outline'])
        self.assertEqual(args.command, 'synthesize')
        self.assertEqual(args.mode, 'outline')

    def test_build_parser_show(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['show', 'quantum-computing-industry', '--scope', 'topics'])
        self.assertEqual(args.command, 'show')
        self.assertEqual(args.scope, 'topics')

    def test_build_parser_list(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['list', 'topics', '--limit', '3'])
        self.assertEqual(args.command, 'list')
        self.assertEqual(args.scope, 'topics')
        self.assertEqual(args.limit, 3)

    def test_build_parser_stats(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['stats'])
        self.assertEqual(args.command, 'stats')

    def test_build_parser_lint_deep(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['lint', '--deep'])
        self.assertEqual(args.command, 'lint')
        self.assertTrue(args.deep)

    def test_build_parser_maintenance(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['maintenance', '--last'])
        self.assertEqual(args.command, 'maintenance')
        self.assertTrue(args.last)

    def test_build_parser_decide(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['decide', '--last', '--execute'])
        self.assertEqual(args.command, 'decide')
        self.assertTrue(args.last)
        self.assertTrue(args.execute)

    def test_build_parser_promote(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['promote', '/tmp/a.md'])
        self.assertEqual(args.command, 'promote')
        self.assertEqual(args.path, '/tmp/a.md')

    def test_build_parser_status(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['status'])
        self.assertEqual(args.command, 'status')

    def test_build_parser_review(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['review', '--summary'])
        self.assertEqual(args.command, 'review')
        self.assertTrue(args.summary)

    def test_build_review_summary(self):
        summary = MODULE.build_review_summary([
            {'url': 'https://a.com', 'status': 'needs_review'},
            {'url': 'https://b.com', 'status': 'briefed'},
            {'url': 'https://c.com', 'status': 'needs_review'},
        ])
        self.assertEqual(summary['count'], 3)
        self.assertEqual(summary['by_status']['needs_review'], 2)
        self.assertEqual(len(summary['urls']), 3)

    def test_search_markdown(self):
        matches = MODULE.search_markdown('quantum', 'topics', limit=5)
        self.assertIsInstance(matches, list)

    def test_slugify(self):
        self.assertEqual(MODULE.slugify('Quantum Financing Notes'), 'quantum-financing-notes')

    def test_render_synthesis_markdown(self):
        markdown = MODULE.render_synthesis_markdown(
            'Test Title',
            'quantum',
            'topics',
            [{'title': 'doc1', 'type': 'topics', 'path': '/tmp/doc1.md', 'excerpt': 'hello world'}],
            'outline',
        )
        self.assertIn('# Test Title', markdown)
        self.assertIn('doc1', markdown)
        self.assertIn('## Source Objects', markdown)

    def test_resolve_show_target(self):
        source_type, path = MODULE.resolve_show_target('quantum-computing-industry', 'topics')
        self.assertEqual(source_type, 'topics')
        self.assertTrue(str(path).endswith('quantum-computing-industry.md'))

    def test_build_list_entries(self):
        entries = MODULE.build_list_entries('topics', limit=2)
        self.assertIsInstance(entries, list)

    def test_run_deep_lint(self):
        result = MODULE.run_deep_lint()
        self.assertIn('topic_count', result)
        self.assertIn('warnings', result)

    def test_build_incremental_maintenance_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'emerging-agent-note.md'
            path.write_text(
                '# Emerging Agent Note\n\n## Context Excerpts\n\n提到 OpenClawRouter 与 NovelConceptAlpha。\n',
                encoding='utf-8',
            )
            signals = MODULE.build_incremental_maintenance_signals([str(path)])
        self.assertTrue(signals['checked'])
        self.assertEqual(signals['scope'], 'incremental')
        self.assertIn('changed_objects', signals)

    def test_infer_changed_object_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = MODULE.BASE
            try:
                MODULE.BASE = Path(tmpdir)
                topic_dir = Path(tmpdir) / 'topics'
                timeline_dir = Path(tmpdir) / 'timelines'
                topic_dir.mkdir()
                timeline_dir.mkdir()
                topic_path = topic_dir / 'sample-topic.md'
                timeline_path = timeline_dir / 'sample-topic.md'
                topic_path.write_text(
                    '# Sample Topic\n\n## 关联文章\n- [A](../articles/parsed/a.md)\n\n这是 NovelConceptBeta，可行。\n',
                    encoding='utf-8',
                )
                timeline_path.write_text(
                    '# Sample Timeline\n\n这里说这个方向存在风险。\n',
                    encoding='utf-8',
                )
                result = MODULE.infer_changed_object_signals([str(topic_path)])
            finally:
                MODULE.BASE = original_base
        self.assertIn('changed_objects', result)
        self.assertTrue(result['changed_objects'])
        self.assertIn('neighbors', result['changed_objects'][0])
        self.assertIn('claims', result['changed_objects'][0])

    def test_extract_claims(self):
        claims = MODULE.extract_claims('OpenClaw 路由可行。这个方案存在风险。')
        self.assertTrue(claims)
        self.assertEqual(claims[0]['polarity'], 'positive')
        self.assertIn('canonical_subject', claims[0])

    def test_canonicalize_subject(self):
        self.assertEqual(MODULE.canonicalize_subject('OpenClaw Router'), 'openclaw-route')

    def test_effective_claim_weight(self):
        self.assertEqual(MODULE.effective_claim_weight('parsed', '/tmp/2026-04-09_example.md'), 3)

    def test_synthesize_object_verdict(self):
        verdict = MODULE.synthesize_object_verdict({
            'type': 'topics',
            'signals': ['emerging_concepts_detected'],
            'warnings': [],
            'contradictions': [],
        })
        self.assertEqual(verdict, 'emerging')

    def test_needs_promotion(self):
        self.assertTrue(MODULE.needs_promotion({
            'type': 'sorted',
            'signals': ['emerging_concepts_detected'],
            'contradictions': [],
            'neighbors': [{'path': '/tmp/a.md'}],
            'claims': [],
        }))

    def test_needs_promotion_zero_context_guardrail(self):
        self.assertFalse(MODULE.needs_promotion({
            'type': 'sorted',
            'signals': ['emerging_concepts_detected'],
            'contradictions': [],
            'neighbors': [],
            'claims': [],
        }))

    def test_synthesize_maintenance_verdict(self):
        verdict = MODULE.synthesize_maintenance_verdict(
            [{'verdict': 'stable'}, {'verdict': 'stable'}],
            [],
            [],
        )
        self.assertEqual(verdict, 'stable')

    def test_synthesize_maintenance_verdict_needs_promotion(self):
        verdict = MODULE.synthesize_maintenance_verdict(
            [{'verdict': 'needs_promotion'}],
            [],
            [],
        )
        self.assertEqual(verdict, 'needs_promotion')

    def test_normalize_maintenance(self):
        normalized = MODULE.normalize_maintenance({'signals': ['x']})
        self.assertEqual(normalized['verdict'], 'watch')
        self.assertIn('changed_objects', normalized)

    def test_build_decision_plan(self):
        plan = MODULE.build_decision_plan({
            'verdict': 'needs_promotion',
            'changed_objects': [{'path': '/tmp/a.md', 'promotion_candidate': True}],
        })
        self.assertIn('promote_to_topic_or_timeline', plan['actions'])
        self.assertTrue(plan['promotion_targets'])
        self.assertIn('steps', plan)

    def test_build_decision_steps(self):
        steps = MODULE.build_decision_steps({
            'verdict': 'needs_promotion',
            'changed_objects': [{'path': '/tmp/a.md', 'promotion_candidate': True}],
        })
        self.assertEqual(steps[0]['action'], 'promote_to_topic_or_timeline')
        self.assertTrue(steps[0]['can_execute'])

    def test_promote_target_to_topic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = MODULE.BASE
            try:
                MODULE.BASE = Path(tmpdir)
                (Path(tmpdir) / 'topics').mkdir()
                sorted_dir = Path(tmpdir) / 'sorted'
                sorted_dir.mkdir()
                source = sorted_dir / 'sample-note.md'
                source.write_text('# Sample\n', encoding='utf-8')
                result = MODULE.promote_target_to_topic(source)
                created = Path(result['path']).read_text(encoding='utf-8')
            finally:
                MODULE.BASE = original_base
        self.assertTrue(result['created'])
        self.assertIn('来源候选', created)
        self.assertIn('type: topic', created)
        self.assertIn('## 笔记关系', created)

    def test_execute_decision_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = MODULE.BASE
            try:
                MODULE.BASE = Path(tmpdir)
                (Path(tmpdir) / 'topics').mkdir()
                sorted_dir = Path(tmpdir) / 'sorted'
                sorted_dir.mkdir()
                source = sorted_dir / 'candidate.md'
                source.write_text('# Candidate\n', encoding='utf-8')
                result = MODULE.execute_decision_plan({'steps': [
                    {
                        'action': 'promote_to_topic_or_timeline',
                        'target': str(source),
                        'can_execute': True,
                    }
                ]})
            finally:
                MODULE.BASE = original_base
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['mode'], 'decision_execute')
        self.assertEqual(result['executed'][0]['reason'], 'topic_created_from_sorted')
        self.assertIn('artifacts', result['executed'][0])
        self.assertIn('state_change', result['executed'][0])

    def test_execute_decision_plan_non_executable(self):
        result = MODULE.execute_decision_plan({'steps': [
            {
                'action': 'prepare_promotion_candidates',
                'target': None,
                'can_execute': False,
            }
        ]})
        self.assertEqual(result['executed'][0]['status'], 'skipped_non_executable')
        self.assertEqual(result['executed'][0]['reason'], 'step_marked_non_executable')

    def test_attach_completion(self):
        payload, _ = MODULE.envelope_ok('synthesize', {'output_path': '/tmp/out.md'})
        payload = MODULE.attach_completion(payload)
        self.assertIn('completion', payload['result'])
        self.assertEqual(payload['result']['completion']['status'], 'completed')

    def test_record_maintenance_with_provenance(self):
        original = MODULE.read_json(MODULE.MAINTENANCE_HISTORY, [])
        try:
            MODULE.record_maintenance('test', {'checked': True, 'scope': 'incremental'}, {'trigger': 'unit-test'})
            history = MODULE.read_maintenance_history()
            self.assertIn('provenance', history[-1])
            self.assertEqual(history[-1]['provenance']['trigger'], 'unit-test')
        finally:
            MODULE.write_json(MODULE.MAINTENANCE_HISTORY, original)

    def test_normalize_legacy_meta_to_provenance(self):
        original = MODULE.read_json(MODULE.MAINTENANCE_HISTORY, [])
        try:
            MODULE.write_json(MODULE.MAINTENANCE_HISTORY, [{
                'command': 'test',
                'maintenance': {'checked': True, 'scope': 'incremental'},
                'meta': {'trigger': 'legacy-test'},
            }])
            history = MODULE.read_maintenance_history()
            self.assertEqual(history[-1]['provenance']['trigger'], 'legacy-test')
        finally:
            MODULE.write_json(MODULE.MAINTENANCE_HISTORY, original)

    def test_topic_seed_source_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            topic_dir = Path(tmpdir) / 'topics'
            topic_dir.mkdir()
            topic_path = topic_dir / 'seed-topic.md'
            topic_path.write_text(
                '# Topic: seed\n\n## 来源候选\n- [seed](../sorted/seed.md)\n',
                encoding='utf-8',
            )
            result = MODULE.infer_changed_object_signals([str(topic_path)])
        self.assertIn('topic_seed_source_present', result['changed_objects'][0]['signals'])

    def test_strip_template_noise(self):
        cleaned = MODULE.strip_template_noise('初始提升骨架，待补充稳定判断。根据后续 ingest 继续完善。信号继续完善。](../sorted/a.md)')
        self.assertNotIn('初始提升骨架', cleaned)
        self.assertNotIn('信号继续完善', cleaned)
        self.assertNotIn('../sorted/', cleaned)

    def test_extract_claims_skip_link_fragments(self):
        claims = MODULE.extract_claims('- [quantum-financing-outline-validation-2](../sorted/x.md)')
        self.assertEqual(claims, [])

    def test_detect_neighbor_tension(self):
        tensions, contradictions = MODULE.detect_neighbor_tension(
            'OpenClaw Router 可行。',
            [{'type': 'topics', 'path': '/tmp/topic.md', 'text': 'OpenClaw 路由存在风险。'}],
            'sorted',
            '/tmp/2026-04-09_sorted.md',
        )
        self.assertTrue(tensions)
        self.assertIsInstance(contradictions, list)
        self.assertTrue(contradictions)
        self.assertEqual(contradictions[0]['baseline_side'], 'neighbor')

    def test_record_maintenance(self):
        original = MODULE.read_json(MODULE.MAINTENANCE_HISTORY, [])
        try:
            MODULE.record_maintenance('test', {'checked': True, 'scope': 'incremental'})
            history = MODULE.read_json(MODULE.MAINTENANCE_HISTORY, [])
            self.assertTrue(isinstance(history, list))
        finally:
            MODULE.write_json(MODULE.MAINTENANCE_HISTORY, original)

    def test_build_parser_reingest(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['reingest', '--last'])
        self.assertEqual(args.command, 'reingest')
        self.assertTrue(args.last)

    def test_build_parser_state(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['state'])
        self.assertEqual(args.command, 'state')

    def test_build_parser_decide_maintenance_path(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['decide', '--maintenance-path', '/tmp/a.md'])
        self.assertEqual(args.command, 'decide')
        self.assertEqual(args.maintenance_path, '/tmp/a.md')

    def test_build_parser_resolve(self):
        parser = MODULE.build_parser()
        args = parser.parse_args(['resolve', '--last'])
        self.assertEqual(args.command, 'resolve')
        self.assertTrue(args.last)

    def test_resolve_decision_target_from_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = MODULE.BASE
            try:
                MODULE.BASE = Path(tmpdir)
                (Path(tmpdir) / 'scripts').mkdir()
                (Path(tmpdir) / 'sorted').mkdir()
                note = Path(tmpdir) / 'sorted' / 'candidate.md'
                note.write_text('# Candidate\n\n## Context Excerpts\n', encoding='utf-8')
                class Args:
                    maintenance_path = str(note)
                    last = False
                maintenance, source = MODULE.resolve_decision_target(Args(), [])
            finally:
                MODULE.BASE = original_base
        self.assertEqual(source['source'], 'maintenance_path')
        self.assertIn(str(note.resolve()), maintenance['changed_paths'])

    def test_envelope_ok(self):
        payload, code = MODULE.envelope_ok('status', {'a': 1})
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['command'], 'status')
        self.assertEqual(code, 0)

    def test_envelope_error(self):
        payload, code = MODULE.envelope_error('reingest', 'review_item_not_found', 'not found', 2)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['error']['code'], 'review_item_not_found')
        self.assertEqual(code, 2)

    def test_build_completion_for_ingest(self):
        completion = MODULE.build_completion('ingest', {
            'title': 'Sample',
            'files': {'raw': '/tmp/raw.md'},
            'next_actions': ['digest_optional'],
            'digest_policy': {'eligible': True},
        })
        self.assertEqual(completion['status'], 'completed')
        self.assertIn('/tmp/raw.md', completion['artifacts'])
        self.assertIn('digest_optional', completion['next_actions'])

    def test_build_completion_for_ingest_suppresses_digest_when_manual_only(self):
        completion = MODULE.build_completion('ingest', {
            'title': 'Sample',
            'files': {'raw': '/tmp/raw.md'},
            'next_actions': ['digest_optional', 'review_required'],
            'digest_policy': {'eligible': False},
        })
        self.assertNotIn('digest_optional', completion['next_actions'])
        self.assertIn('review_required', completion['next_actions'])

    def test_build_digest_policy_auto_eligible(self):
        digest_policy = MODULE.build_digest_policy({
            'quality': {'review_required': False},
            'lifecycle_status': 'integrated',
            'routing': {'primary_topic': 'ai-coding-and-autoresearch.md'},
            'updated_topics': [{'topic': 'ai-coding-and-autoresearch.md'}],
            'next_actions': ['digest_optional'],
        })
        self.assertTrue(digest_policy['eligible'])
        self.assertEqual(digest_policy['mode'], 'auto_eligible')
        self.assertEqual(digest_policy['recommended_action'], 'digest_optional')

    def test_build_digest_policy_manual_only(self):
        digest_policy = MODULE.build_digest_policy({
            'quality': {'review_required': True},
            'lifecycle_status': 'briefed',
            'routing': {'primary_topic': None},
            'updated_topics': [],
            'next_actions': [],
        })
        self.assertFalse(digest_policy['eligible'])
        self.assertEqual(digest_policy['mode'], 'manual_only')
        self.assertIn('review_required', digest_policy['blocking_reasons'])

    def test_attach_digest_policy(self):
        payload, _ = MODULE.envelope_ok('ingest', {
            'quality': {'review_required': False},
            'lifecycle_status': 'integrated',
            'routing': {'primary_topic': 'ai-coding-and-autoresearch.md'},
            'updated_topics': [{'topic': 'ai-coding-and-autoresearch.md'}],
            'next_actions': ['digest_optional'],
        })
        payload = MODULE.attach_digest_policy(payload)
        self.assertIn('digest_policy', payload['result'])
        self.assertTrue(payload['result']['digest_policy']['eligible'])

    def test_build_completion_for_digest(self):
        completion = MODULE.build_completion('digest', {'output': '/tmp/topic-digest.md'})
        self.assertEqual(completion['status'], 'completed')
        self.assertIn('/tmp/topic-digest.md', completion['artifacts'])

    def test_build_completion_for_resolve(self):
        completion = MODULE.build_completion('resolve', {'url': 'https://example.com'})
        self.assertEqual(completion['status'], 'completed')
        self.assertIn('resolve completed', completion['summary'])

    def test_cmd_resolve_returns_envelope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_base = MODULE.BASE
            original_review_queue = MODULE.REVIEW_QUEUE
            original_resolved_review = MODULE.RESOLVED_REVIEW
            original_system_state = MODULE.SYSTEM_STATE
            original_maintenance_history = MODULE.MAINTENANCE_HISTORY
            original_last_payload = MODULE.LAST_PAYLOAD
            original_lint_report = MODULE.LINT_REPORT
            original_sorted = MODULE.SORTED
            original_scripts = MODULE.SCRIPTS
            try:
                base = Path(tmpdir)
                MODULE.BASE = base
                MODULE.SORTED = base / 'sorted'
                MODULE.SCRIPTS = base / 'scripts'
                MODULE.REVIEW_QUEUE = MODULE.SORTED / 'review-queue.json'
                MODULE.RESOLVED_REVIEW = MODULE.SORTED / 'resolved-review.json'
                MODULE.SYSTEM_STATE = MODULE.SORTED / 'system-state.json'
                MODULE.MAINTENANCE_HISTORY = MODULE.SORTED / 'maintenance-history.json'
                MODULE.LAST_PAYLOAD = MODULE.SORTED / 'last-ingest-payload.json'
                MODULE.LINT_REPORT = MODULE.SORTED / 'wiki-lint-report.json'
                MODULE.ensure_layout()
                MODULE.write_json(MODULE.REVIEW_QUEUE, [{
                    'url': 'https://example.com/review-item',
                    'status': 'pending',
                }])
                class Args:
                    url = None
                    last = True
                    reason = None
                payload, exit_code = MODULE.cmd_resolve(Args())
            finally:
                MODULE.BASE = original_base
                MODULE.REVIEW_QUEUE = original_review_queue
                MODULE.RESOLVED_REVIEW = original_resolved_review
                MODULE.SYSTEM_STATE = original_system_state
                MODULE.MAINTENANCE_HISTORY = original_maintenance_history
                MODULE.LAST_PAYLOAD = original_last_payload
                MODULE.LINT_REPORT = original_lint_report
                MODULE.SORTED = original_sorted
                MODULE.SCRIPTS = original_scripts
        self.assertTrue(payload['ok'])
        self.assertEqual(exit_code, 0)
        self.assertIn('completion', payload['result'])


if __name__ == '__main__':
    unittest.main()
