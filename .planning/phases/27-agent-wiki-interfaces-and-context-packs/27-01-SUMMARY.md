# Phase 27-01 Summary

## Result

Completed - `wikify agent export` now generates durable agent-facing exports from the existing wiki object model.

## Commits

- `fbede56` `test(27-01): add failing agent export tests`
- `d378927` `feat(27-01): implement agent export indexes`
- `e184851` `test(27-01): add failing agent export CLI tests`
- `85a97a9` `feat(27-01): wire agent export CLI`

## Files Changed

- `wikify/agent.py`
- `wikify/cli.py`
- `tests/test_agent.py`
- `tests/test_wikify_cli.py`

## Behavior Shipped

- Added `wikify.agent-export.v1` export report generation.
- Added `llms.txt` and `llms-full.txt`.
- Added `artifacts/agent/page-index.json`, `citation-index.json`, `related-index.json`, and `graph.json`.
- Added `.wikify/agent/last-agent-export.json`.
- Wired `wikify agent export` with JSON envelope command name `agent.export`.
- Preserved explicit command boundaries: export does not run sync, wikiize, views, graph, providers, embeddings, or vector stores.

## Deviations

None. Implementation followed the planned export/index scope.

## Self-Check

The export path is object-model-first, source-backed, validation-gated on writes, and compatible with the later context/cite/related query work.
