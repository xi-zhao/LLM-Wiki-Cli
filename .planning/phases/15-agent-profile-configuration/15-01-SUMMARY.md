# Phase 15 Summary: Agent Profile Configuration

## Outcome

Completed explicit agent command profiles. Projects can now store named external agent commands in `wikify-agent-profiles.json` and use them with producer/run automation through `--agent-profile`.

## Delivered

- Added `wikify/maintenance/agent_profile.py` with profile artifact read/write, validation, listing, showing, removal, and resolution.
- Added `wikify agent-profile` with `--set`, `--list`, `--show`, and `--unset`.
- Added `--agent-profile` support to `produce-bundle`, `run-task`, `run-tasks`, and `maintain-run`.
- Added structured errors for ambiguous command/profile input, missing config, missing profile, invalid names, invalid config, and missing command.
- Exposed profile source metadata in command results via `execution.agent_profile` and `execution.agent_command_source`.
- Preserved existing producer/preflight/apply/lifecycle behavior; profiles resolve to the same explicit command input path.
- Updated README, product docs, protocol docs, and GSD planning files.

## Verification

- `python3 -m unittest tests.test_maintenance_agent_profile -v`
- `python3 -m unittest tests.test_wikify_cli tests.test_maintenance_agent_profile tests.test_maintenance_bundle_producer tests.test_maintenance_task_runner tests.test_maintenance_batch_runner tests.test_maintenance_maintain_run -v`
- `python3 -m unittest discover -s tests -v`
- `python3 -m compileall -q wikify`
- Temp sample KB smoke: `agent-profile --set default ...` then `maintain-run --agent-profile default` completed one task, marked it `done`, and applied the patch.

## Requirement Coverage

- AGP-01: Complete
- AGP-02: Complete
- AGP-03: Complete
- AGP-04: Complete
- AGP-05: Complete
- AGP-06: Complete
- AGP-07: Complete
- AGP-08: Complete

## Notes

Profiles are intentionally aliases for explicit external commands, not provider adapters. They do not store secrets, select models, retry provider calls, or bypass patch preflight.
