import unittest


class MaintenanceTaskQueueTests(unittest.TestCase):
    def test_build_task_queue_creates_tasks_only_for_queued_steps(self):
        from wikify.maintenance.executor import apply_plan
        from wikify.maintenance.planner import build_plan
        from wikify.maintenance.task_queue import build_task_queue

        findings = [
            {
                'id': 'broken-link:topics/a.md:7:Missing',
                'type': 'broken_link',
                'severity': 'warning',
                'title': 'Broken link',
                'subject': 'topics/a.md',
                'evidence': {'source': 'topics/a.md', 'line': 7, 'target': 'Missing'},
                'recommended_action': 'queue_link_repair',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
                'relevance': {
                    'schema_version': 'wikify.graph-relevance.v1',
                    'max_score': 7.5,
                    'max_confidence': 'high',
                    'priority_signal': True,
                    'top_related': [{'id': 'articles/parsed/a.md', 'score': 7.5}],
                },
            },
            {
                'id': 'thin-graph',
                'type': 'thin_graph',
                'severity': 'warning',
                'title': 'Thin graph',
                'subject': 'graph',
                'evidence': {'node_count': 0, 'edge_count': 0},
                'recommended_action': 'record_graph_health_snapshot',
                'can_auto_apply': True,
                'policy_minimum': 'conservative',
            },
        ]
        plan = build_plan(findings, policy='balanced')
        execution = apply_plan(plan, dry_run=False)

        queue = build_task_queue(plan, execution, findings)

        self.assertEqual(queue['schema_version'], 'wikify.graph-agent-tasks.v1')
        self.assertEqual(queue['summary']['task_count'], 1)
        self.assertEqual(len(queue['tasks']), 1)

        task = queue['tasks'][0]
        self.assertEqual(task['source_finding_id'], 'broken-link:topics/a.md:7:Missing')
        self.assertEqual(task['action'], 'queue_link_repair')
        self.assertEqual(task['priority'], 'high')
        self.assertEqual(task['target'], 'topics/a.md')
        self.assertEqual(task['evidence']['target'], 'Missing')
        self.assertEqual(task['relevance']['max_confidence'], 'high')
        self.assertEqual(task['write_scope'], ['topics/a.md'])
        self.assertFalse(task['requires_user'])
        self.assertEqual(task['status'], 'queued')

        for key in [
            'id',
            'source_finding_id',
            'action',
            'priority',
            'target',
            'evidence',
            'write_scope',
            'agent_instructions',
            'acceptance_checks',
            'requires_user',
            'status',
        ]:
            self.assertIn(key, task)
        self.assertGreaterEqual(len(task['agent_instructions']), 1)
        self.assertGreaterEqual(len(task['acceptance_checks']), 1)

    def test_low_confidence_relevance_does_not_escalate_priority(self):
        from wikify.maintenance.executor import apply_plan
        from wikify.maintenance.planner import build_plan
        from wikify.maintenance.task_queue import build_task_queue

        findings = [
            {
                'id': 'orphan-node:topics/a.md',
                'type': 'orphan_node',
                'severity': 'info',
                'title': 'Orphan',
                'subject': 'topics/a.md',
                'evidence': {},
                'recommended_action': 'queue_orphan_attachment',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
                'relevance': {
                    'schema_version': 'wikify.graph-relevance.v1',
                    'max_score': 1.0,
                    'max_confidence': 'low',
                    'priority_signal': False,
                    'top_related': [{'id': 'topics/b.md', 'score': 1.0}],
                },
            }
        ]
        plan = build_plan(findings, policy='balanced')
        execution = apply_plan(plan, dry_run=False)

        queue = build_task_queue(plan, execution, findings)

        self.assertEqual(queue['tasks'][0]['priority'], 'normal')
        self.assertEqual(queue['tasks'][0]['relevance']['max_confidence'], 'low')

    def test_build_task_queue_copies_generated_page_metadata(self):
        from wikify.maintenance.executor import apply_plan
        from wikify.maintenance.planner import build_plan
        from wikify.maintenance.task_queue import build_task_queue

        findings = [
            {
                'id': 'broken-link:wiki/pages/page_alpha.md:5:Missing',
                'type': 'broken_link',
                'severity': 'warning',
                'title': 'Broken link',
                'subject': 'wiki/pages/page_alpha.md',
                'evidence': {'source': 'wiki/pages/page_alpha.md', 'line': 5, 'target': 'Missing'},
                'recommended_action': 'queue_link_repair',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
                'target_kind': 'wiki_page',
                'target_family': 'personal_wiki_page',
                'object_id': 'page_alpha',
                'object_type': 'wiki_page',
                'body_path': 'wiki/pages/page_alpha.md',
                'object_path': 'artifacts/objects/wiki_pages/page_alpha.json',
                'source_refs': [{'source_id': 'src_notes', 'item_id': 'item_alpha', 'confidence': 0.9}],
                'review_status': 'generated',
                'write_scope': ['wiki/pages/page_alpha.md'],
            }
        ]
        plan = build_plan(findings, policy='balanced')
        execution = apply_plan(plan, dry_run=False)

        queue = build_task_queue(plan, execution, findings)

        task = queue['tasks'][0]
        self.assertEqual(task['target'], 'wiki/pages/page_alpha.md')
        self.assertEqual(task['object_id'], 'page_alpha')
        self.assertEqual(task['object_type'], 'wiki_page')
        self.assertEqual(task['body_path'], 'wiki/pages/page_alpha.md')
        self.assertEqual(task['source_refs'][0]['source_id'], 'src_notes')
        self.assertEqual(task['review_status'], 'generated')
        self.assertEqual(task['write_scope'], ['wiki/pages/page_alpha.md'])

    def test_build_task_queue_adds_instructions_for_artifact_actions(self):
        from wikify.maintenance.executor import apply_plan
        from wikify.maintenance.planner import build_plan
        from wikify.maintenance.task_queue import build_task_queue

        findings = [
            {
                'id': 'generated-drift',
                'type': 'generated_page_drift',
                'severity': 'warning',
                'title': 'Generated page drift',
                'subject': 'wiki/pages/page_alpha.md',
                'evidence': {},
                'recommended_action': 'queue_generated_page_repair',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
                'object_id': 'page_alpha',
                'body_path': 'wiki/pages/page_alpha.md',
                'source_refs': [{'source_id': 'src_notes', 'item_id': 'item_alpha'}],
                'review_status': 'generated',
                'write_scope': ['wiki/pages/page_alpha.md'],
            },
            {
                'id': 'agent-missing',
                'type': 'agent_export_missing',
                'severity': 'info',
                'title': 'Agent export missing',
                'subject': 'artifacts/agent/page-index.json',
                'evidence': {},
                'recommended_action': 'queue_agent_export_refresh',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
                'agent_artifact_path': 'artifacts/agent/page-index.json',
                'write_scope': ['artifacts/agent/page-index.json'],
                'regeneration_command': 'wikify agent export',
            },
        ]
        plan = build_plan(findings, policy='balanced')
        execution = apply_plan(plan, dry_run=False)

        queue = build_task_queue(plan, execution, findings)

        by_action = {task['action']: task for task in queue['tasks']}
        generated_task = by_action['queue_generated_page_repair']
        self.assertFalse(generated_task['requires_user'])
        self.assertIn('source_refs', ' '.join(generated_task['agent_instructions']))
        self.assertIn('review_status', ' '.join(generated_task['agent_instructions']))
        self.assertGreaterEqual(len(generated_task['acceptance_checks']), 1)

        agent_task = by_action['queue_agent_export_refresh']
        self.assertFalse(agent_task['requires_user'])
        self.assertEqual(agent_task['regeneration_command'], 'wikify agent export')
        self.assertIn('wikify agent export', ' '.join(agent_task['agent_instructions']))


if __name__ == '__main__':
    unittest.main()
