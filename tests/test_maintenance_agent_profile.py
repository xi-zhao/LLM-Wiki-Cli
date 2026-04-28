import json
import tempfile
import unittest
from pathlib import Path


class MaintenanceAgentProfileTests(unittest.TestCase):
    def test_set_list_show_and_unset_agent_profile(self):
        from wikify.maintenance.agent_profile import (
            agent_profile_path,
            list_agent_profiles,
            set_agent_profile,
            show_agent_profile,
            unset_agent_profile,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)

            set_result = set_agent_profile(
                kb,
                'default',
                'python3 agent.py',
                producer_timeout_seconds=120,
                description='local codex adapter',
            )

            path = agent_profile_path(kb)
            stored = json.loads(path.read_text(encoding='utf-8'))
            listed = list_agent_profiles(kb)
            shown = show_agent_profile(kb, 'default')
            unset_result = unset_agent_profile(kb, 'default')

            self.assertEqual(stored['schema_version'], 'wikify.agent-profiles.v1')
            self.assertEqual(set_result['status'], 'saved')
            self.assertEqual(set_result['profile']['name'], 'default')
            self.assertEqual(set_result['profile']['agent_command'], 'python3 agent.py')
            self.assertEqual(set_result['profile']['producer_timeout_seconds'], 120.0)
            self.assertEqual(set_result['profile']['description'], 'local codex adapter')
            self.assertEqual(listed['summary']['profile_count'], 1)
            self.assertEqual(listed['profiles'][0]['name'], 'default')
            self.assertEqual(shown['profile']['agent_command'], 'python3 agent.py')
            self.assertEqual(unset_result['status'], 'removed')
            self.assertFalse(agent_profile_path(kb).exists())

    def test_resolve_agent_profile_returns_command_timeout_and_source(self):
        from wikify.maintenance.agent_profile import resolve_agent_execution, set_agent_profile

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            set_agent_profile(kb, 'default', 'python3 agent.py', producer_timeout_seconds=45)

            resolved = resolve_agent_execution(kb, agent_command=None, agent_profile='default')

            self.assertEqual(resolved['agent_command'], 'python3 agent.py')
            self.assertEqual(resolved['producer_timeout_seconds'], 45.0)
            self.assertEqual(resolved['source'], 'profile')
            self.assertEqual(resolved['profile'], 'default')

    def test_explicit_command_resolution_keeps_existing_behavior(self):
        from wikify.maintenance.agent_profile import resolve_agent_execution

        with tempfile.TemporaryDirectory() as tmpdir:
            resolved = resolve_agent_execution(
                Path(tmpdir),
                agent_command='python3 direct_agent.py',
                agent_profile=None,
                producer_timeout_seconds=30,
            )

            self.assertEqual(resolved['agent_command'], 'python3 direct_agent.py')
            self.assertEqual(resolved['producer_timeout_seconds'], 30.0)
            self.assertEqual(resolved['source'], 'command')
            self.assertIsNone(resolved['profile'])

    def test_profile_errors_are_structured(self):
        from wikify.maintenance.agent_profile import AgentProfileError, resolve_agent_execution, set_agent_profile

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            set_agent_profile(kb, 'default', 'python3 agent.py')

            with self.assertRaises(AgentProfileError) as ambiguous:
                resolve_agent_execution(kb, agent_command='python3 other.py', agent_profile='default')
            self.assertEqual(ambiguous.exception.code, 'agent_profile_ambiguous')

            with self.assertRaises(AgentProfileError) as missing:
                resolve_agent_execution(kb, agent_command=None, agent_profile='missing')
            self.assertEqual(missing.exception.code, 'agent_profile_missing')
            self.assertEqual(missing.exception.details['profile'], 'missing')

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(AgentProfileError) as missing_config:
                resolve_agent_execution(Path(tmpdir), agent_command=None, agent_profile='default')
            self.assertEqual(missing_config.exception.code, 'agent_profile_config_missing')

    def test_default_profile_can_be_set_shown_cleared_and_resolved(self):
        from wikify.maintenance.agent_profile import (
            DEFAULT_PROFILE_SENTINEL,
            clear_default_agent_profile,
            list_agent_profiles,
            resolve_agent_execution,
            set_agent_profile,
            set_default_agent_profile,
            show_default_agent_profile,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            set_agent_profile(kb, 'default', 'python3 agent.py', producer_timeout_seconds=60)

            set_default = set_default_agent_profile(kb, 'default')
            listed = list_agent_profiles(kb)
            shown = show_default_agent_profile(kb)
            resolved = resolve_agent_execution(kb, agent_profile=DEFAULT_PROFILE_SENTINEL)
            cleared = clear_default_agent_profile(kb)

            self.assertEqual(set_default['status'], 'default_set')
            self.assertEqual(set_default['default_profile'], 'default')
            self.assertEqual(listed['default_profile'], 'default')
            self.assertEqual(listed['summary']['default_profile'], 'default')
            self.assertEqual(shown['profile']['name'], 'default')
            self.assertEqual(resolved['agent_command'], 'python3 agent.py')
            self.assertEqual(resolved['profile'], 'default')
            self.assertEqual(resolved['source'], 'profile')
            self.assertEqual(cleared['status'], 'default_cleared')
            self.assertIsNone(list_agent_profiles(kb)['default_profile'])

    def test_unset_current_default_profile_clears_default_reference(self):
        from wikify.maintenance.agent_profile import (
            list_agent_profiles,
            set_agent_profile,
            set_default_agent_profile,
            unset_agent_profile,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            set_agent_profile(kb, 'default', 'python3 default_agent.py')
            set_agent_profile(kb, 'other', 'python3 other_agent.py')
            set_default_agent_profile(kb, 'default')

            unset_result = unset_agent_profile(kb, 'default')
            listed = list_agent_profiles(kb)

            self.assertEqual(unset_result['status'], 'removed')
            self.assertIsNone(listed['default_profile'])
            self.assertEqual(listed['summary']['profile_count'], 1)
            self.assertEqual(listed['profiles'][0]['name'], 'other')

    def test_default_profile_errors_are_structured(self):
        from wikify.maintenance.agent_profile import (
            DEFAULT_PROFILE_SENTINEL,
            AgentProfileError,
            clear_default_agent_profile,
            resolve_agent_execution,
            set_agent_profile,
            set_default_agent_profile,
            show_default_agent_profile,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = Path(tmpdir)
            set_agent_profile(kb, 'default', 'python3 agent.py')

            with self.assertRaises(AgentProfileError) as missing_default:
                resolve_agent_execution(kb, agent_profile=DEFAULT_PROFILE_SENTINEL)
            self.assertEqual(missing_default.exception.code, 'agent_profile_default_missing')

            with self.assertRaises(AgentProfileError) as missing_profile:
                set_default_agent_profile(kb, 'missing')
            self.assertEqual(missing_profile.exception.code, 'agent_profile_missing')

            with self.assertRaises(AgentProfileError) as show_missing:
                show_default_agent_profile(kb)
            self.assertEqual(show_missing.exception.code, 'agent_profile_default_missing')

            with self.assertRaises(AgentProfileError) as clear_missing:
                clear_default_agent_profile(kb)
            self.assertEqual(clear_missing.exception.code, 'agent_profile_default_missing')


if __name__ == '__main__':
    unittest.main()
