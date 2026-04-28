# Phase 14 Summary: Maintenance Run Automation

## Outcome

Completed `wikify maintain-run`, a one-command maintenance automation entrypoint that refreshes graph maintenance artifacts and advances a bounded task batch through the existing audited runner.

## Delivered

- Added `wikify.maintenance-run.v1` result schema via `wikify/maintenance/maintain_run.py`.
- Added `wikify maintain-run` CLI command with policy, status, action, id, limit, agent command, producer timeout, continue-on-error, and dry-run flags.
- Preserved conservative defaults: balanced policy, queued status, limit 5, sequential execution, and stop-on-error.
- Kept `--agent-command` explicit; no provider, model, key, retry, or hidden LLM behavior was added.
- Implemented dry-run preview from the fresh in-memory maintenance task queue so stale on-disk queues do not mislead automation.
- Added phase-aware structured errors for maintenance refresh and batch execution failures.
- Updated README, product docs, protocol docs, and GSD planning files.

## Verification

- `python3 -m unittest tests.test_maintenance_maintain_run -v`
- `python3 -m unittest tests.test_wikify_cli tests.test_maintenance_maintain_run -v`
- `python3 -m unittest discover -s tests -v`
- `python3 -m compileall -q wikify`
- Temp sample KB smoke: `maintain-run --action queue_link_repair --limit 1 --agent-command ...` completed one task, marked it `done`, and applied the patch.

## Requirement Coverage

- MRA-01: Complete
- MRA-02: Complete
- MRA-03: Complete
- MRA-04: Complete
- MRA-05: Complete
- MRA-06: Complete
- MRA-07: Complete

## Notes

`maintain-run` is intentionally a composition layer. It does not add new patch semantics, concurrency, approval prompts, or hidden provider execution. Future provider-backed generation should remain a separate explicit phase.
