# Phase 28-03 Summary

## Result

Completed - Generated wiki page repair flows now carry preservation context and deterministic local checks prevent `source_refs` or `review_status` loss before apply.

## Commit

- `3805e8f` `feat(28-03): enforce generated page preservation`

## Files Changed

- `wikify/maintenance/preservation.py`
- `wikify/maintenance/proposal.py`
- `wikify/maintenance/bundle_request.py`
- `wikify/maintenance/bundle_verifier.py`
- `wikify/maintenance/patch_apply.py`
- `tests/test_maintenance_generated_page_preservation.py`
- `tests/test_maintenance_bundle_request.py`
- `tests/test_maintenance_bundle_verifier.py`
- `tests/test_maintenance_patch_apply.py`
- `tests/test_maintenance_task_runner.py`

## Behavior Delivered

- Added `wikify.generated-page-preservation.v1` context for generated wiki page repair proposals.
- Added bundle-request safety metadata and explicit producer instructions for preserving generated page `source_refs` and `review_status`.
- Added deterministic preflight/apply checks that simulate `replace_text` operations and reject metadata loss with `generated_page_preservation_failed`.
- Ensured verifier flow fails preservation violations before external verifier commands run.
- Kept repair feedback compatible so blocked tasks can be retried with preservation constraints still present.

## Verification

Recorded in `28-03-VERIFICATION.md`.

## Self-Check

MAINT-03 is complete. Generated page source traceability and review state are now protected locally, independent of external verifier quality.
