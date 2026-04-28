# Phase 12 Summary: Run Task Inline Producer Automation

## Outcome

Completed one-command producer automation for `wikify run-task`.

`wikify run-task --id <task-id> --agent-command "<command>"` now:
- creates or reuses the task proposal
- marks queued tasks as proposed
- writes the patch bundle request when the bundle is missing
- invokes the explicit external producer command
- preflights the produced bundle
- applies the deterministic patch bundle
- marks the task done

The default behavior remains conservative:
- `run-task` without `--agent-command` still stops at `waiting_for_patch_bundle`
- dry-run with `--agent-command` does not execute the command or write artifacts
- existing bundles are applied without executing the producer command
- producer failures return structured `bundle_producer_*` errors with `details.phase = "bundle_producer"`

## Commits

- Planning: `56ae7a2 docs: plan gsd run-task inline producer automation phase`
- Implementation: `81c5cb7 feat: let run-task invoke explicit bundle producer`
- Documentation: `49ffaff docs: document run-task inline producer automation`

## Verification

- `python3 -m unittest tests.test_maintenance_task_runner -v`
- `python3 -m unittest tests.test_wikify_cli tests.test_maintenance_task_runner -v`
- `python3 -m unittest discover -s tests -v`
- `python3 -m compileall -q wikify`
- Temp-KB smoke: one `run-task --agent-command` command produced request and bundle, applied the patch, and marked the task `done`.

## Requirement Coverage

- RTP-01: Complete
- RTP-02: Complete
- RTP-03: Complete
- RTP-04: Complete
- RTP-05: Complete
- RTP-06: Complete
- RTP-07: Complete

## Deviations

None.
