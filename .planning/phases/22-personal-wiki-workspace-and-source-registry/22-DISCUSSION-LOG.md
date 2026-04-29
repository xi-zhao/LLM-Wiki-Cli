# Phase 22: Personal Wiki Workspace And Source Registry - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 22-personal-wiki-workspace-and-source-registry
**Areas discussed:** Workspace Layout, Source Identity, Source Registration Scope, CLI Shape, Registry Artifact Format

---

## Workspace Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Manifest plus visible product directories | `wikify.json`, `.wikify/registry/sources.json`, `sources/`, `wiki/`, `artifacts/`, `views/` | Yes |
| Reuse legacy `topics/sources/sorted/articles` layout | Keep current historical directory conventions as the v0.2 workspace model | No |
| Hide all state and outputs under `.wikify/` | Make the workspace mostly internal and invisible | No |

**User's choice:** User asked for a product-and-algorithm advisor to decide the five gray areas. The advisor recommended manifest plus visible product directories, and this was adopted.
**Notes:** The selected layout separates user-visible product artifacts from internal control state.

---

## Source Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Opaque generated `source_id` | Generate stable ids at first registration and use `locator_key` only for duplicate detection | Yes |
| Locator-derived id | Hash or slug the locator to produce source identity | No |
| Content-derived id | Hash source content or fingerprint to produce source identity | No |
| User-defined slug | Let users choose ids manually | No |

**User's choice:** Delegated to advisor. The advisor recommended opaque immutable ids with separate locator-key duplicate detection, and this was adopted.
**Notes:** Stable ids are needed for future citations and agent references.

---

## Source Registration Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Bounded offline metadata | Register source and collect cheap local stat metadata only | Yes |
| Metadata only with no probing | Store only user input and type | No |
| Registration plus recursive discovery | Walk directories, hash content, create ingest queue | No |
| Registration plus network probing | Fetch URLs or query/clone repositories | No |

**User's choice:** Delegated to advisor. The advisor recommended bounded offline metadata only, and this was adopted.
**Notes:** Full sync and discovery are explicitly deferred to Phase 23.

---

## CLI Shape

| Option | Description | Selected |
|--------|-------------|----------|
| `wikify init` plus `wikify source add/list/show` | Use top-level init and a singular source namespace | Yes |
| `wikify add` | Use a short top-level add command for source registration | No |
| `wikify sources ...` | Use plural source namespace | No |
| `wikify registry ...` | Expose the registry implementation directly | No |

**User's choice:** Delegated to advisor. The advisor recommended `wikify init` plus `wikify source add/list/show`, and this was adopted.
**Notes:** `wikify add` is deferred because it is too broad before sync/wikiize semantics are stable.

---

## Registry Artifact Format

| Option | Description | Selected |
|--------|-------------|----------|
| Single canonical JSON file | `.wikify/registry/sources.json` with schema version and sources keyed by id | Yes |
| JSONL event log | Append-only event stream requiring replay/compaction | No |
| Per-source files | One file per source record | No |
| SQLite | Local database-backed registry | No |

**User's choice:** Delegated to advisor. The advisor recommended a single JSON registry, and this was adopted.
**Notes:** Phase 22 needs current-state registry semantics, not an event log.

---

## the agent's Discretion

- Exact structured error code names.
- Exact local stat fingerprint field names.
- Exact timestamp format, provided it is deterministic and timezone-explicit.
- Whether locator lookup is accepted by `source show` in addition to primary `source_id` lookup.

## Deferred Ideas

- Recursive directory scan.
- URL fetch and remote repository probing.
- Sync queue generation.
- Wikiization and page generation.
- Human static views.
- Agent exports and context packs.
- Source deduplication across different locators.
- JSONL/per-source/SQLite registry alternatives.
