# Phase 27: Agent Wiki Interfaces And Context Packs - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 27 exposes the personal wiki as stable machine-readable context for agents.

This phase delivers agent-oriented exports (`llms.txt`, `llms-full.txt`, JSON indexes, citation queries, related-topic/page queries, and task-specific context packs) from the same v0.2 object/source/control artifacts that already feed `wikify wikiize` and `wikify views`.

This phase does not add hidden provider calls, embeddings/vector databases, chat/RAG UI, hosted sync, cloud publishing, provider-backed semantic enrichment, maintenance repair targeting, or new human browsing surfaces. Phase 28 owns maintenance integration.

</domain>

<decisions>
## Implementation Decisions

### Command Surface

- **D-01:** Add an object-aware agent command namespace, preferably `wikify agent`, rather than overloading legacy `wikify query`, `wikify search`, or `wikify graph`.
- **D-02:** Recommended subcommands are `wikify agent export`, `wikify agent context`, `wikify agent cite`, and `wikify agent related`.
- **D-03:** `wikify agent export` builds durable agent artifacts and should be the default prerequisite for agents that want stable files rather than one-off command output.
- **D-04:** `wikify agent context <query>` creates a task-specific context pack with explicit budget controls. It may also accept selectors such as object id, page id, source id, or type filters if planning finds this useful.
- **D-05:** `wikify agent cite <query-or-object-id>` returns source-backed citation/source-ref evidence without fabricating claim support.
- **D-06:** `wikify agent related <object-id-or-query>` returns ranked related objects/pages with explanation signals.
- **D-07:** Keep legacy `wikify query` behavior compatible. It can remain a legacy Markdown search/context command; Phase 27 should introduce the v0.2 object-aware surface separately.
- **D-08:** All Phase 27 commands must use existing Wikify JSON envelopes and stable exit codes. Dry-run modes must write nothing.

### Artifact Layout

- **D-09:** `llms.txt` and `llms-full.txt` should be written at the workspace root because that is the conventional location agents and tools look for.
- **D-10:** Machine-readable agent artifacts should live under a visible product artifact directory, recommended `artifacts/agent/`, not hidden only under `.wikify/`.
- **D-11:** Recommended generated artifacts are `artifacts/agent/page-index.json`, `artifacts/agent/citation-index.json`, `artifacts/agent/related-index.json`, `artifacts/agent/graph.json`, and `artifacts/agent/context-packs/<pack-id>.json`.
- **D-12:** Run reports and control manifests belong under `.wikify/agent/`, for example `.wikify/agent/last-agent-export.json` and `.wikify/agent/context-pack-manifest.json`.
- **D-13:** Context pack objects should also be representable as `wikify.context-pack.v1` objects under `artifacts/objects/context_packs/` when written. The pack object should reference selected object ids and source refs; it may include budget metadata and excerpts as additional fields.
- **D-14:** Avoid creating a second knowledge store. Agent artifacts are derived indexes and packs over the object/source/control model, not an independent database.

### Export Content

- **D-15:** `llms.txt` should be compact: product/workspace summary, core entry points, artifact paths, command hints, top page/source counts, and explicit guidance that agents should cite object/source refs.
- **D-16:** `llms-full.txt` should be richer but still generated from wiki artifacts, not raw source files. It can include object summaries, page metadata, source refs, citations, and generated wiki page bodies or bounded excerpts.
- **D-17:** Planner should add clear truncation metadata for `llms-full.txt` if any per-page or whole-file cap is used. Silent truncation is not acceptable.
- **D-18:** The page index should include page object id, title, summary, body path, review status, confidence, updated time, source refs, outbound links, backlinks, and any corresponding human view path.
- **D-19:** The citation index should merge explicit `citation` objects and page-level `source_refs`. Explicit citation objects are stronger evidence; page source refs are still useful fallback evidence.
- **D-20:** The agent graph export should be object-model-first. It may incorporate existing `graph/graph.json` when present, but should not mutate or replace legacy graph artifacts in Phase 27.
- **D-21:** Related index/query output should expose explanation signals, not opaque scores. Signals can include direct object links, backlinks, graph edges, shared sources, citation overlap, common neighbors, type affinity, and text/title match.

### Context Pack Selection

- **D-22:** Context pack selection must be deterministic and stdlib-only in Phase 27. Use lexical matching, object metadata, source refs, graph edges, backlinks, and existing relevance signals before considering embeddings in a future phase.
- **D-23:** Default context packs should prioritize source-backed generated wiki pages over raw source text. Raw source files should not be reread unless a future phase explicitly designs raw-source retrieval.
- **D-24:** A context pack must include why each item was selected: match terms, relation signals, source overlap, citation evidence, or direct object id match.
- **D-25:** Context packs need explicit budget accounting: requested max chars/tokens approximation, included character count, omitted object count, truncation flags, and per-item excerpt lengths.
- **D-26:** Recommended default budget behavior: bounded by characters with a reasonable default for coding agents, plus `--max-chars`, `--max-pages`, and `--include-full-pages` or equivalent explicit flags.
- **D-27:** Context pack output should be useful both as a written artifact and command stdout. Non-dry-run writes the pack; dry-run returns the would-select set without writing.
- **D-28:** Do not call external agents or LLM providers to choose context in Phase 27. Ranking must be explainable from local artifacts.

### Citation And Claim Evidence

- **D-29:** Citation queries must return stable ids, source ids, item ids when available, locator/path, confidence, snippet/span when present, and linked page/object ids.
- **D-30:** Citation output must distinguish explicit citations from weaker page-level source refs.
- **D-31:** If no citation evidence exists for a query, return an empty result with next actions, not a guessed citation.
- **D-32:** Context packs should carry citation/source-ref evidence alongside included page excerpts so downstream agents can cite sources without rereading raw files.

### Data Flow And Validation

- **D-33:** Phase 27 commands read the workspace manifest, source registry, source item index, object index, object JSON documents, generated page Markdown, validation report, view manifest/report, and optional graph artifacts.
- **D-34:** Non-dry-run export/context-pack writes should validate object artifacts first and fail with structured exit-code-2 style errors on hard validation failures.
- **D-35:** Missing optional artifacts should degrade gracefully. Missing graph artifacts can reduce related scores; missing citation objects can fall back to page source refs; missing views can omit human view paths.
- **D-36:** Missing required workspace/object artifacts or malformed control artifacts should return structured errors. Do not silently emit incomplete indexes as if complete.
- **D-37:** Generated indexes should use deterministic sorting and stable ids so agents can diff outputs and cache context.
- **D-38:** Agent artifacts should include schema versions. Recommended schemas include `wikify.agent-export.v1`, `wikify.page-index.v1`, `wikify.citation-index.v1`, `wikify.related-index.v1`, `wikify.agent-graph.v1`, and existing `wikify.context-pack.v1`.

### Product Experience For Agents

- **D-39:** The main product promise for Phase 27 is "agents can retrieve durable, source-backed context without rereading raw files every time."
- **D-40:** Prefer file artifacts and JSON commands over conversational behavior. The CLI should be easy for Codex, OpenClaw, Claude Code, and shell scripts to call.
- **D-41:** Agent-facing output must be honest about coverage gaps, validation status, and truncation. Confidence comes from traceability, not from assertive prose.
- **D-42:** The human wiki remains the visible product artifact from Phase 26; Phase 27 adds machine interfaces over the same artifact graph, not a separate agent backend.

### the agent's Discretion

- Exact module/package names, as long as Phase 27 logic is not buried in legacy `scripts/fokb.py`.
- Exact schema field ordering and report field names, as long as schemas are versioned, deterministic, and documented.
- Exact default character budgets, as long as they are tested and overridable.
- Exact scoring weights for related/context selection, as long as outputs expose signal-level explanations.
- Whether context pack JSON is accompanied by an optional Markdown companion, as long as JSON is authoritative.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Direction

- `AGENTS.md` - Product positioning, human/agent view split, CLI-first boundary, Graphify/LLM Wiki lessons, and generated wiki as the product artifact.
- `.planning/PROJECT.md` - Current v0.2.0 state, active agent interface requirement, constraints, and key decisions.

### Phase Scope

- `.planning/ROADMAP.md` - Phase 27 goal, requirements, success criteria, dependencies, and verification expectations.
- `.planning/REQUIREMENTS.md` - Agent wiki interface requirements `AGT-01` through `AGT-05`.
- `.planning/STATE.md` - Current GSD state and recent decisions affecting agent exports and context packs.

### Upstream Phase Context

- `.planning/phases/24-wiki-object-model-and-validation/24-CONTEXT.md` - Object schemas, object ids, context pack object contract, citation objects, graph edge compatibility, and validation rules.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-CONTEXT.md` - Generated page/object layout, source refs, object index updates, wikiization tasks, edit protection, and explicit agent handoff boundary.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-01-SUMMARY.md` - Implemented `wikify wikiize` behavior and generated page/object evidence.
- `.planning/phases/26-human-wiki-views-and-local-static-output/26-CONTEXT.md` - View generation source of truth, human/agent boundary, graph/timeline entry behavior, and no-hidden-pipeline constraints.
- `.planning/phases/26-human-wiki-views-and-local-static-output/26-01-SUMMARY.md` - Implemented `wikify views` behavior, view manifest, view tasks, docs, and residual Phase 27 scope.
- `.planning/phases/26-human-wiki-views-and-local-static-output/26-01-VERIFICATION.md` - Verification evidence for views, HTML, validation, and smoke workflow.

### Existing Implementation Patterns

- `wikify/objects.py` - Object schema versions, object paths, `citation` and `context_pack` constructors, and required fields.
- `wikify/object_validation.py` - Validation result shape, validation report path, strict validation behavior, and focused path validation.
- `wikify/wikiize.py` - Generated page body paths, source refs, object index writing, page hash guards, and run report conventions.
- `wikify/views.py` - Artifact loading, deterministic object grouping, graph/view artifact references, run report style, and no-hidden-pipeline view rendering pattern.
- `wikify/sync.py` - Source item index and ingest queue paths that citation and context pack commands should use for source/item metadata.
- `wikify/workspace.py` - Workspace manifest, source registry, visible artifact directories, and workspace discovery assumptions.
- `wikify/graph/builder.py` - Existing legacy graph artifact paths and current `wikify.graph.v1` shape.
- `wikify/graph/relevance.py` - Existing explainable relevance signals and scoring pattern that Phase 27 can adapt for object-level related queries.
- `wikify/graph/model.py` - Current graph node/edge dictionary conventions.
- `wikify/cli.py` - CLI parser extension pattern, JSON envelope handlers, and completion metadata style.
- `wikify/envelope.py` - Stable success/error envelope helpers.
- `scripts/fokb.py` - Legacy `query`/`search` behavior that must remain compatible but should not define the v0.2 object-aware agent interface.
- `tests/test_views.py` - Temporary workspace fixtures and semantic object fixtures useful for Phase 27 tests.
- `tests/test_wikiize.py` - Generated page/object and source-ref assertions.
- `tests/test_objects.py` - Citation and context pack constructor expectations.
- `tests/test_graph_relevance.py` - Signal-level relevance expectations.
- `tests/test_wikify_cli.py` - CLI parser/envelope testing pattern.
- `README.md`, `LLM-Wiki-Cli-README.md`, and `scripts/fokb_protocol.md` - Current public docs and protocol registry to update with Phase 27 commands and schemas.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `wikify.config.discover_base`: use the same workspace resolution behavior as existing commands.
- `wikify.workspace.load_workspace`: load manifest and source registry for export headers, source metadata, and artifact paths.
- `wikify.objects.object_artifacts_dir`, `object_index_path`, `object_document_path`, `SCHEMA_VERSIONS`, `make_citation_object`, and `make_context_pack_object`: enumerate and write object-model artifacts.
- `wikify.object_validation.validate_workspace_objects`: run strict validation before non-dry-run agent artifact writes.
- `wikify.wikiize` generated page metadata and source refs: primary source of agent context and citation fallback.
- `wikify.views` object loading/grouping patterns: useful starting point for page/citation/index loaders, but Phase 27 should use a dedicated module.
- `wikify.graph.relevance.compute_relevance`: reusable approach for explainable relatedness, though Phase 27 should adapt it to object ids and object artifacts.
- `wikify.envelope.envelope_ok` and `envelope_error`: keep stdout stable for agents.

### Established Patterns

- Visible product artifacts live under `wiki/`, `views/`, `graph/`, and `artifacts/`; `.wikify/` stores control-plane state.
- Commands are explicit. Prior phases rejected hidden sync/wikiize/graph/provider/agent execution.
- Generated visible Markdown is hash-guarded when a person may edit it; machine indexes can be regenerated deterministically.
- Object validation blocks writes on hard object errors.
- Tests use `unittest`, temporary workspaces, direct module calls, and `cli.main` JSON envelopes.
- Existing legacy `query` is string search over Markdown files and is not object-model-aware.

### Integration Points

- Add a focused module such as `wikify/agent.py`, `wikify/agent_exports.py`, or a small `wikify/agent/` package for exports, indexes, context packs, cite, and related logic.
- Add a `wikify agent` subparser namespace in `wikify/cli.py` without disturbing `agent-profile` or legacy `query`.
- Read object artifacts from `artifacts/objects/` and generated page Markdown from `wiki_page.body_path`.
- Write root `llms.txt` and `llms-full.txt`; write JSON indexes under `artifacts/agent/`; write control reports/manifests under `.wikify/agent/`.
- Add focused tests, likely `tests/test_agent_exports.py`, plus CLI tests in `tests/test_wikify_cli.py`.
- Update public docs and protocol docs with command usage, schema versions, artifact locations, budget semantics, and no-hidden-provider boundaries.

</code_context>

<specifics>
## Specific Ideas

- Treat Phase 27 as the agent equivalent of Phase 26: same wiki, different interface.
- Agents should be able to start from `llms.txt`, then use JSON indexes and context-pack commands for task-specific detail.
- Context packs should look like durable evidence bundles: selected pages, why selected, source refs/citations, related objects, and explicit truncation/budget metadata.
- Related queries should follow the Graphify lesson: explain relationships with provenance/signals rather than returning opaque similarity.
- LLM Wiki influence should stay at the product behavior level: wikiized, source-backed knowledge that can be incrementally exported for agents.

</specifics>

<deferred>
## Deferred Ideas

- Vector embeddings, semantic search, fuzzy retrieval, and hybrid embedding ranking belong to a future retrieval phase.
- Chat-first RAG UI is out of scope for v0.2.0.
- Provider-backed context selection or summarization belongs to a future explicit provider runtime phase.
- Maintenance findings that target agent exports and context packs belong to Phase 28.
- Publishing `llms.txt` or wiki artifacts to a hosted URL belongs to future sharing/publishing scope.
- Direct OpenClaw/Codex/Claude Code plugin installation helpers can be added later; Phase 27 should keep generic CLI/files first.

</deferred>

---

*Phase: 27-agent-wiki-interfaces-and-context-packs*
*Context gathered: 2026-04-29*
