---
phase: 20-verifier-repair-automation
plan: 01
status: complete
completed_at: 2026-04-29
requirements:
  - RPR-01
  - RPR-02
  - RPR-03
  - RPR-04
  - RPR-05
  - RPR-06
  - RPR-07
---

# Phase 20 Summary: Verifier Repair Automation

## What Changed

- Added `repair_context` to patch bundle requests.
- Loaded repair feedback from task `blocked_feedback`, latest block lifecycle event, or runner-provided repair feedback.
- Let `run-task --agent-command` repair verifier-blocked tasks by retrying lifecycle state and regenerating the default bundle.
- Forced explicit repair runs to overwrite the previous rejected default bundle instead of reusing it.
- Verified batch repair by selecting `--status blocked` through the existing `run-tasks` path.
- Documented repair requests, stale bundle replacement, and explicit command boundaries.

## Contract

- Repair still requires an explicit producer command/profile.
- Verifier still requires an explicit verifier command/profile.
- Repair requests carry verifier summary, findings, verdict, and instructions for the producer.
- Accepted repair bundles must pass verifier and deterministic apply before `mark_done`.
- Rejected repair attempts leave content unchanged, write no application record, and persist fresh blocked feedback.

## Verification

- Focused red/green check: new tests failed before implementation on missing `repair_context`, blocked-to-done lifecycle, and stale rejected bundle reuse.
- `python3 -m unittest tests.test_maintenance_bundle_request tests.test_maintenance_task_runner tests.test_maintenance_batch_runner -v` passed.
- `python3 -m unittest discover -s tests -v` passed: 240 tests.
- `python3 -m compileall -q wikify` passed.
- Docs grep passed for `repair_context`, verifier-blocked repair, `--status blocked`, and RPR requirements.
- CLI smoke passed: verifier-blocked task repaired with explicit producer/verifier commands, old rejected bundle overwritten, request carried `repair_context`, content changed only after accepted verification, task marked `done`.

## Decisions

- `repair_context` is carried in the request instead of inventing a separate repair artifact.
- The runner preserves the explicit external command boundary; it does not choose a provider or retry policy.
- Repair mode is only activated for verifier-blocked tasks with an explicit producer command.
