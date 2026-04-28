---
phase: 17-maintenance-loop-automation
plan: 01
status: complete
completed_at: 2026-04-29
requirements:
  - MLP-01
  - MLP-02
  - MLP-03
  - MLP-04
  - MLP-05
  - MLP-06
  - MLP-07
  - MLP-08
---

# Phase 17 Summary: Maintenance Loop Automation

## What Changed

- Added `wikify.maintenance-loop.v1` through `wikify/maintenance/maintain_loop.py`.
- Added `wikify maintain-loop` CLI support with `--max-rounds`, `--task-budget`, `--limit`, `--agent-command`, `--agent-profile`, `--continue-on-error`, and `--dry-run`.
- Kept loop execution as a composition of `run_maintenance_workflow`, preserving existing proposal, request, producer, preflight, apply, rollback, and lifecycle boundaries.
- Added aggregate loop output with `stop_reason`, per-round results, summary counts, artifacts, and next actions.
- Documented loop behavior, stop reasons, conservative defaults, and explicit external-agent boundaries.

## Stop Conditions

- `no_tasks`
- `waiting_for_patch_bundle`
- `failed_tasks`
- `task_budget_exhausted`
- `max_rounds_reached`
- `dry_run_preview`

## Verification

- `python3 -m unittest tests.test_maintenance_maintain_loop tests.test_wikify_cli -v` passed.
- `python3 -m unittest discover -s tests -v` passed: 223 tests.
- `python3 -m compileall -q wikify` passed.
- Manual smoke passed for `maintain-loop --agent-profile` with a default profile:
  - exit code 0
  - status `completed`
  - stop reason `no_tasks`
  - round count 2
  - content repaired

## Decisions

- Dry-run runs one preview round only, because looping dry-run would replay the same in-memory task queue without changing artifacts.
- Task budget counts selected tasks, not only completed tasks, so waiting/failing tasks still consume loop budget.
- The loop stops on failed or waiting states instead of trying to invent recovery behavior.
- Default profiles remain explicit shorthand; configuring a default alone does not trigger external execution.
