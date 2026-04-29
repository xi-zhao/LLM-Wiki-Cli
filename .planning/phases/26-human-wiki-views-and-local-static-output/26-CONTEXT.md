# Phase 26: Human Wiki Views And Local Static Output - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 26 turns the v0.2 wiki object model and source-backed page artifacts into human-readable navigation artifacts.

This phase delivers generated Markdown views, generated source pages, generated topic/project/person/decision collection pages, graph and timeline entry points, and stdlib-compatible local static HTML output.

This phase does not sync sources, consume ingest queues, call providers, fetch remote content, infer new semantic entities from raw source text, export `llms.txt`, build context packs, add chat/RAG UI, or clone desktop/Tauri behavior. Those remain separate phases.

</domain>

<decisions>
## Implementation Decisions

### Command Boundary

- **D-01:** Add a top-level `wikify views` command for generating human-facing wiki views. Do not overload `wikify wikiize`, `wikify graph`, or legacy `wikify ingest`.
- **D-02:** `wikify views` should generate both Markdown views and local static HTML by default. Include `--no-html` for Markdown-only generation and `--dry-run` for preview without writes.
- **D-03:** Planner may add a focused selector such as `--section home|sources|pages|collections|timeline|graph|review|all`, but the default behavior should cover all Phase 26 view requirements.
- **D-04:** `wikify views --dry-run` must report planned Markdown paths, planned HTML paths, source/object counts, missing prerequisite warnings, drift conflicts, and next actions without writing view files, manifests, reports, task queues, or static assets.
- **D-05:** The command result uses the existing Wikify JSON envelope. The result should include `schema_version`, `status`, `dry_run`, `summary`, `artifacts`, generated view records, validation summary, conflicts, and `next_actions`.
- **D-06:** `wikify views` is a rendering command, not a pipeline orchestrator. It must not run `sync`, `wikiize`, `graph`, external agents, providers, network fetchers, or repository commands implicitly.

### Source Of Truth And Data Flow

- **D-07:** Human views are generated from the same source of truth that future agent views will use: `artifacts/objects/object-index.json` plus object JSON documents under `artifacts/objects/`.
- **D-08:** Source status data comes from Phase 22 and Phase 23 artifacts: `.wikify/registry/sources.json`, `.wikify/sync/source-items.json`, and `.wikify/queues/ingest-items.json`.
- **D-09:** Review and unresolved issue data comes from `.wikify/queues/wikiization-tasks.json`, object validation records, and relevant queued control artifacts. Do not rely on prose-only warnings.
- **D-10:** Graph entry views may reference existing `graph/graph.json`, `graph/GRAPH_REPORT.md`, and `graph/graph.html` when present. Phase 26 should not rebuild graph artifacts unless the user runs `wikify graph` separately.
- **D-11:** Timeline views are generated from `timeline_entry` objects when they exist. Do not synthesize timeline events from page text in Phase 26.
- **D-12:** Do not create a separate human-only knowledge store. Markdown views and static HTML are derived artifacts over the object model, source registry, queues, and optional graph artifacts.
- **D-13:** Do not reread raw source files to build human views. If a page, topic, source reference, or citation is not represented in object/control artifacts, the view should expose the gap as missing data or next action rather than silently deriving new facts.

### View Set And Content

- **D-14:** Generate a human-facing home page that works as the main browsing entry point. It should include recent updates, object counts, source groups, core topics when topic objects exist, review/unresolved counts, and links to source, page, collection, graph, timeline, and review views.
- **D-15:** Generate a page directory that lists wiki pages from `wiki_page` objects with title, summary, review status, confidence, updated time, source refs, and links to the underlying generated page.
- **D-16:** Generate source index and per-source pages. Each source page should show source status, source metadata, sync summary, contributed pages discovered through `source_refs`, citation objects when available, and unresolved issues/tasks connected to that source.
- **D-17:** Generate collection indexes and detail pages for `topic`, `project`, `person`, and `decision` objects. Each detail page should show summary, related page ids, source-backed references, review status when present, and links back to source/page views.
- **D-18:** If topic/project/person/decision objects do not exist yet, generate honest empty-state collection views with counts and next actions. Do not fabricate "core topics" from filenames or source snippets in this phase.
- **D-19:** Generate a timeline view from `timeline_entry` objects when present. If no timeline entries exist, the timeline page should explain the absence through structured empty-state content and link back to pages/sources.
- **D-20:** Generate a graph entry view that links to existing graph artifacts when present and gives an explicit next action such as `wikify graph` when graph artifacts are missing.
- **D-21:** Generate a review view that makes unresolved work visible to humans: wikiization tasks, validation errors/warnings, drift conflicts, unsupported sources, remote-without-content tasks, and missing graph/timeline artifacts when relevant.

### Output Layout

- **D-22:** Visible Markdown view artifacts should live under `views/`. Recommended paths are `views/index.md`, `views/pages.md`, `views/sources/index.md`, `views/sources/<source-id>.md`, `views/topics/index.md`, `views/topics/<object-id>.md`, `views/projects/`, `views/people/`, `views/decisions/`, `views/timeline.md`, `views/graph.md`, and `views/review.md`.
- **D-23:** Local static HTML should live under `views/site/` and mirror the Markdown view structure with relative links, for example `views/site/index.html`, `views/site/sources/<source-id>.html`, and `views/site/assets/style.css`.
- **D-24:** Write a run report under `.wikify/views/last-views.json` using a schema such as `wikify.views-run.v1`.
- **D-25:** Track generated view file hashes in `.wikify/views/view-manifest.json` using a schema such as `wikify.views-manifest.v1`. The manifest is control-plane state; the visible views remain the human-facing artifact.
- **D-26:** If a generated Markdown view exists and the manifest cannot prove it is safe to overwrite, do not overwrite it. Report a drift conflict and create or update a view task under `.wikify/queues/view-tasks.json`.
- **D-27:** Static HTML is derived output, but it should still be scoped under `views/site/` and generated deterministically. If source Markdown view drift prevents regenerating a view, HTML for that view should be skipped or marked conflicted rather than silently rendering stale or user-edited content as canonical.

### Static HTML Rendering

- **D-28:** Static HTML rendering must be stdlib-only. Use safe escaping with Python's standard `html` module and avoid introducing Markdown, template, YAML, JS framework, or browser-server dependencies.
- **D-29:** The renderer may support a bounded Markdown subset that Wikify itself writes: headings, paragraphs, bullet lists, fenced or indented code blocks if needed, inline code, and links. Full CommonMark compatibility is out of scope.
- **D-30:** Generated HTML should be local-file friendly: relative links, no required dev server, no external CDN, no accounts, no telemetry, and no mandatory JavaScript.
- **D-31:** The static site should be functional and restrained rather than a marketing page. It should prioritize scannable navigation, source traceability, and review state visibility.
- **D-32:** Planner may reuse the simple escaping and HTML style pattern from `wikify/graph/html.py`, but Phase 26 should provide a dedicated renderer for view pages instead of coupling human wiki rendering to graph internals.

### Validation, Missing Data, And Failure Behavior

- **D-33:** Before non-dry-run writes, `wikify views` should validate the object artifacts it plans to render. Warnings can be surfaced in review views; hard object errors should block successful generation and return a structured exit-code-2 style error consistent with `wikify validate`.
- **D-34:** Missing optional artifacts should not crash view generation. Examples: no topic objects, no timeline entries, no graph artifacts, no citation objects, or no wikiization tasks. Generate empty-state views and clear next actions.
- **D-35:** Missing required prerequisites should return structured errors. Examples: uninitialized workspace, malformed object index, invalid source registry, invalid source item index, or object validation hard errors.
- **D-36:** Generated views should keep every claim tied to object/source fields. Display source refs and citation objects; do not invent uncited summaries beyond object summaries already present.
- **D-37:** View generation should be deterministic enough for tests and agent diffs: stable ordering, stable relative links, sorted object groups, and explicit generated timestamps in reports rather than unstable content where possible.

### Product Experience

- **D-38:** The generated wiki is the product artifact. The first view should help a person understand "what knowledge do I have, where did it come from, what changed recently, and what needs attention?"
- **D-39:** Human views should improve agent usefulness indirectly by exposing clearer source/page/collection structure, not by creating a separate retrieval API. Phase 27 owns machine-focused exports and context packs.
- **D-40:** Audit, hash guards, manifests, and view tasks should be treated as trust infrastructure. The user-facing language should emphasize safe generation, visible unresolved work, and recoverable automation rather than selling audit logs as the headline.

### the agent's Discretion

- Exact module names, as long as view-generation code is focused and not buried in legacy scripts.
- Exact static CSS, as long as it is local, readable, and not a decorative landing page.
- Exact schema field ordering, as long as schemas are explicit, deterministic, and tested.
- Exact empty-state wording, as long as missing data is honest and actionable.
- Exact collection detail layout, as long as topics, projects, people, and decisions are first-class view categories.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Direction

- `AGENTS.md` - Product positioning, human/agent view split, CLI-first boundary, Graphify/LLM Wiki lessons, and generated wiki as product artifact.
- `.planning/PROJECT.md` - Current v0.2.0 state, active human view requirement, constraints, and key decisions.

### Phase Scope

- `.planning/ROADMAP.md` - Phase 26 goal, requirements, success criteria, dependencies, and verification expectations.
- `.planning/REQUIREMENTS.md` - Human wiki view requirements `VIEW-01` through `VIEW-05`.
- `.planning/STATE.md` - Current GSD state, Phase 25 completion, and recent decisions affecting views.

### Upstream Phase Context

- `.planning/phases/22-personal-wiki-workspace-and-source-registry/22-CONTEXT.md` - Workspace layout, visible artifact directories, source registry identity, and source registration boundary.
- `.planning/phases/23-incremental-sync-and-ingest-queue/23-CONTEXT.md` - Source item model, sync artifacts, ingest queue semantics, and no-fetch/no-provider boundary.
- `.planning/phases/24-wiki-object-model-and-validation/24-CONTEXT.md` - Object schemas, object ids, front matter, validation, graph edge compatibility, and canonical object artifact root.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-CONTEXT.md` - Generated wiki page layout, source refs, object index updates, wikiization tasks, edit protection, and explicit agent handoff boundary.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-01-SUMMARY.md` - Implemented `wikify wikiize` behavior and residual Phase 26 handoff.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-01-VERIFICATION.md` - Verification evidence for generated pages, object index, validation, and wikiization tasks.

### Existing Implementation Patterns

- `wikify/wikiize.py` - Generated page/object layout, object index writing, generation hashes, wikiization task queue, run report shape, and validation gate pattern.
- `wikify/objects.py` - Object schema versions, object type helpers, object document paths, object index helpers, and constructors for topic/project/person/decision/timeline/citation objects.
- `wikify/object_validation.py` - Validation result shape, hard-error behavior, validation report path, and focused validation support.
- `wikify/workspace.py` - Workspace manifest, visible `views/` directory, source registry paths, and atomic JSON write style.
- `wikify/sync.py` - Source item index and ingest queue artifact paths/statuses that source pages and review views should read.
- `wikify/frontmatter.py` - Bounded front matter parser/renderer used by generated Markdown pages.
- `wikify/graph/builder.py` - Current graph artifact paths and graph build result shape.
- `wikify/graph/html.py` - Simple stdlib HTML escaping pattern; useful as a style reference, not a coupling target.
- `wikify/markdown_index.py` - Legacy Markdown scanner used by graph compatibility; views should prefer object artifacts but may need to understand legacy scan boundaries.
- `wikify/cli.py` - CLI parser extension pattern, JSON envelope command handlers, and completion metadata style.
- `wikify/envelope.py` - Stable success/error envelope helpers.
- `tests/test_wikiize.py` - Existing temporary-workspace tests for generated pages, object artifacts, hash guard behavior, tasks, and explicit agent handoff.
- `tests/test_wikify_cli.py` - CLI parser and envelope tests for init, sync, wikiize, validate, and command wiring.
- `README.md` - Current documentation for workspace, source registry, sync, wikiize, object validation, and explicit Phase 26 boundary.
- `scripts/fokb_protocol.md` - Protocol registry and historical compatibility context for schema/version naming.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `wikify.config.discover_base`: use the same workspace discovery behavior as existing commands.
- `wikify.workspace.load_workspace`, `registry_path`, and manifest paths: load workspace/source registry and keep `views/` inside the initialized workspace.
- `wikify.objects.object_index_path`, `object_artifacts_dir`, `object_document_path`, `SCHEMA_VERSIONS`, and collection object constructors: enumerate and interpret object artifacts.
- `wikify.object_validation.validate_workspace_objects`: run focused or workspace validation before rendering views and write validation records when needed.
- `wikify.wikiize.wikiization_task_queue_path` and `wikiize_report_path`: read unresolved wikiization task and latest wikiization status for review/source pages.
- `wikify.sync.source_items_path` and `ingest_queue_path`: read source item and queue state for source pages and review views.
- `wikify.envelope.envelope_ok` and `envelope_error`: keep JSON output stable.

### Established Patterns

- Visible product artifacts live under `wiki/`, `artifacts/`, and `views/`; `.wikify/` is internal control-plane state.
- Commands are stdlib-only, use `argparse`, and return structured JSON envelopes.
- Tests use `unittest`, temporary directories, and direct CLI invocation through `cli.main`.
- Generated content should be hash-guarded when a human may edit visible Markdown output.
- Existing automation records blocked work as machine-readable task artifacts instead of relying on terminal prose.
- Object ids are canonical for machine references; paths and titles are human-facing labels.

### Integration Points

- Add a focused view-generation module, likely `wikify/views.py` or `wikify/human_views.py`.
- Add `wikify views` parser and handler in `wikify/cli.py`.
- Read object artifacts and source/control artifacts; do not create a new registry or object store.
- Write Markdown views under `views/`, static HTML under `views/site/`, and reports/manifests under `.wikify/views/`.
- Add focused unit tests in a new `tests/test_views.py` plus CLI parser/envelope tests in `tests/test_wikify_cli.py`.
- Update `README.md`, `LLM-Wiki-Cli-README.md`, and `scripts/fokb_protocol.md` with the human view command, artifact schemas, static output path, and no-hidden-pipeline boundary.

</code_context>

<specifics>
## Specific Ideas

- The human view layer should make the loop visible: `source add -> sync -> wikiize -> views`.
- The home page should answer: what exists, what changed recently, where should I browse first, and what needs attention?
- Source pages are important because trust comes from knowing where generated pages and claims came from.
- Graphify should appear here as graph entry points and relationship navigation, not as a broad graph feature expansion.
- LLM Wiki should appear here as wikiized, browsable source-backed pages and overview updates, not as a copied desktop app.

</specifics>

<deferred>
## Deferred Ideas

- `llms.txt`, `llms-full.txt`, page/citation indexes, context packs, related-topic queries, and agent JSON query commands belong to Phase 27.
- Maintenance findings that target personal wiki pages, source pages, human views, and agent exports belong to Phase 28.
- Automatic graph rebuilds, graph query/path/explain commands, and graph-driven maintenance actions should stay separate unless a later phase explicitly adds them.
- Full semantic extraction into topic/project/person/decision/timeline objects can be improved after the view layer can display existing objects honestly.
- Desktop/Tauri UI parity, hosted publishing, account systems, cloud sync, chat-first RAG, and vector search remain out of scope for v0.2.0.

</deferred>

---

*Phase: 26-human-wiki-views-and-local-static-output*
*Context gathered: 2026-04-29*
