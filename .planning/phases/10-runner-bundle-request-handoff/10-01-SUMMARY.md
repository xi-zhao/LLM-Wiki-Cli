# Summary: Build Runner Bundle Request Handoff

## Plan

- Phase: 10-runner-bundle-request-handoff
- Plan: 10-01
- Plan commit: `bd0eabd`
- Implementation commit: `ae6e97d`
- Documentation commit: `5cd4d55`
- Status: Complete

## What Changed

- `run_agent_task` now composes the Phase 9 bundle request contract when no patch bundle exists.
- Non-dry-run missing-bundle flow writes `sorted/graph-patch-bundle-requests/<task-id>.json`.
- Dry-run missing-bundle flow reports `summary.bundle_request_path` and `summary.suggested_bundle_path` while writing nothing.
- `wikify.agent-task-run.v1` results now include `artifacts.patch_bundle_request`.
- Bundle request errors inside runner are wrapped with `details.phase = "bundle_request"`.
- Docs now describe `run-task` as the preferred automation entrypoint and `bundle-request` as explicit refresh/manual handoff.

## Verification

- `python3 -m unittest tests.test_maintenance_task_runner -v` passed.
- `python3 -m unittest tests.test_wikify_cli tests.test_maintenance_task_runner -v` passed.
- `python3 -m unittest discover -s tests -v` passed: 177 tests.
- `python3 -m compileall -q wikify` passed.
- Temp-KB smoke passed:
  - `wikify run-task --dry-run` reported request paths and wrote no artifacts.
  - `wikify run-task` without bundle wrote proposal, lifecycle event, and bundle request.
  - After adding the bundle, `wikify run-task` applied the patch and marked the task done.
- `rg -n "run-task|bundle-request|patch_bundle_request|graph-patch-bundle-requests|waiting_for_patch_bundle" README.md LLM-Wiki-Cli-README.md scripts/fokb_protocol.md` confirmed docs describe the flow.

## Deviations from Plan

None - plan executed as written.

## Self-Check: PASSED

Phase 10 meets HND-01 through HND-05. The main automation loop now prepares the external-agent handoff artifact automatically without introducing hidden provider calls or semantic content generation.
