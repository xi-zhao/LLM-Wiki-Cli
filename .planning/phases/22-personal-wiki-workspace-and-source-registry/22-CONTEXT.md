# Phase 22: Personal Wiki Workspace And Source Registry - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 22 delivers the personal wiki workspace and durable source registry foundation. It covers workspace initialization, explicit workspace locations, source registration, source listing, and source inspection through stable JSON CLI output.

This phase does not perform full sync, recursive ingest, wikiization, human view generation, agent export generation, source merging, provider calls, or content mutation.

</domain>

<decisions>
## Implementation Decisions

### Workspace Layout

- **D-01:** `wikify init [BASE]` initializes a workspace rooted at `BASE` or the current working directory when `BASE` is omitted.
- **D-02:** The default workspace layout is:

```text
<base>/
  wikify.json
  .wikify/
    registry/
      sources.json
  sources/
  wiki/
  artifacts/
  views/
```

- **D-03:** `wikify.json` is the visible workspace manifest. It records a workspace id, schema version, and explicit source, wiki, artifact, and view locations.
- **D-04:** Manifest paths are stored as workspace-relative paths by default for portability. CLI output may include resolved absolute paths for agent convenience.
- **D-05:** `.wikify/` is internal control state. Product-facing artifacts live in visible directories such as `sources/`, `wiki/`, `artifacts/`, and `views/`.

### Source Identity

- **D-06:** Source identity is opaque and immutable. A source receives a generated `source_id` at first registration, using a shape such as `src_<uuid4hex>`.
- **D-07:** `source_id` must not be derived from locator text, file path, URL, content hash, or title because those fields can change.
- **D-08:** Duplicate detection uses a separate canonical `locator_key`, derived from normalized source type and locator.
- **D-09:** Re-adding the same canonical locator is idempotent and returns the existing source.
- **D-10:** Different locators are not automatically merged, even if lightweight metadata appears similar.
- **D-11:** Locator changes require explicit update semantics in a future phase and must preserve the original `source_id` and locator history when implemented.

### Source Registration Scope

- **D-12:** Phase 22 registration records bounded metadata only.
- **D-13:** Local file, directory, and note sources may be probed with cheap local filesystem metadata: existence, kind, size when applicable, mtime, and inode/device where available.
- **D-14:** URL sources are normalized syntactically but are not fetched, pinged, or resolved over the network.
- **D-15:** Repository sources are registered as locators. Local repository paths may receive lightweight local metadata, but remote repositories are not cloned or queried.
- **D-16:** Registration must not recursively scan directories, hash large content, create ingest queues, create wiki pages, call external agents, or call LLM providers.
- **D-17:** New sources start with `last_sync_status: "never_synced"`.

### CLI Shape

- **D-18:** Workspace initialization is exposed as top-level `wikify init`.
- **D-19:** Source registry behavior is exposed under a singular resource namespace:

```text
wikify source add <locator> --type file|directory|url|repository|note
wikify source list
wikify source show <source_id|locator>
```

- **D-20:** Type inference may be supported for obvious locators, but `--type` is the stable explicit interface.
- **D-21:** Source commands return the existing Wikify JSON envelope shape and must not imply sync, ingest, wikiization, or view generation.
- **D-22:** Do not use `wikify add` in Phase 22. It is too broad and should remain available for a future higher-level workflow after source, sync, and wikiize semantics are stable.

### Registry Artifact Format

- **D-23:** The canonical source registry is a single JSON document at `.wikify/registry/sources.json`.
- **D-24:** The registry contains `schema_version`, `workspace_id`, `updated_at`, and a `sources` object keyed by `source_id`.
- **D-25:** Each source record includes at minimum `source_id`, `type`, `locator`, `locator_key`, `fingerprint`, `discovery_status`, `last_sync_status`, `created_at`, `updated_at`, and `errors`.
- **D-26:** Registry writes use a temp file plus atomic replace and deterministic key ordering where practical.
- **D-27:** Runtime lookup indexes such as locator-key indexes should be built in memory rather than stored redundantly in the registry.
- **D-28:** JSONL event logs, per-source files, and database-backed registries are deferred until registry scale, merge behavior, or audit requirements justify them.

### the agent's Discretion

- Exact error code names for invalid source type, invalid locator, missing workspace, malformed manifest, and registry write failure.
- Exact timestamp format, as long as it is deterministic, timezone-explicit, and consistently tested.
- Exact `fingerprint` field names for local stat metadata, as long as they remain cheap and bounded.
- Whether `source show` accepts locator lookup in addition to `source_id`, as long as `source_id` lookup is primary and stable.

</decisions>

<specifics>
## Specific Ideas

- Treat Phase 22 as a source control plane that can support later ingest, wikiization, human views, and agent interfaces without implementing those later phases now.
- The workspace should be understandable to a human inspecting the directory tree.
- Keep legacy Markdown table indexing out of the v0.2 registry core model.
- Registration should catch obvious local path mistakes without causing hidden network I/O or expensive scanning.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Direction

- `.planning/PROJECT.md` - Current v0.2.0 product positioning, constraints, active requirements, and key decisions.
- `AGENTS.md` - Product direction and agent guidance for personal wiki, human views, agent views, and Graphify/LLM Wiki lessons.

### Phase Scope

- `.planning/REQUIREMENTS.md` - Phase 22 source registry requirements `SRC-01` through `SRC-04`.
- `.planning/ROADMAP.md` - Phase 22 goal, dependencies, success criteria, and verification expectations.

### Existing Implementation Patterns

- `wikify/config.py` - Existing base discovery via `WIKIFY_BASE` and `FOKB_BASE`; planning should account for future workspace discovery without breaking current behavior.
- `wikify/cli.py` - Existing CLI parser extension pattern and command envelope usage.
- `wikify/envelope.py` - Stable JSON envelope helpers used by agent-facing commands.
- `wikify/markdown_index.py` - Existing convention-directory scanner; useful context but not the new registry model.
- `scripts/source_index_manager.py` - Legacy Markdown table source index; explicitly not the v0.2 registry core.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `wikify.envelope.envelope_ok` and `wikify.envelope.envelope_error`: use for `init` and `source` command output.
- `wikify.config.discover_base`: existing base resolution should remain compatible while Phase 22 introduces `wikify.json` workspace manifests.
- `wikify.cli.build_parser`: existing pattern for adding Wikify-native commands on top of the legacy `fokb` parser.

### Established Patterns

- Commands return structured JSON envelopes by default, with pretty/quiet output handled centrally.
- Tests use `unittest` and temporary directories for CLI and filesystem behavior.
- Current graph and maintenance features avoid hidden provider calls and rely on explicit command/profile boundaries.

### Integration Points

- Add new workspace/registry code in a focused module rather than extending `scripts/source_index_manager.py`.
- Add `wikify init` and `wikify source ...` parser entries in `wikify/cli.py`.
- Preserve `WIKIFY_BASE`/`FOKB_BASE` compatibility while adding manifest-aware behavior.
- Future Phase 23 sync should consume `.wikify/registry/sources.json`, not legacy `sources/index.md`.

</code_context>

<deferred>
## Deferred Ideas

- Recursive directory scanning belongs to Phase 23 incremental sync.
- URL fetch, HTTP metadata, remote repository probing, and repository clone behavior belong to later sync/provider phases.
- Wiki page generation belongs to Phase 25 wikiization.
- Human static views belong to Phase 26.
- `llms.txt`, `graph.json`, citation indexes, and context packs belong to Phase 27.
- Source merge inference, deduplication across different locators, and source update/history commands are future capabilities.
- File watching and background sync are future capabilities.
- JSONL event logs, per-source registry files, and SQLite-backed registries are deferred until current-state JSON becomes insufficient.

</deferred>

---

*Phase: 22-personal-wiki-workspace-and-source-registry*
*Context gathered: 2026-04-29*
