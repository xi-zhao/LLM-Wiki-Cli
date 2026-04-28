# Phase 16 Summary: Explicit Default Agent Profile

## Outcome

Completed explicit default profile shorthand. Projects can now set a default profile and use it with a bare `--agent-profile` flag while preserving the explicit external-agent boundary.

## Delivered

- Added `default_profile` to `wikify-agent-profiles.json`.
- Added `wikify agent-profile --set-default <name>`.
- Added `wikify agent-profile --show-default`.
- Added `wikify agent-profile --clear-default`.
- Added resolver support for the `@default` sentinel.
- Updated automation commands so `--agent-profile` with no value resolves the configured default.
- Ensured unsetting the current default profile clears the default pointer.
- Added structured `agent_profile_default_missing` errors.
- Updated README, product docs, protocol docs, and GSD planning files.

## Verification

- `python3 -m unittest tests.test_maintenance_agent_profile -v`
- `python3 -m unittest tests.test_wikify_cli ... -v` for default profile parser and CLI cases
- `python3 -m unittest discover -s tests -v`
- `python3 -m compileall -q wikify`
- Temp sample KB smoke: set profile, set default, ran `maintain-run --agent-profile` with no value, completed one task and marked it `done`.

## Requirement Coverage

- DFP-01: Complete
- DFP-02: Complete
- DFP-03: Complete
- DFP-04: Complete
- DFP-05: Complete
- DFP-06: Complete
- DFP-07: Complete

## Notes

The default profile is intentionally not automatic. It only resolves when the user or caller explicitly passes `--agent-profile`; commands without that flag still do not execute an external producer.
