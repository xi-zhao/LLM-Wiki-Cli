---
phase: 18-agent-verifier-gate
plan: 01
status: complete
completed_at: 2026-04-29
requirements:
  - VFG-01
  - VFG-02
  - VFG-03
  - VFG-04
  - VFG-05
  - VFG-06
  - VFG-07
  - VFG-08
---

# Phase 18 Summary: Agent Verifier Gate

## What Changed

- Added `wikify/maintenance/bundle_verifier.py`.
- Added standalone `wikify verify-bundle`.
- Added verifier gate support to `run-task`, `run-tasks`, `maintain-run`, and `maintain-loop`.
- Added `--verifier-command`, `--verifier-profile`, and `--verifier-timeout`.
- Added verification audit artifacts at `sorted/graph-patch-verifications/<task-id>.json`.
- Documented verifier request and verdict schemas.

## Contract

- Wikify runs deterministic patch preflight before verifier execution.
- Verifier receives `wikify.patch-bundle-verification-request.v1` JSON on stdin.
- Verifier returns `wikify.patch-bundle-verdict.v1` JSON on stdout.
- `accepted: true` allows apply to continue.
- `accepted: false` writes an audit artifact and blocks apply with `patch_bundle_verification_rejected`.

## Verification

- `python3 -m unittest tests.test_maintenance_bundle_verifier tests.test_maintenance_task_runner tests.test_maintenance_batch_runner tests.test_maintenance_maintain_run tests.test_maintenance_maintain_loop tests.test_wikify_cli -v` passed.
- `python3 -m unittest discover -s tests -v` passed: 233 tests.
- `python3 -m compileall -q wikify` passed.
- `git diff --check` passed.
- Accepted verifier smoke passed: exit code 0, status `completed`, content changed, verification artifact written, application record written.
- Rejected verifier smoke passed: exit code 2, error `patch_bundle_verification_rejected`, content unchanged, verification artifact written, no application record.

## Decisions

- Verifier profiles reuse the existing visible `wikify-agent-profiles.json` store.
- A configured default profile still does nothing unless `--verifier-profile` is explicitly present.
- Rejection is a structured blocking error instead of an apply-time warning.
- Dry-run builds request/preflight context but never executes verifier commands.
