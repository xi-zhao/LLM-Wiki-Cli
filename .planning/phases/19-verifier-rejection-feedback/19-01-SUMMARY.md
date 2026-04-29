---
phase: 19-verifier-rejection-feedback
plan: 01
status: complete
completed_at: 2026-04-29
requirements:
  - VRF-01
  - VRF-02
  - VRF-03
  - VRF-04
  - VRF-05
  - VRF-06
  - VRF-07
---

# Phase 19 Summary: Verifier Rejection Feedback

## What Changed

- Extended task lifecycle actions with optional event `details`.
- Persisted verifier rejection metadata on blocked tasks as `blocked_feedback`.
- Cleared stale `blocked_feedback` on `retry` and `restore`.
- Updated `run-task` so `patch_bundle_verification_rejected` blocks the selected task after the verifier writes its audit artifact.
- Added lifecycle artifact paths to rejection error details: `agent_tasks` and `task_events`.
- Documented blocked feedback, retry behavior, and inspection paths.

## Contract

- Standalone `verify-bundle` still writes `sorted/graph-patch-verifications/<task-id>.json` and returns `patch_bundle_verification_rejected` when `accepted: false`.
- When rejection occurs inside `run-task` automation, Wikify marks the task `blocked`.
- Task `blocked_feedback` and the block event `details` include verifier summary, findings, verdict, and verification path.
- Content stays unchanged and no patch application record is written.
- `tasks --id <id> --retry` and `--restore` move work back to `queued` and clear stale rejection feedback.

## Verification

- Focused red/green check: new tests failed before implementation with missing `details` support and proposed-state rejection behavior.
- `python3 -m unittest tests.test_maintenance_task_lifecycle tests.test_maintenance_task_runner tests.test_maintenance_batch_runner -v` passed.
- `python3 -m unittest discover -s tests -v` passed: 235 tests.
- `python3 -m compileall -q wikify` passed.
- Docs grep passed for `blocked_feedback`, `patch_bundle_verification_rejected`, `verification_path`, `agent_tasks`, and `task_events`.
- CLI smoke passed: rejecting verifier returned exit code 2, task status `blocked`, lifecycle actions `mark_proposed` then `block`, content unchanged, no application record, verification artifact written.

## Decisions

- Rejection feedback is stored under `blocked_feedback` instead of overloading the verifier artifact.
- The runner blocks only explicit verifier rejections; verifier command failures, timeouts, and invalid output remain verifier errors without task-block feedback.
- Retry and restore intentionally clear stale block feedback so repaired attempts start from current evidence.
