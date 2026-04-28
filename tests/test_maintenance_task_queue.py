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


if __name__ == '__main__':
    unittest.main()
