# Phase 23: Incremental Sync And Ingest Queue - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 23 consumes the Phase 22 source registry and adds deterministic source sync. It detects source item states, updates source-level sync metadata, and writes machine-readable sync status plus ingest queue artifacts for later wikiization.

This phase does not fetch remote URL contents, clone repositories, call LLM providers, run existing `wikify ingest`, generate wiki pages, generate human views, build graph artifacts, export agent context, or mutate generated wiki content.

</domain>

<decisions>
## Implementation Decisions

### Command Boundary

- **D-01:** Add a top-level `wikify sync` command for source discovery and ingest queue creation.
- **D-02:** `wikify sync` defaults to all registered sources and supports `--source <source_id>` for a single-source run.
- **D-03:** `wikify sync --dry-run` returns the same planned classification and artifacts metadata but writes nothing.
- **D-04:** `wikify sync` must not call `wikify ingest`, `scripts/ingest_any_url.py`, external agents, providers, network fetchers, or repository clone/update commands.
- **D-05:** The command result uses the existing Wikify JSON envelope and includes summary counts by source status, item status, queued item count, skipped item count, and error count.

### Source Item Model

- **D-06:** Introduce source items as deterministic child records of registered sources. Source ids remain opaque `src_<uuid>`, while source item ids are deterministic from `source_id` plus canonical item locator.
- **D-07:** Source item id shape should be stable and compact, such as `item_<sha256-prefix>`, where the hash input includes source id, item type, and canonical item locator.
- **D-08:** A `file` source creates one source item for the file itself.
- **D-09:** A `note` source creates one source item for the Markdown note itself, using the same filesystem mechanics as `file` but preserving semantic item/source type.
- **D-10:** A `directory` source recursively discovers regular files under the source root in deterministic sorted order.
- **D-11:** Directory sync excludes hidden/internal and dependency-heavy directories by default: `.git`, `.wikify`, `__pycache__`, `node_modules`, `.venv`, `venv`, `dist`, `build`, and generated workspace directories when they are nested under the source root.
- **D-12:** Directory sync records skipped files/directories in status artifacts but does not put skipped items into the ingest queue.
- **D-13:** A local `repository` source is treated as a directory-like source with `.git` excluded and `git_dir_exists` metadata preserved; Phase 23 does not shell out to `git`.
- **D-14:** A remote `repository` source is represented as one unverified remote item. It is not cloned or queried in Phase 23.
- **D-15:** A `url` source is represented as one URL item based on the canonical locator. It is not fetched in Phase 23.

### Freshness And Classification

- **D-16:** Source item statuses are `new`, `changed`, `unchanged`, `missing`, `skipped`, and `errored`.
- **D-17:** New items are items discovered in the current sync that did not exist in the previous source item index.
- **D-18:** Changed items are items whose deterministic fingerprint differs from the previous index.
- **D-19:** Unchanged items are items whose fingerprint matches the previous index and therefore should not be queued for wikiization.
- **D-20:** Missing items are previously indexed local items that are no longer present.
- **D-21:** Skipped items are intentionally excluded by ignore rules, size/hash limits, unsupported kinds, or future config limits.
- **D-22:** Errored items carry per-item error records and do not abort unrelated source items or sources.
- **D-23:** Local file fingerprints include cheap stat metadata: exists, kind, size_bytes, mtime_ns, inode, and device where available.
- **D-24:** For regular local files, compute `sha256` only when the file size is below a bounded default cap. Large files retain stat fingerprints and include `hash_status: "skipped_size_limit"`.
- **D-25:** Remote URL and remote repository fingerprints remain deterministic and non-networked: canonical locator hash plus `network_checked: false`.
- **D-26:** Repeated syncs must be stable: once a new or changed item has been indexed and queued, the next sync classifies it as unchanged if its fingerprint has not changed.

### Artifacts

- **D-27:** Store Phase 23 control artifacts under `.wikify/`, not visible human wiki directories.
- **D-28:** Write the current source item index to `.wikify/sync/source-items.json` using schema `wikify.source-items.v1`.
- **D-29:** Write the latest sync run report to `.wikify/sync/last-sync.json` using schema `wikify.sync-run.v1`.
- **D-30:** Write the ingest queue to `.wikify/queues/ingest-items.json` using schema `wikify.ingest-queue.v1`.
- **D-31:** Artifact writes use temp file plus atomic replace, following the Phase 22 registry pattern.
- **D-32:** Artifact ordering is deterministic: sources sorted by `source_id`, source items sorted by source id then relative path or canonical locator, queue entries sorted by deterministic item id.
- **D-33:** `source-items.json` is the durable item state used for later change detection.
- **D-34:** `last-sync.json` is the human/agent readable summary of the most recent sync operation.
- **D-35:** `ingest-items.json` contains pending wikiization work for later phases; Phase 23 creates the queue but does not consume it.

### Queue Semantics

- **D-36:** Queue entries are created for `new` and `changed` source items only.
- **D-37:** Missing, skipped, and errored items are recorded in sync status artifacts, not queued for wikiization in Phase 23.
- **D-38:** Queue entries include `queue_id`, `source_id`, `item_id`, `item_status`, `locator`, `relative_path` when applicable, fingerprint, evidence, `status: "queued"`, `requires_user: false`, and acceptance checks for later wikiization.
- **D-39:** Re-running sync should not duplicate queue entries for unchanged items.
- **D-40:** If a queued item is still pending and the source item changes again, planning may either update the existing queue entry deterministically or replace it, but the final artifact must contain only one active queue entry per source item.

### Registry Updates

- **D-41:** Non-dry-run sync updates each affected source record with source-level sync metadata: `last_sync_status`, `last_synced_at`, `last_sync_summary`, and `last_sync_errors`.
- **D-42:** Source-level `last_sync_status` values should include `synced`, `sync_errors`, `missing`, and existing `never_synced`.
- **D-43:** Source registry updates and sync artifact writes should be coordinated so a failed write does not leave an obviously inconsistent state. Prefer writing derived artifacts first, then registry metadata.

### the agent's Discretion

- Exact schema field ordering, as long as output is deterministic and tested.
- Exact default content hash cap, as long as it is bounded and documented in tests.
- Exact ignore list helper names and whether ignores live as constants or future config-ready structures.
- Exact error code names for source item scan failures, unsupported source item kinds, and corrupt sync artifact JSON.
- Whether `--source` accepts locator lookup in addition to `source_id`, as long as `source_id` is primary and stable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Direction

- `AGENTS.md` - Product positioning, human/agent view split, low-interruption automation direction, and Graphify/LLM Wiki lessons.
- `.planning/PROJECT.md` - Current v0.2.0 product positioning, constraints, active requirements, and key decisions.

### Phase Scope

- `.planning/ROADMAP.md` - Phase 23 goal, requirements, success criteria, dependencies, and verification expectations.
- `.planning/REQUIREMENTS.md` - Incremental ingest requirements `ING-01` through `ING-04`.
- `.planning/STATE.md` - Current GSD state, recent decisions, and Phase 22 completion context.

### Upstream Phase 22

- `.planning/phases/22-personal-wiki-workspace-and-source-registry/22-CONTEXT.md` - Locked workspace/source registry decisions that Phase 23 must respect.
- `.planning/phases/22-personal-wiki-workspace-and-source-registry/22-01-SUMMARY.md` - Phase 22 implementation summary and boundary confirmation.
- `.planning/phases/22-personal-wiki-workspace-and-source-registry/22-01-VERIFICATION.md` - Phase 22 verification evidence and residual Phase 23 risk.

### Existing Implementation Patterns

- `wikify/workspace.py` - Workspace manifest, registry loading, source record shape, atomic JSON write pattern, and source locator/fingerprint helpers.
- `wikify/cli.py` - Current command wiring and JSON envelope command handlers.
- `wikify/config.py` - Base discovery precedence: `WIKIFY_BASE`, `FOKB_BASE`, `wikify.json`, app root.
- `wikify/envelope.py` - Stable JSON envelope helpers.
- `wikify/maintenance/task_queue.py` - Existing deterministic queue artifact style for graph agent tasks.
- `wikify/maintenance/task_reader.py` - Existing queue reader and selection pattern.
- `scripts/source_index_manager.py` - Legacy Markdown table source index; useful context but not the Phase 23 registry/index model.
- `scripts/ingest_any_url.py` - Existing URL ingest behavior; Phase 23 must not call it from sync.
- `scripts/ingest_result_enricher.py` - Existing lifecycle/status vocabulary; useful for naming, but Phase 23 remains pre-wikiization.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `wikify.workspace.load_workspace`: use as the entry point for reading manifest and source registry before sync.
- `wikify.workspace.registry_path` and existing atomic write helper pattern: mirror for sync artifacts.
- `wikify.config.discover_base`: `wikify sync` should follow the same workspace discovery semantics as `source` commands.
- `wikify.envelope.envelope_ok` and `wikify.envelope.envelope_error`: use for `sync` command output.
- `wikify.maintenance.task_queue` and `task_reader`: use as style references for queue schema, summary, status filtering, and deterministic task shape.

### Established Patterns

- Commands return structured JSON envelopes by default; `print_output` handles output rendering centrally.
- Tests use `unittest`, temporary directories, and direct CLI invocation through `cli.main`.
- Existing automation avoids hidden provider calls and explicit producer/verifier boundaries are preserved.
- Graph agent task artifacts are current-state JSON files, not append-only logs; Phase 23 should use the same current-state approach for source item index and ingest queue.
- Phase 22 source registry is a single JSON file with atomic writes; Phase 23 should not introduce SQLite, JSONL event sourcing, or per-source files yet.

### Integration Points

- Add a focused sync module, likely `wikify/sync.py`, rather than extending legacy scripts.
- Wire `wikify sync` in `wikify/cli.py` next to workspace/source commands.
- Add focused tests in a new `tests/test_sync.py` plus CLI parser/command tests in `tests/test_wikify_cli.py`.
- Update docs and protocol with `wikify sync`, artifact schemas, statuses, and explicit no-ingest/no-fetch boundary.

</code_context>

<specifics>
## Specific Ideas

- Phase 23 should make the product feel like a reliable incremental scanner: add sources once, then run one command to know what changed.
- Queue/status artifacts should be useful to agents without needing to parse prose.
- The queue exists to hand off later wikiization work, not to execute wikiization now.
- Low user interruption means errors are recorded per item/source and the sync continues where possible.
- Source item identity should be stable enough for repeated agent runs, even when source contents change.

</specifics>

<deferred>
## Deferred Ideas

- Fetching URL contents belongs to explicit ingest or later provider/runtime phases, not Phase 23 sync.
- Cloning or pulling repositories belongs to a future explicit repository integration phase.
- Wiki page generation belongs to Phase 25.
- Human source pages and static views belong to Phase 26.
- Agent context exports, `llms.txt`, citation indexes, and context packs belong to Phase 27.
- File watching/background sync is a future capability.
- User-configurable ignore patterns and sync policies can be added after the default deterministic scanner is stable.
- Append-only sync history, JSONL event logs, and SQLite indexes are deferred until current-state JSON artifacts prove insufficient.

</deferred>

---

*Phase: 23-incremental-sync-and-ingest-queue*
*Context gathered: 2026-04-29*
