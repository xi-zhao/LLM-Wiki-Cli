# Summary: Build Patch Bundle Request Contract

## Plan

- Phase: 09-patch-bundle-request-contract
- Plan: 09-01
- Plan commit: `7d0d8aa`
- Implementation commit: `4def9cb`
- Documentation commit: `bb983b2`
- Follow-up fix commit: `95c568d`
- Status: Complete

## What Changed

- Added `wikify.maintenance.bundle_request.build_bundle_request`.
- Added `wikify bundle-request --task-id <task-id> [--dry-run]`.
- Request artifacts use `wikify.patch-bundle-request.v1`.
- Non-dry-run writes `sorted/graph-patch-bundle-requests/<task-id>.json`.
- Non-dry-run writes the scoped proposal artifact if it is missing.
- Request artifacts include proposal context, write scope, target file snapshots, SHA-256 hashes, default bundle path, and the allowed `replace_text` patch bundle contract.
- `suggested_bundle_path` is reported separately from written artifacts so callers do not mistake a suggested output path for an existing file.
- Documented the external-agent request-to-bundle handoff in README, product README, and protocol docs.

## Verification

- `python3 -m unittest tests.test_maintenance_bundle_request -v` passed.
- `python3 -m unittest tests.test_maintenance_bundle_request tests.test_wikify_cli -v` passed.
- `python3 -m unittest discover -s tests -v` passed: 176 tests.
- Temp-KB smoke passed:
  - `wikify bundle-request --dry-run` wrote no request or proposal artifacts.
  - `wikify bundle-request` wrote request and proposal artifacts.
  - Task status stayed `queued`.
  - Target content stayed unchanged.
- `rg -n "bundle-request|patch-bundle-request|graph-patch-bundle-requests|wikify.patch-bundle.v1" README.md LLM-Wiki-Cli-README.md scripts/fokb_protocol.md` confirmed docs mention the contract.

## Deviations from Plan

None - plan executed as written.

## Self-Check: PASSED

Phase 9 meets BND-01 through BND-06. The low-interruption workflow now has a deterministic handoff from `waiting_for_patch_bundle` to an external agent that can produce an explicit patch bundle without hidden provider calls.
