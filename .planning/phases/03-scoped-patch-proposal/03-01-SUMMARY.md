---
phase: 03-scoped-patch-proposal
plan: 01
subsystem: maintenance
tags: [wikify, graph, patch-proposal, agent-tasks]
provides:
  - Scoped patch proposal module
  - `wikify propose` CLI command
  - Write-scope validation for proposal paths
  - Structured proposal errors
affects: [wikify-propose, graph-maintenance]
tech-stack:
  added: []
  patterns: [stdlib-json-artifacts, argparse-subcommand, unittest, write-scope-preflight]
key-files:
  created:
    - wikify/maintenance/proposal.py
    - tests/test_maintenance_proposal.py
  modified:
    - wikify/cli.py
    - tests/test_wikify_cli.py
    - README.md
    - LLM-Wiki-Cli-README.md
    - scripts/fokb_protocol.md
key-decisions:
  - "`wikify propose` generates proposal artifacts but does not apply patches."
  - "`--dry-run` returns proposal JSON without writing `graph-patch-proposals`."
  - "Every planned edit path must be inside the source task `write_scope`."
duration: 1-session
completed: 2026-04-28
---

# Phase 3: Scoped Patch Proposal Summary

`wikify propose --task-id <id>` now converts one queued graph agent task into an auditable patch proposal artifact.

## Performance
- **Duration:** 1 session
- **Tasks:** 5 completed
- **Files modified:** 12

## Accomplishments
- Added `wikify.maintenance.proposal`.
- Added `wikify propose --task-id <id> [--dry-run]`.
- Added proposal artifacts at `sorted/graph-patch-proposals/<task-id>.json`.
- Added write-scope validation before proposal artifacts are written.
- Added structured errors:
  - `agent_task_queue_missing`
  - `agent_task_not_found`
  - `proposal_write_scope_missing`
  - `proposal_out_of_scope`
  - `proposal_path_invalid`
- Documented the maintain -> tasks -> propose automation loop.

## Task Commits
1. **Implementation and docs** - `e4285c8`

## Files Created/Modified
- `wikify/maintenance/proposal.py` - Builds and writes scoped patch proposal artifacts.
- `tests/test_maintenance_proposal.py` - Covers proposal build/write, dry-run-style no-write behavior, missing write scope, and out-of-scope paths.
- `wikify/cli.py` - Adds `propose` command and structured error mapping.
- `tests/test_wikify_cli.py` - Covers parser, artifact write, dry-run, missing queue, and proposal errors.
- `README.md` - Adds proposal quick examples and safety rule.
- `LLM-Wiki-Cli-README.md` - Adds scoped patch proposal product section.
- `scripts/fokb_protocol.md` - Documents command, schema, and error contract.

## Verification
- `python3 -m unittest tests.test_maintenance_proposal -v` passed with 4 tests.
- `python3 -m unittest tests.test_wikify_cli -v` passed with 16 tests.
- `python3 -m unittest discover -s tests -v` passed with 135 tests.
- Manual smoke passed:
  - `wikify tasks --refresh`
  - `wikify propose --task-id agent-task-1`
  - `wikify propose --task-id agent-task-1 --dry-run`
  - Verified proposal artifact exists after normal run.
  - Verified task status remains `queued`.

## Decisions & Deviations
- GSD SDK remains unavailable in PATH, so GSD files were maintained manually.
- Proposal artifacts do not contain executable patches yet; they carry planned edits and preflight metadata for later lifecycle/apply phases.
- `propose` intentionally does not mutate task status. Phase 4 should introduce explicit lifecycle transitions.

## Next Phase Readiness
Phase 4 should add durable task lifecycle commands and append-only events now that `proposed` has a concrete artifact to reference.
