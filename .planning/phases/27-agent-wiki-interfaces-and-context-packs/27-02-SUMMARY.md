# Phase 27-02 Summary

## Result

Completed - Agents can now request context packs, citation evidence, and related-object explanations through the `wikify agent` namespace.

## Commits

- `a36970a` `test(27-02): add failing agent query tests`
- `bf56607` `feat(27-02): implement agent query core`
- `0090f9c` `test(27-02): add failing agent query CLI tests`
- `d8eccea` `feat(27-02): wire agent query CLI`

## Files Changed

- `wikify/agent.py`
- `wikify/cli.py`
- `tests/test_agent.py`
- `tests/test_wikify_cli.py`

## Behavior Shipped

- Added `run_agent_context`, `query_agent_citations`, and `query_agent_related`.
- Added `wikify.context-pack-manifest.v1` and context pack manifest helpers.
- Added deterministic, budgeted `wikify.context-pack.v1` generation.
- Added context pack object writes under `artifacts/objects/context_packs/`.
- Added object-index refresh and strict validation after context pack object writes.
- Added citation query behavior that ranks explicit citation objects before page source-ref fallback evidence.
- Added related query behavior with signal maps for direct links, graph edges, shared sources, citation overlap, common neighbors, type affinity, and text matches.
- Wired `wikify agent context`, `wikify agent cite`, and `wikify agent related`.

## Deviations

The implementation recomputes indexes from the object snapshot for query commands instead of requiring pre-existing agent index files. This matches the plan's graceful optional-artifact degradation requirement.

## Self-Check

The query layer stays stdlib-only, deterministic, source-backed, and read-only except for explicit non-dry-run context pack generation.
