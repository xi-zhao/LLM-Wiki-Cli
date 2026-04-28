---
phase: 02-agent-task-reader
plan: 01
subsystem: maintenance
tags: [wikify, agent-tasks, cli, maintenance]
provides:
  - Read-only graph agent task reader module
  - `wikify tasks` CLI command
  - Structured missing-queue and missing-task errors
affects: [wikify-tasks, graph-maintenance]
tech-stack:
  added: []
  patterns: [stdlib-json-artifacts, argparse-subcommand, unittest]
key-files:
  created:
    - wikify/maintenance/task_reader.py
    - tests/test_maintenance_task_reader.py
  modified:
    - wikify/cli.py
    - tests/test_wikify_cli.py
    - README.md
    - LLM-Wiki-Cli-README.md
    - scripts/fokb_protocol.md
key-decisions:
  - "`wikify tasks` is read-only by default."
  - "`--refresh` is the only task-reader path that runs maintain and writes artifacts."
  - "Task status mutation and patch application remain future phase work."
duration: 1-session
completed: 2026-04-28
---

# Phase 2: Agent Task Reader Summary

`wikify tasks` now gives downstream agents a stable way to read, filter, and inspect graph agent tasks.

## Performance
- **Duration:** 1 session
- **Tasks:** 5 completed
- **Files modified:** 10

## Accomplishments
- Added `wikify.maintenance.task_reader`.
- Added `wikify tasks` with `--status`, `--action`, `--id`, `--limit`, `--refresh`, and `--policy`.
- Added structured errors:
  - `agent_task_queue_missing`
  - `agent_task_not_found`
  - `invalid_agent_task_query`
- Documented command behavior and read-only safety boundary.

## Task Commits
1. **Phase added** - `8d04a6a`
2. **Phase plan** - `bdb9148`
3. **Task reader** - `799b5b8`
4. **CLI wiring** - `4bd3409`
5. **Docs** - `7f2aec3`

## Files Created/Modified
- `wikify/maintenance/task_reader.py` - Loads and filters `graph-agent-tasks.json`.
- `tests/test_maintenance_task_reader.py` - Covers loading, filtering, limits, and typed errors.
- `wikify/cli.py` - Adds `tasks` command.
- `tests/test_wikify_cli.py` - Covers parser, list, refresh, and missing queue behavior.
- `README.md` - Adds quick examples.
- `LLM-Wiki-Cli-README.md` - Describes Agent Task Reader semantics.
- `scripts/fokb_protocol.md` - Documents protocol and error contract.

## Verification
- `python3 -m unittest discover -s tests -v` passed with 126 tests.
- Manual smoke passed:
  - `wikify tasks --refresh`
  - `wikify tasks --status queued --limit 1`
  - `wikify tasks --id agent-task-1`

## Decisions & Deviations
- GSD SDK remains unavailable in PATH, so GSD files were maintained manually.
- The reader does not mutate task status in V1; mutation would require stronger state semantics.

## Next Phase Readiness
The next useful phase is safe patch proposal: read one queued task, inspect only its write scope, and emit a patch proposal artifact without applying it automatically.
