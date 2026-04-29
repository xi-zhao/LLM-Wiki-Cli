# Phase 23: Incremental Sync And Ingest Queue - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 23-incremental-sync-and-ingest-queue
**Areas discussed:** command boundary, source item granularity, freshness and classification, artifacts, queue semantics, registry updates

---

## Command Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| `wikify sync` | Top-level command that scans registered sources and writes sync/queue artifacts. Best fit for workflow action. | Yes |
| `wikify source sync` | Keeps all source operations under `source`, but makes sync look like registry CRUD. | |
| Reuse `wikify ingest` | Would blur sync discovery with actual ingest/wikiization. | |

**Selected:** `wikify sync`
**Notes:** Selected by the agent as the recommended default because the user previously asked for low-interruption automation and Phase 23 is a workflow step, not a registry edit. The command must not call existing ingest scripts or hidden providers.

---

## Source Item Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| One item per registered source only | Simpler, but cannot classify changed files inside directories. | |
| Deterministic child source items | Enables directory/file-level change detection and stable queue handoff. | Yes |
| Full wiki object model now | Too early; belongs to Phase 24 and Phase 25. | |

**Selected:** Deterministic child source items.
**Notes:** File and note sources produce one item. Directory and local repository sources recursively produce file items with deterministic ordering and default ignores. URL and remote repository sources produce one non-networked item.

---

## Freshness And Classification

| Option | Description | Selected |
|--------|-------------|----------|
| Stat metadata only | Cheap and simple, but misses rare same-size/same-mtime content changes. | |
| Bounded content hash plus stat metadata | More robust while still protecting performance on large files. | Yes |
| Always hash all files | More robust but can be expensive for personal knowledge folders. | |

**Selected:** Bounded content hash plus stat metadata.
**Notes:** Regular files below a default cap get `sha256`; larger files use stat metadata and record `hash_status: "skipped_size_limit"`. Remote locators remain `network_checked: false`.

---

## Artifacts

| Option | Description | Selected |
|--------|-------------|----------|
| `.wikify/sync/` and `.wikify/queues/` | Keeps control-plane state internal while giving agents stable artifact paths. | Yes |
| Visible `artifacts/` directory | More visible to humans, but sync queues are internal workflow state. | |
| Legacy `sorted/` artifacts | Reuses existing convention but keeps v0.2 tied to old project-only layout. | |

**Selected:** `.wikify/sync/source-items.json`, `.wikify/sync/last-sync.json`, and `.wikify/queues/ingest-items.json`.
**Notes:** Current-state JSON files are preferred over append-only history in this phase.

---

## Queue Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Queue only `new` and `changed` items | Keeps queue focused on pending wikiization. | Yes |
| Queue missing/error items too | Could enable repair workflows, but mixes maintenance concerns into ingest queue. | |
| Queue every item every time | Simple but violates incremental behavior. | |

**Selected:** Queue only `new` and `changed` items.
**Notes:** Missing, skipped, and errored items belong in sync status artifacts for now. Later maintenance phases can decide how to turn them into tasks.

---

## Registry Updates

| Option | Description | Selected |
|--------|-------------|----------|
| Update source-level sync metadata | Lets `source show/list` reflect sync state without reading every item. | Yes |
| Keep registry immutable after add | Simpler but hides useful status from users and agents. | |
| Move all sync state into registry | Creates a bulky registry and weakens separation from item index. | |

**Selected:** Update source-level sync metadata.
**Notes:** Registry gets `last_sync_status`, `last_synced_at`, `last_sync_summary`, and `last_sync_errors`; durable per-item state lives in `.wikify/sync/source-items.json`.

---

## the agent's Discretion

- Exact sync module/function names.
- Exact default hash size cap.
- Exact schema field ordering, provided tests lock deterministic behavior.
- Exact error code names for corrupt sync artifacts and scan failures.

## Deferred Ideas

- URL fetch and remote repository clone/pull.
- Wikiization/page generation.
- Human view generation.
- Agent context exports.
- File watching/background sync.
- Append-only sync history or SQLite-backed state.
