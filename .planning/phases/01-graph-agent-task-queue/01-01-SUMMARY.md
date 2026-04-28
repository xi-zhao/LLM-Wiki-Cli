---
phase: 01-graph-agent-task-queue
plan: 01
subsystem: maintenance
tags: [wikify, graph, maintenance, agent-task-queue]
provides:
  - Deterministic graph agent task queue generation
  - Runner integration for graph-agent-tasks.json
  - Protocol documentation for downstream agents
affects: [wikify-maintain, graph-maintenance]
tech-stack:
  added: []
  patterns: [stdlib-json-artifacts, unittest, gsd-manual-fallback]
key-files:
  created:
    - wikify/maintenance/task_queue.py
    - tests/test_maintenance_task_queue.py
  modified:
    - wikify/maintenance/runner.py
    - tests/test_maintenance_runner.py
    - README.md
    - LLM-Wiki-Cli-README.md
    - scripts/fokb_protocol.md
key-decisions:
  - "Generate agent tasks from queued execution classifications, not from executed or skipped steps."
  - "For dry-run, return task queue preview but do not write sorted/graph-agent-tasks.json."
  - "Keep CLI free of hidden LLM calls and content-page edits."
duration: 1-session
completed: 2026-04-28
---

# Phase 1: Graph Agent Task Queue Summary

`wikify maintain` now produces deterministic agent task queue data for queued graph maintenance work.

## Performance
- **Duration:** 1 session
- **Tasks:** 5 completed
- **Files modified:** 11

## Accomplishments
- Added `wikify.maintenance.task_queue.build_task_queue()`.
- Integrated `task_queue` into `run_maintenance()`.
- Added `sorted/graph-agent-tasks.json` for normal maintain runs.
- Preserved dry-run behavior: graph artifacts only, task preview in result, no sorted task artifact.
- Documented the artifact and V1 no-content-edit/no-hidden-LLM safety rule.

## Task Commits
1. **GSD initialization** - `90e3160`
2. **Phase plan** - `6abe149`
3. **Task queue builder** - `0f4aeb4`
4. **Runner integration** - `997186b`
5. **Protocol docs** - `332c80c`

## Files Created/Modified
- `wikify/maintenance/task_queue.py` - Converts queued maintenance execution results into agent task packets.
- `tests/test_maintenance_task_queue.py` - Covers the task queue contract.
- `wikify/maintenance/runner.py` - Writes `graph-agent-tasks.json` and returns task queue preview.
- `tests/test_maintenance_runner.py` - Verifies normal and dry-run artifact behavior.
- `README.md` - Documents the artifact for quickstart users.
- `LLM-Wiki-Cli-README.md` - Documents product behavior and task queue semantics.
- `scripts/fokb_protocol.md` - Documents schema and protocol contract.

## Verification
- `python3 -m unittest discover -s tests -v` passed with 119 tests.
- Manual smoke passed:
  - `maintain --dry-run` writes graph artifacts and does not write `sorted/graph-agent-tasks.json`.
  - `maintain` writes findings, plan, agent tasks, and history artifacts.

## Decisions & Deviations
- GSD SDK was unavailable in PATH, so GSD project files were maintained manually.
- Dry-run task previews are generated from a non-writing execution classification while the actual execution result remains dry-run.

## Next Phase Readiness
The next useful phase is an agent task consumer: read `sorted/graph-agent-tasks.json`, inspect bounded write scopes, produce proposed patches, and keep semantic edits separate from deterministic bookkeeping.
