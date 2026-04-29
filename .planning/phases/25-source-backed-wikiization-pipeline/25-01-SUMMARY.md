# Phase 25 Plan 25-01 Summary: Source-Backed Wikiization Pipeline

**Completed:** 2026-04-29
**Status:** Complete

## Goal

Make the core product loop real: `wikify source add -> wikify sync -> wikify wikiize` turns queued source items into readable, source-backed Markdown pages and machine-readable wiki page objects without hidden provider calls.

## Delivered

- Added `wikify.wikiize` with schema constants, path helpers, typed errors, queue/source-item loading, selectors, dry-run planning, generated page/object writes, run reports, task queue writes, and strict object validation.
- Added deterministic local wikiization for text/Markdown source items: H1-or-filename title extraction, conservative summaries, source reference sections, bounded excerpts, and generated `wikify.wiki-page.v1` objects.
- Added generated page/object output paths under `wiki/pages/` and `artifacts/objects/wiki_pages/`, plus object index and validation report updates.
- Added queue lifecycle updates: completed queue entries record `completed_at`, generated object ids, and generated paths; blocked entries become `needs_review`.
- Added hash-guarded incremental updates so generated pages are updated only when the stored generated hash still matches current content.
- Added `.wikify/queues/wikiization-tasks.json` for drifted, remote-without-content, unsupported, unreadable, missing, or failed wikiization work.
- Added explicit external agent handoff with `wikify.wikiization-request.v1` and `wikify.wikiization-result.v1` artifacts, stdin JSON, result capture, timeout/error handling, and existing agent profile semantics.
- Added top-level `wikify wikiize` CLI command with `--dry-run`, `--queue-id`, `--item`, `--source`, `--limit`, `--agent-command`, `--agent-profile`, and `--timeout`.
- Updated README, Chinese README, and protocol docs with command usage, artifact paths, schemas, source traceability, edit protection, task routing, and hidden-provider boundaries.

## Requirements Closed

- `WIK-01`: `wikify wikiize` turns ingested source items into structured Markdown wiki pages.
- `WIK-02`: Generated pages and objects preserve source refs with source id, item id, locator/path evidence, fingerprint evidence, and confidence.
- `WIK-03`: Incremental wikiization safely updates generated pages and refuses user-edited drift.
- `WIK-04`: Remote-without-content, unsupported, unreadable, drifted, or failed transformations create wikiization review tasks instead of silent merges.
- `WIK-05`: External semantic enrichment uses explicit request/result artifacts and explicit command/profile flags, not hidden provider calls.

## Important Boundaries

- Phase 25 does not generate human home/source/topic/static views.
- Phase 25 does not export `llms.txt`, context packs, citation indexes, or agent query APIs.
- Phase 25 does not fetch remote URLs, clone repositories, call provider SDKs, or run background watchers.
- Legacy `wikify ingest` remains separate from the v0.2 queue-to-wiki command.
- Generated source refs are item-level unless precise spans are available; richer claim/citation extraction remains a later enhancement.

## Commits

- `c8bb355` test(25-01): add failing wikiization pipeline tests
- `a91cfbd` feat(25-01): implement wikiization pipeline core
- `8e17d9f` test(25-01): add failing wikiize CLI tests
- `610731c` feat(25-01): expose wikiize CLI command
- `770ea75` docs(25-01): document wikiization pipeline

## Deviations From Plan

- Tasks were committed as grouped TDD slices instead of one commit per numbered task because the wikiization module tests exercised multiple planned task behaviors together. The delivered behavior and verification coverage still maps to all planned tasks.

## Self-Check

PASSED. All planned product behaviors are implemented, documented, and verified with focused tests, full test discovery, and a command-level smoke flow.

## Next Phase

Start Phase 26: Human Wiki Views And Local Static Output.

Recommended next command: `$gsd-discuss-phase 26`
