# Summary: Build Deterministic Patch Apply And Rollback

## Plan

- Phase: 07-patch-apply-and-rollback-contract
- Plan: 07-01
- Plan commit: `bdff734`
- Implementation commit: `6ebfd5f`
- Documentation commit: `4f6f0d3`
- Status: Complete

## What Changed

- Added `wikify.maintenance.patch_apply` with patch bundle preflight, deterministic apply, audit record writing, and rollback.
- Added `wikify apply --proposal-path ... --bundle-path ... [--dry-run]`.
- Added `wikify rollback --application-path ... [--dry-run]`.
- Limited V1.2 operations to deterministic `replace_text` with exact-once matching and one operation per path.
- Wrote application records under `sorted/graph-patch-applications/<application-id>.json` with before/after hashes and rollback guard metadata.
- Updated README, product README, and protocol docs with patch bundle, application, and rollback contracts.

## Verification

- `python3 -m unittest tests.test_maintenance_patch_apply -v` passed.
- `python3 -m unittest tests.test_wikify_cli -v` passed.
- `python3 -m unittest discover -s tests -v` passed: 160 tests.
- Temp-KB smoke passed:
  - `wikify apply --dry-run` validated without writing content or application records.
  - `wikify apply` changed content and wrote an application record.
  - `wikify rollback --dry-run` validated rollback without changing content.
  - `wikify rollback` restored original content and marked the application record rolled back.
- `rg -n "patch bundle|graph-patch-applications|rollback|replace_text|wikify apply" README.md LLM-Wiki-Cli-README.md scripts/fokb_protocol.md` confirmed all docs mention the contract.

## Deviations from Plan

- Added an extra guard beyond the initial plan: V1.2 rejects multiple operations for the same path with `patch_operation_conflict`. This prevents partial application and keeps rollback hashes simple until a future sequential multi-op contract is designed.

## Self-Check: PASSED

Phase 7 meets APP-01 through APP-06. The graph maintenance loop now has queue, read, propose, lifecycle, relevance, purpose rationale, deterministic apply, and hash-guarded rollback surfaces.
