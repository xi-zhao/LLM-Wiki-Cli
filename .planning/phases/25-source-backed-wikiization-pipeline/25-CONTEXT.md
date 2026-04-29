# Phase 25: Source-Backed Wikiization Pipeline - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 25 consumes Phase 23 ingest queue entries and turns eligible source items into structured, source-backed Markdown wiki pages using the Phase 24 object model.

This phase delivers a wikiization command, queue item processing, generated `wiki_page` Markdown bodies, JSON object artifacts, source references, review/task artifacts for ambiguous work, and explicit external agent handoff contracts for semantic enrichment.

This phase does not generate the human wiki home page, source index pages, static HTML, `llms.txt`, context packs, agent query APIs, graph maintenance repair flows, provider SDK integrations, background sync, or automatic user-content rewrites. Those remain later phases.

</domain>

<decisions>
## Implementation Decisions

### Command Boundary

- **D-01:** Add a top-level `wikify wikiize` command for consuming `.wikify/queues/ingest-items.json`.
- **D-02:** `wikify wikiize` defaults to processing queued items and supports bounded selection. Planner should include at least a dry-run mode and one or more focused selectors such as `--queue-id`, `--item`, `--source`, or `--limit`.
- **D-03:** `wikify wikiize --dry-run` must report selected queue entries, planned page/object paths, and reasons for skipped/blocked items without writing pages, object artifacts, queue updates, or run reports.
- **D-04:** Do not reuse legacy `wikify ingest` as the Phase 25 queue consumer. Existing ingest behavior can remain for compatibility, but v0.2 queue-to-wiki behavior should have a distinct `wikiize` surface.
- **D-05:** The command result uses the existing Wikify JSON envelope and should include item counts by outcome, touched object ids, touched paths, queue updates, validation summary, and next actions.

### Queue Consumption And Lifecycle

- **D-06:** Phase 25 reads `.wikify/queues/ingest-items.json` (`wikify.ingest-queue.v1`) and `.wikify/sync/source-items.json` (`wikify.source-items.v1`) together. Queue entries provide work selection; source items provide current source facts and paths.
- **D-07:** A queue entry is processable only when its source item still exists in the source item index and is eligible for wikiization. Missing, skipped, errored, or remote-without-content items should not silently create weak pages.
- **D-08:** Successful queue entries should be marked `completed` with `completed_at`, generated `object_ids`, and generated paths. Repeated `wikiize` runs should skip completed entries unless the source item was re-queued as `new` or `changed` by a later sync.
- **D-09:** Ambiguous, low-confidence, unsupported, or remote-without-content work should become `needs_review` or a dedicated wikiization task, not a silently generated page.
- **D-10:** Failures should be recorded per queue entry with structured errors while allowing unrelated entries to continue when safe.
- **D-11:** Phase 25 may update the current ingest queue artifact with lifecycle status, but should also write a run report so agents can inspect what happened without diffing queue state.

### Generated Output Layout

- **D-12:** Generated Markdown page bodies live under `wiki/pages/` by default. This keeps Phase 25 output separate from legacy `articles/parsed`, `topics`, and `sorted` layouts while staying human-visible.
- **D-13:** Generated wiki page JSON artifacts live under `artifacts/objects/wiki_pages/` using `wikify.wiki-page.v1`.
- **D-14:** `artifacts/objects/object-index.json` should be updated after successful generation so agents can enumerate generated objects without scanning Markdown.
- **D-15:** `body_path` in each wiki page object points to the generated Markdown page relative path, for example `wiki/pages/<slug>.md`.
- **D-16:** The page filename should be deterministic from the generated object id and readable title. If collision risk exists, prefer object id stability over title prettiness.
- **D-17:** Phase 25 should not generate source pages, topic pages, home pages, timeline views, static HTML, or browse navigation beyond the generated source-backed page bodies. Those belong to Phase 26.

### Object And Front Matter Contract

- **D-18:** Each generated page must have front matter that mirrors the `wikify.wiki-page.v1` metadata: `schema_version`, `id`, `type`, `title`, `summary`, `body_path`, `source_refs`, `outbound_links`, `backlinks`, `created_at`, `updated_at`, `confidence`, and `review_status`.
- **D-19:** Each generated page also has a machine-authoritative JSON object artifact with the same object id and required fields.
- **D-20:** Generated object ids should use the Phase 24 `stable_object_id("wiki_page", locator)` helper unless an explicit prior object id already exists for the same source item.
- **D-21:** The generated Markdown body should be readable without requiring JSON tooling. It should include a title, summary, source reference section, and bounded excerpt or derived notes from the source item.
- **D-22:** Front matter must use the Phase 24 supported subset: scalar values plus JSON-flow arrays/objects. Do not introduce full YAML dependencies.
- **D-23:** `review_status` is `generated` for deterministic high-confidence pages and `needs_review` for low-confidence or agent-enriched pages that require later review.

### Source Traceability

- **D-24:** Every generated wiki page must include `source_refs` with at least `source_id`, `item_id`, `locator` or `relative_path`, and confidence.
- **D-25:** When the source item is a local text file, source refs should include path and fingerprint evidence from the source item index.
- **D-26:** When line/span evidence can be determined cheaply, include bounded span metadata. If spans are not available in Phase 25, record item-level source refs rather than inventing precision.
- **D-27:** Do not copy large raw source content into object artifacts. Page bodies may include bounded excerpts useful for humans; object artifacts should keep references and short snippets only.
- **D-28:** Generated citations may be created when the implementation naturally has claim/span evidence, but citation-object generation is optional in Phase 25. Source refs on wiki pages are mandatory.

### Deterministic Baseline Generation

- **D-29:** Phase 25 must work without provider credentials or external agents for local text/Markdown source items.
- **D-30:** The deterministic baseline should extract a title from the first Markdown H1 or filename, derive a conservative summary from the first meaningful lines, and preserve a bounded excerpt or outline.
- **D-31:** The deterministic baseline should not claim semantic facts it cannot derive. It can state what source item was imported and expose excerpts/source refs.
- **D-32:** Deterministic extraction may preserve existing Markdown links as outbound link candidates only when they resolve to known object ids or can be left as unresolved for later review. Do not invent semantic relationships.
- **D-33:** Remote URL and remote repository source items remain unfetched unless an explicit external agent command is provided. Without explicit enrichment, they should produce review/agent handoff work rather than weak pages.

### External Agent Handoff

- **D-34:** Semantic enrichment must use explicit request/result artifacts and explicit command/profile flags. There must be no hidden provider or LLM call inside `wikify wikiize`.
- **D-35:** Prefer a contract parallel to existing patch bundle flows: build a wikiization request with source item facts, source text or bounded excerpt, target object schema, write scope, acceptance checks, and validation requirements.
- **D-36:** If an external agent is invoked, it must receive the request JSON on stdin and return a structured wikiization result/bundle. Wikify remains responsible for path validation, object validation, front matter rendering, and final writes.
- **D-37:** `--agent-command` and `--agent-profile` should follow existing explicit profile semantics from maintenance automation. Passing both remains ambiguous and should be rejected.
- **D-38:** Agent-generated output must still pass Phase 24 object validation before queue entries are completed.

### User Edit Protection

- **D-39:** Generated pages must not overwrite user-edited content silently.
- **D-40:** For generated pages, store enough generation metadata to detect drift, such as prior generated body hash and source item fingerprint in the JSON object artifact or a companion run artifact.
- **D-41:** If a target page exists and no matching prior generated hash proves it is safe to update, mark the queue entry `needs_review` and create a task rather than overwriting.
- **D-42:** If a generated page can be safely updated because the prior generated hash matches, update the page and object artifact atomically where practical.
- **D-43:** User-authored legacy wiki files outside the generated `wiki/pages/` target should not be mutated in Phase 25.

### Review And Task Artifacts

- **D-44:** Low-confidence, conflicting, unsupported, or blocked wikiization work should create a machine-readable task artifact instead of relying only on a prose warning.
- **D-45:** Use a new wikiization-specific task queue under `.wikify/queues/`, such as `.wikify/queues/wikiization-tasks.json`, rather than overloading `sorted/graph-agent-tasks.json` which is graph-maintenance-specific.
- **D-46:** Wikiization tasks should include `source_id`, `item_id`, queue id, target paths, evidence, reason code, agent instructions, acceptance checks, `requires_user`, and status.
- **D-47:** `requires_user` should default to `false` when an agent can reasonably inspect/repair the task; reserve `true` for policy or safety cases where human choice is genuinely needed.
- **D-48:** Phase 25 creates review/task artifacts but does not execute maintenance repair flows. Phase 28 integrates generated wiki pages with the broader maintenance loop.

### Validation And Atomicity

- **D-49:** Generated objects and front matter should be validated in memory before writing where practical, then `validate_workspace_objects(..., strict=True, write_report=True)` should run after the command writes artifacts.
- **D-50:** A validation failure should prevent the queue entry from being marked completed and should return a structured exit-code-2 style error or per-item failed status consistent with existing envelope patterns.
- **D-51:** Writes should use temp file plus atomic replace for JSON artifacts and queue/run-report files. Markdown writes should avoid partial files and should be scoped to generated target paths.
- **D-52:** `wikify validate` remains the explicit standalone validation command; `wikify wikiize` may call the validator as a safety gate but should not hide validation records.

### the agent's Discretion

- Exact module names, as long as wikiization code is focused and not buried inside legacy `scripts/fokb.py`.
- Exact report schema names, as long as every new artifact has an explicit `schema_version` and tests assert the shape.
- Exact deterministic summary/excerpt heuristics for the baseline local text importer.
- Exact selector flags beyond dry-run, as long as agents can process all queued work and a focused single item.
- Whether citation objects are generated in Phase 25 or deferred, as long as page-level source refs are complete and validated.

</decisions>

<specifics>
## Specific Ideas

- This phase should make the product loop real: `source add -> sync -> wikiize -> readable generated page`.
- The generated wiki page is a product artifact for people, not only backend context for agents.
- Baseline deterministic wikiization should be conservative and source-backed rather than pretending to understand more than it can.
- Explicit agent enrichment is valuable, but it must look like the existing safe automation pattern: request artifact, bounded write scope, validation gate, structured result.
- Remote URL/repository items are useful queued work, but without explicit fetch/enrichment they should not become fake pages.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Direction

- `AGENTS.md` - Product positioning, source-to-wiki flow, human/agent view split, low-interruption automation direction, and Graphify/LLM Wiki lessons.
- `.planning/PROJECT.md` - Current v0.2.0 positioning, validated requirements, active requirements, constraints, and Phase 24 completion state.

### Phase Scope

- `.planning/ROADMAP.md` - Phase 25 goal, requirements, success criteria, dependencies, and verification expectations.
- `.planning/REQUIREMENTS.md` - Wikiization requirements `WIK-01` through `WIK-05`.
- `.planning/STATE.md` - Current GSD state, Phase 25 focus, and recent Phase 24 decisions.

### Upstream Context

- `.planning/phases/22-personal-wiki-workspace-and-source-registry/22-CONTEXT.md` - Workspace layout, visible vs internal artifact separation, source registry identity, and source registration boundary.
- `.planning/phases/23-incremental-sync-and-ingest-queue/23-CONTEXT.md` - Source item model, ingest queue semantics, sync artifacts, and no-fetch/no-provider boundary.
- `.planning/phases/23-incremental-sync-and-ingest-queue/23-01-SUMMARY.md` - Implemented `wikify sync`, source item index, ingest queue, dry-run, and residual Phase 25 risks.
- `.planning/phases/24-wiki-object-model-and-validation/24-CONTEXT.md` - Object model, object ids, front matter, source refs, validation, and graph compatibility decisions.
- `.planning/phases/24-wiki-object-model-and-validation/24-01-SUMMARY.md` - Implemented object model, front matter parser, validator, graph object-id compatibility, and `wikify validate`.
- `.planning/phases/24-wiki-object-model-and-validation/24-01-VERIFICATION.md` - Phase 24 verification evidence and validation command matrix.

### Existing Implementation Patterns

- `wikify/sync.py` - Source item index, ingest queue paths, queue entry shape, deterministic item ids, source item statuses, and current-state JSON write pattern.
- `wikify/objects.py` - Object constructors, schema versions, required fields, stable object ids, object artifact paths, and source/source-item adapters.
- `wikify/frontmatter.py` - Front matter parser/serializer used by generated Markdown pages.
- `wikify/object_validation.py` - Validator and report writer that Phase 25 should use as a post-write safety gate.
- `wikify/workspace.py` - Workspace loading, registry paths, source records, and atomic JSON write style.
- `wikify/cli.py` - Command wiring, JSON envelope patterns, and explicit command/profile behavior.
- `wikify/envelope.py` - Stable success/error envelope helpers.
- `wikify/maintenance/agent_profile.py` - Existing explicit agent profile semantics to reuse for wikiization agent handoff.
- `wikify/maintenance/bundle_request.py` - Existing request artifact pattern for external agents.
- `wikify/maintenance/bundle_producer.py` - Existing explicit command invocation pattern and timeout/error handling.
- `wikify/maintenance/task_queue.py` - Existing task artifact fields and low-interruption agent task design.
- `scripts/fokb_protocol.md` - Current protocol registry, object validation schema, existing patch-bundle request/result conventions, and error code style.
- `README.md` - User-facing command and artifact boundary documentation.
- `LLM-Wiki-Cli-README.md` - Chinese product documentation and v0.2 object/validation positioning.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `wikify.sync.ingest_queue_path`, `source_items_path`, `INGEST_QUEUE_SCHEMA_VERSION`, and `SOURCE_ITEMS_SCHEMA_VERSION`: use to locate and validate Phase 23 input artifacts.
- `wikify.objects.make_wiki_page_object`, `stable_object_id`, `object_document_path`, `object_index_path`, and `make_object_index`: use for generated object artifacts.
- `wikify.frontmatter.render_markdown_with_front_matter`: use for generated Markdown page metadata.
- `wikify.object_validation.validate_workspace_objects`: use as the strict safety gate after generation.
- `wikify.config.discover_base`: use the same workspace discovery behavior as source, sync, graph, and validate commands.
- `wikify.envelope.envelope_ok` and `envelope_error`: use for `wikify wikiize` output.
- `wikify.maintenance.agent_profile.resolve_agent_execution`: reuse explicit agent-command/profile conflict handling if Phase 25 includes external agent execution.

### Established Patterns

- Workspace state lives under `.wikify/`; visible product artifacts live under `wiki/`, `artifacts/`, and `views/`.
- Commands are stdlib-only, return JSON envelopes, and are tested with `unittest` and temporary directories.
- Existing automation avoids hidden provider calls and requires explicit external command/profile flags.
- JSON control artifacts use explicit `schema_version`, sorted deterministic output where practical, and temp-file atomic writes.
- Existing graph task queues use structured task artifacts with evidence, write scope, agent instructions, acceptance checks, `requires_user`, and status.

### Integration Points

- Add a focused wikiization module, likely `wikify/wikiize.py`, rather than extending legacy ingest scripts.
- Add parser and handler for `wikify wikiize` in `wikify/cli.py`.
- Read source registry/source item facts through existing workspace/sync artifacts instead of creating a parallel source store.
- Write generated Markdown under `wiki/pages/` and JSON objects under `artifacts/objects/`.
- Update `.wikify/queues/ingest-items.json` and write a `.wikify/wikiization/last-wikiize.json` style report.
- Add tests in a new `tests/test_wikiize.py` plus CLI tests in `tests/test_wikify_cli.py`.

</code_context>

<deferred>
## Deferred Ideas

- Human home pages, source pages, topic pages, local static HTML, graph/timeline entry views, and browse navigation belong to Phase 26.
- `llms.txt`, `llms-full.txt`, citation index export, context packs, related-topic queries, and agent context APIs belong to Phase 27.
- Connecting generated wiki pages to graph maintenance repair, verifier preservation of source refs, and broad compatibility flows belongs to Phase 28.
- Built-in provider SDKs, provider key management, retries, budgets, and provider audit records are future provider-runtime work.
- Background file watching, automatic sync/wikiize loops, and scheduled ingestion are future automation features.
- Full semantic entity extraction into topic/project/person/decision/timeline objects can be added after the baseline source-backed page pipeline is stable.
- Fetching URL bodies or cloning remote repositories without an explicit external agent/provider boundary remains out of scope.

</deferred>

---

*Phase: 25-source-backed-wikiization-pipeline*
*Context gathered: 2026-04-29*
