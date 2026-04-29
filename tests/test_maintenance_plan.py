import unittest


class MaintenancePlanTests(unittest.TestCase):
    def setUp(self):
        self.findings = [
            {
                'id': 'broken-link:topics/a.md:7:Missing',
                'type': 'broken_link',
                'severity': 'warning',
                'title': 'Broken link',
                'subject': 'topics/a.md',
                'evidence': {'source': 'topics/a.md', 'line': 7},
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

    def test_build_plan_creates_one_policy_gated_step_per_finding(self):
        from wikify.maintenance.planner import build_plan

        plan = build_plan(self.findings, policy='balanced')

        self.assertEqual(plan['schema_version'], 'wikify.maintenance-plan.v1')
        self.assertEqual(plan['policy'], 'balanced')
        self.assertEqual(len(plan['steps']), 2)
        for step in plan['steps']:
            self.assertIn('finding_id', step)

    def test_apply_plan_executes_deterministic_steps_and_queues_content_steps(self):
        from wikify.maintenance.executor import apply_plan
        from wikify.maintenance.planner import build_plan

        plan = build_plan(self.findings, policy='balanced')

        execution = apply_plan(plan, dry_run=False)

        status_by_action = {
            item['action']: item['status']
            for item in execution['results']
        }
        self.assertEqual(status_by_action['queue_link_repair'], 'queued')
        self.assertEqual(status_by_action['record_graph_health_snapshot'], 'executed')
        self.assertEqual(execution['summary']['executed_count'], 1)
        self.assertEqual(execution['summary']['queued_count'], 1)

    def test_apply_plan_marks_all_steps_as_dry_run(self):
        from wikify.maintenance.executor import apply_plan
        from wikify.maintenance.planner import build_plan

        plan = build_plan(self.findings, policy='balanced')

        execution = apply_plan(plan, dry_run=True)

        self.assertEqual(
            {item['status'] for item in execution['results']},
            {'dry_run'},
        )
        self.assertEqual(execution['summary']['dry_run_count'], 2)

    def test_new_artifact_actions_have_expected_risks_and_queueing(self):
        from wikify.maintenance.executor import apply_plan
        from wikify.maintenance.planner import build_plan

        findings = [
            {
                'id': 'validation',
                'type': 'object_validation_record',
                'severity': 'info',
                'title': 'Validation',
                'subject': 'wiki/pages/page_alpha.md',
                'evidence': {},
                'recommended_action': 'queue_object_validation_repair',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
            },
            {
                'id': 'view',
                'type': 'view_task',
                'severity': 'info',
                'title': 'View',
                'subject': 'views/pages.md',
                'evidence': {},
                'recommended_action': 'queue_view_regeneration',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
            },
            {
                'id': 'agent',
                'type': 'agent_export_missing',
                'severity': 'info',
                'title': 'Agent',
                'subject': 'artifacts/agent/page-index.json',
                'evidence': {},
                'recommended_action': 'queue_agent_export_refresh',
                'can_auto_apply': False,
                'policy_minimum': 'conservative',
            },
        ]

        plan = build_plan(findings, policy='balanced')
        risk_by_action = {step['action']: step['risk'] for step in plan['steps']}
        self.assertEqual(risk_by_action['queue_object_validation_repair'], 'semantic')
        self.assertEqual(risk_by_action['queue_view_regeneration'], 'generated_content')
        self.assertEqual(risk_by_action['queue_agent_export_refresh'], 'deterministic')

        execution = apply_plan(plan, dry_run=False)
        self.assertEqual({result['status'] for result in execution['results']}, {'queued'})


if __name__ == '__main__':
    unittest.main()
