# Phase 24: Wiki Object Model And Validation - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 24 defines the canonical wiki object model shared by future wikiization, human views, agent interfaces, graph extraction, and maintenance.

This phase delivers schema definitions, object parsing/serialization helpers, Markdown front matter support, JSON object artifact contracts, validation, structured validation errors, and a compatibility path for existing graph builders.

This phase does not process the ingest queue into wiki pages, generate human views, export `llms.txt`, build context packs, call providers, infer semantic entities, repair content, or run maintenance tasks. Those remain later phases.

</domain>

<decisions>
## Implementation Decisions

### Schema Set And Boundaries

- **D-01:** Define Phase 24 schemas for source, source item, wiki page, topic, project, person, decision, timeline entry, citation, graph edge, and context pack objects.
- **D-02:** Reuse existing Phase 22 and Phase 23 source/source-item concepts instead of redefining them. Phase 24 may provide object-model adapters for them, but must not fork source registry or sync source item truth.
- **D-03:** Use explicit schema versions for every new document family. Recommended names are `wikify.object-index.v1`, `wikify.wiki-page.v1`, `wikify.topic.v1`, `wikify.project.v1`, `wikify.person.v1`, `wikify.decision.v1`, `wikify.timeline-entry.v1`, `wikify.citation.v1`, `wikify.graph-edge.v1`, `wikify.context-pack.v1`, and `wikify.object-validation.v1`.
- **D-04:** Keep schemas as plain Python dictionaries/dataclasses and stdlib validation logic. Do not add Pydantic, JSON Schema dependencies, YAML dependencies, or a database in Phase 24.
- **D-05:** A schema is only considered canonical when tests assert required fields, valid examples, invalid examples, and round-trip behavior where relevant.

### Object Identity

- **D-06:** Object ids are stable machine ids, not display titles. The object id is authoritative for agent references, graph edges, citations, and validation.
- **D-07:** Existing `source_id` and `item_id` remain canonical for source and source item references.
- **D-08:** Wiki page ids should prefer explicit front matter `id` when present. When absent, validators may compute a deterministic path fallback for compatibility, but must report a warning or error depending on strictness.
- **D-09:** Generated object ids should use type-aware prefixes where practical, such as `page_`, `topic_`, `project_`, `person_`, `decision_`, `timeline_`, `citation_`, `edge_`, and `ctx_`.
- **D-10:** Object records should keep both `id` and `relative_path` where a file exists. Agents use `id`; humans and compatibility graph code can still inspect paths.
- **D-11:** Duplicate object ids are validation errors. Duplicate titles are allowed when ids differ.

### Markdown And JSON Artifacts

- **D-12:** JSON object artifacts are the machine-authoritative representation.
- **D-13:** Markdown front matter is a human-readable mirror of required object metadata, not a separate source of truth that may drift silently.
- **D-14:** Use a small stdlib front matter parser for the subset Wikify writes and validates: scalar strings, numbers, booleans, simple arrays, and flat nested records where needed. Full YAML compatibility is out of scope.
- **D-15:** Front matter should include at minimum `schema_version`, `id`, `type`, `title`, `summary`, `source_refs`, `outbound_links`, `confidence`, and `review_status` for wiki pages where applicable.
- **D-16:** JSON object artifacts should live in a visible product artifact area, not only `.wikify/` control state. Preferred path: `artifacts/objects/`.
- **D-17:** `.wikify/` remains internal control-plane state for registry, sync, and queues. The wiki object model is part of the generated knowledge base and should be readable by humans and agents.
- **D-18:** Phase 24 may validate existing Markdown without rewriting it. Automatic mutation of user or generated pages belongs to later explicit flows.

### Required Wiki Page Fields

- **D-19:** Wiki page objects include at minimum: `schema_version`, `id`, `type`, `title`, `summary`, `body_path`, `source_refs`, `outbound_links`, `backlinks`, `created_at`, `updated_at`, `confidence`, and `review_status`.
- **D-20:** `confidence` is numeric from `0.0` to `1.0`. Any derived labels such as `low`, `medium`, or `high` are secondary and should not replace the numeric value.
- **D-21:** `review_status` should use a small explicit vocabulary: `generated`, `needs_review`, `approved`, `rejected`, and `stale`.
- **D-22:** `type` should be a product-level object type such as `source`, `source_item`, `wiki_page`, `topic`, `project`, `person`, `decision`, `timeline_entry`, `citation`, `graph_edge`, or `context_pack`, not a legacy folder name.
- **D-23:** Legacy folder scopes such as `topics`, `articles/parsed`, `briefs`, `sorted`, and `sources` can be mapped into object types for compatibility, but should not become the new canonical type system.

### Source References And Citations

- **D-24:** Every generated claim-bearing page should support `source_refs` that point to Phase 22/23 source ids and source item ids.
- **D-25:** A source reference should include at minimum `source_id`, optional `item_id`, `locator` or `relative_path`, `span` or line evidence when available, and confidence.
- **D-26:** Citation objects should be separate reusable records when a claim, relationship, or page needs stable source-backed evidence.
- **D-27:** Citation records should avoid copying large raw source content. Store bounded snippets or spans only when needed for evidence and later copyright-safe display.
- **D-28:** Validation must catch unresolved source ids and source item ids against `.wikify/registry/sources.json` and `.wikify/sync/source-items.json` when those artifacts exist.

### Links, Backlinks, And Graph Edges

- **D-29:** Outbound links and backlinks should reference canonical object ids, with optional path/title labels for human debugging.
- **D-30:** Graph edge schema should align with the existing `GraphEdge` fields: `source`, `target`, `type`, `provenance`, `confidence`, `source_path`, `line`, and `label`.
- **D-31:** Preserve Graphify-style provenance vocabulary as first-class schema values: `EXTRACTED`, `INFERRED`, and `AMBIGUOUS`.
- **D-32:** Phase 24 validates graph edge shape and unresolved object references, but does not perform new semantic inference.
- **D-33:** Existing graph builders must keep working with path-based nodes. Phase 24 should add an adapter or metadata bridge so graph extraction can read object ids without requiring content mutation.

### Validation Command And Result Shape

- **D-34:** Add an explicit validation surface for the object model. Preferred CLI shape: top-level `wikify validate`.
- **D-35:** `wikify validate` should return the existing Wikify JSON envelope and a `wikify.object-validation.v1` result document.
- **D-36:** Validation should support at least a workspace-level default run and a focused path run. Planner may choose exact flags, but `--path` and `--strict` are preferred.
- **D-37:** Default validation should be compatibility-tolerant: it should report legacy Markdown gaps as warnings where needed instead of making existing sample KB unusable.
- **D-38:** Strict validation should fail declared v0.2 object documents when required fields are missing, links are unresolved, duplicate ids exist, or source refs are unresolved.
- **D-39:** Validation errors must be structured records with stable fields: `code`, `message`, `path`, `object_id`, `field`, `severity`, and `details`.
- **D-40:** Important error codes should include `object_required_field_missing`, `object_duplicate_id`, `object_link_unresolved`, `object_source_ref_unresolved`, `object_frontmatter_invalid`, and `object_schema_invalid`.
- **D-41:** Exit code semantics should match the existing CLI style: successful validation exits `0`; validation failures that are hard errors should exit `2` or a documented non-zero code; warnings alone should not fail default mode.

### Compatibility And Migration

- **D-42:** Do not break `wikify graph`, `wikify maintain`, legacy `fokb` commands, or existing sample KB layouts in Phase 24.
- **D-43:** Existing `wikify.markdown_index.WikiObject` should either be extended carefully or adapted by new object-model code. Avoid a broad graph rewrite in this phase.
- **D-44:** Existing path ids used by graph analytics remain valid as compatibility ids until generated pages carry canonical object ids.
- **D-45:** Phase 24 should provide test fixtures for valid and invalid object documents instead of relying only on current sample KB content.
- **D-46:** Docs must state that Phase 24 defines and validates the object model only. Queue consumption and page generation start in Phase 25.

### the agent's Discretion

- Exact module names, as long as object model code is focused and not buried inside legacy scripts.
- Exact file names under `artifacts/objects/`, as long as paths are deterministic and documented.
- Exact object id hash length and slug normalization rules, as long as they are stable and tested.
- Exact validator implementation decomposition between parser, schema helpers, and CLI handler.
- Exact warning vs error split for legacy Markdown compatibility, as long as strict mode enforces required v0.2 fields.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Direction

- `AGENTS.md` - Product positioning, human/agent view split, low-interruption automation direction, and Graphify/LLM Wiki lessons.
- `.planning/PROJECT.md` - Current v0.2.0 product positioning, constraints, active requirements, and key decisions.

### Phase Scope

- `.planning/ROADMAP.md` - Phase 24 goal, requirements, success criteria, dependencies, and verification expectations.
- `.planning/REQUIREMENTS.md` - Object model requirements `OBJ-01` through `OBJ-04`.
- `.planning/STATE.md` - Current GSD state and Phase 22/23 decisions.

### Upstream Source And Sync Context

- `.planning/phases/22-personal-wiki-workspace-and-source-registry/22-CONTEXT.md` - Source registry and workspace decisions Phase 24 must respect.
- `.planning/phases/23-incremental-sync-and-ingest-queue/23-CONTEXT.md` - Source item, sync artifact, and ingest queue decisions Phase 24 must respect.
- `.planning/phases/23-incremental-sync-and-ingest-queue/23-01-SUMMARY.md` - Implemented sync artifact behavior and residual risks.
- `.planning/phases/23-incremental-sync-and-ingest-queue/23-01-VERIFICATION.md` - Phase 23 verification evidence and boundaries.

### Existing Implementation Patterns

- `wikify/workspace.py` - Workspace/source registry schema and artifact loading patterns.
- `wikify/sync.py` - Source item index, ingest queue, schema constants, deterministic id helpers, and validation style for existing sync artifacts.
- `wikify/markdown_index.py` - Current lightweight Markdown object scanner that graph and maintenance use today.
- `wikify/graph/model.py` - Existing graph node and edge dataclasses.
- `wikify/graph/extractors.py` - Existing Markdown/wikilink extraction and path-based graph id behavior.
- `wikify/graph/builder.py` - Existing graph artifact build flow.
- `wikify/maintenance/findings.py` - Maintenance findings that consume graph objects and should remain compatible.
- `wikify/cli.py` - CLI parser extension pattern and JSON envelope command handlers.
- `wikify/envelope.py` - Stable JSON envelope helpers.

### Existing Protocol And Front Matter Context

- `scripts/fokb_protocol.md` - Existing schema/version conventions, changed object schema, claim schema, graph relevance schema, and error vocabulary style.
- `README.md` - User-facing CLI and artifact boundaries.
- `LLM-Wiki-Cli-README.md` - Chinese product documentation, existing front matter references, and workflow descriptions.
- `scripts/topic_maintainer.py` - Existing front matter writing style for topic notes.
- `scripts/generate_topic_digest.py` - Existing front matter writing style for digest outputs.
- `scripts/README.md` - Legacy front matter and Obsidian-friendly notes context.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `wikify.envelope.envelope_ok` and `wikify.envelope.envelope_error`: use for `wikify validate` JSON output.
- `wikify.config.discover_base`: use the same base discovery as workspace, source, and sync commands.
- `wikify.workspace.load_workspace`: load manifest and registry for source-reference validation.
- `wikify.sync.source_items_path`: locate source item index for source item reference validation.
- `wikify.markdown_index.scan_objects`: compatibility scanner for existing Markdown files.
- `wikify.graph.model.GraphNode` and `GraphEdge`: schema reference for graph edge/object compatibility.

### Established Patterns

- Current artifact schemas are plain JSON dictionaries with explicit `schema_version`.
- Commands use stdlib only and return stable JSON envelopes.
- Tests use `unittest` and temporary directories.
- Existing graph ids are relative paths. Phase 24 must preserve that compatibility while introducing canonical object ids.
- Current front matter writers output a small YAML-like subset; Phase 24 should parse only a bounded subset instead of introducing a YAML dependency.
- Current maintenance treats graph object issues as queued agent tasks rather than silent content mutation.

### Integration Points

- Add focused object model code, likely under a new `wikify` module, instead of extending legacy `scripts/fokb.py`.
- Add CLI validation wiring in `wikify/cli.py`.
- Extend or adapt `wikify/markdown_index.py` carefully so `wikify graph` can consume metadata without changing existing graph behavior.
- Add tests for schema constructors, front matter round trips, validation failures, duplicate ids, unresolved links, unresolved source refs, and graph integration smoke.
- Update `README.md`, `LLM-Wiki-Cli-README.md`, and `scripts/fokb_protocol.md` with schema and validation contracts.

</code_context>

<specifics>
## Specific Ideas

- Phase 24 should make the knowledge base object model feel like a real product contract, not a loose folder convention.
- The object model should serve both people and agents: Markdown remains readable, JSON remains stable for automation.
- Graphify lessons should enter as provenance and graph edge schema quality, not as a broad feature expansion.
- LLM Wiki lessons should enter as page/source/citation traceability, not as a copied implementation.
- Validation should be useful to agents: structured errors, stable codes, and paths/object ids precise enough for follow-up repair tasks.

</specifics>

<deferred>
## Deferred Ideas

- Processing `.wikify/queues/ingest-items.json` into generated wiki pages belongs to Phase 25.
- Creating source pages, topic pages, home pages, local static HTML, graph/timeline entry views, and browseable human output belongs to Phase 26.
- `llms.txt`, `llms-full.txt`, citation index export, page index export, related-topic queries, and context packs belong to Phase 27.
- Maintenance findings that mutate or repair v0.2 wiki pages belong to Phase 28.
- Full YAML compatibility, JSON Schema dependency, Pydantic models, SQLite object store, vector embeddings, and entity-resolution inference are out of scope for Phase 24.
- Automatic migration or rewriting of existing Markdown pages to add front matter is deferred until explicit content mutation flows exist.

</deferred>

---

*Phase: 24-wiki-object-model-and-validation*
*Context gathered: 2026-04-29*
