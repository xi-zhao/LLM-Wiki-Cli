# Phase 27: Pattern Map

**Phase:** 27 - Agent Wiki Interfaces And Context Packs
**Created:** 2026-04-29

## Closest Existing Patterns

### Explicit Artifact Export Command

- **Analog:** `wikify/wikiize.py` and `wikify/views.py`
- **Pattern:** A top-level CLI command discovers the workspace, loads existing product/control artifacts, supports dry-run with zero writes, validates object artifacts before non-dry-run writes, emits deterministic visible artifacts plus `.wikify/` control reports, and returns a stable JSON envelope.
- **Use for Phase 27:** Implement `wikify agent export` as the agent-facing counterpart to `wikify views`: read the object/source/wiki/view/graph artifacts, write root `llms.txt` and `llms-full.txt`, write machine indexes under `artifacts/agent/`, and write run reports under `.wikify/agent/`.

### Object And Source Snapshot Loading

- **Analog:** `wikify/views.py`
- **Pattern:** The renderer loads `wikify.json`, `.wikify/registry/sources.json`, `.wikify/sync/source-items.json`, `.wikify/queues/ingest-items.json`, `.wikify/queues/wikiization-tasks.json`, `artifacts/objects/object-index.json`, object JSON files, validation records, and optional graph artifacts without rereading raw source files.
- **Use for Phase 27:** Add a focused `wikify/agent.py` snapshot loader that reuses the same source of truth, then derives page index, citation index, related index, agent graph, context packs, and `llms` exports from that snapshot.

### Object Validation Before Writes

- **Analog:** `wikify/views.py::_validate_before_write`
- **Pattern:** Non-dry-run generation runs `validate_workspace_objects(root, path=object_artifacts_dir(root), strict=True, write_report=True)` and returns structured exit-code-2 style errors on hard validation failures.
- **Use for Phase 27:** All non-dry-run `agent export` and `agent context` writes must validate first. Read-only `agent cite` and `agent related` can degrade with warnings but must not pretend malformed required artifacts are valid.

### Deterministic Visible And Control Artifacts

- **Analog:** `wikify/workspace.py`, `wikify/wikiize.py`, `wikify/views.py`
- **Pattern:** Visible generated product artifacts live under stable product directories; control-plane reports/manifests live under `.wikify/`; writes use atomic temp-file replacement and sorted JSON.
- **Use for Phase 27:** Root `llms.txt` and `llms-full.txt` are explicit visible outputs. JSON indexes live under `artifacts/agent/`. Run reports and context-pack manifests live under `.wikify/agent/`. Context pack object documents live under `artifacts/objects/context_packs/`.

### Explainable Relatedness

- **Analog:** `wikify/graph/relevance.py`
- **Pattern:** Relevance uses deterministic weights and exposes signal details such as direct links, source overlap, common neighbors, and type affinity instead of opaque scores.
- **Use for Phase 27:** Related query and context-pack ranking should expose signal-level explanations: direct object links, backlinks, graph edges, shared sources, citation overlap, common neighbors, type affinity, and text/title match.

### Citation And Context Pack Object Contracts

- **Analog:** `wikify/objects.py` and `tests/test_objects.py`
- **Pattern:** `make_citation_object()` and `make_context_pack_object()` already define stable object contracts for citations and context packs.
- **Use for Phase 27:** Citation indexes should merge explicit citation objects with page-level `source_refs`, marking evidence strength. Context pack writes should create both `artifacts/agent/context-packs/<pack-id>.json` and a `wikify.context-pack.v1` object under `artifacts/objects/context_packs/`.

### CLI Namespace Wiring

- **Analog:** `wikify/cli.py`
- **Pattern:** Native commands import focused module entry points, add argparse subcommands, catch typed errors, attach completion metadata, and return `envelope_ok()` or `envelope_error()`.
- **Use for Phase 27:** Add `wikify agent` as a subparser namespace with `export`, `context`, `cite`, and `related`. Keep `agent-profile` and legacy `query/search/graph` behavior compatible.

### Unit Test Style

- **Analog:** `tests/test_views.py`, `tests/test_wikiize.py`, `tests/test_wikify_cli.py`, `tests/test_graph_relevance.py`
- **Pattern:** Tests use `unittest`, temporary workspaces, direct module calls, `cli.main()` JSON envelope assertions, deterministic fixture object writes, and no pytest-specific features.
- **Use for Phase 27:** Add `tests/test_agent.py` for module behavior and extend `tests/test_wikify_cli.py` for parser/envelope behavior. Reuse temporary workspace fixture patterns from `tests/test_views.py`.

## New Files Expected

- `wikify/agent.py` - agent snapshot loading, export/index generation, `llms` rendering, context-pack selection/writing, citation query, related query, path helpers, schema constants, and typed errors.
- `tests/test_agent.py` - unit tests for dry-run export, durable artifact writes, page/citation/related indexes, context-pack budgeting, citation evidence, related ranking signals, and missing-data behavior.

## Modified Files Expected

- `wikify/cli.py` - add `wikify agent export/context/cite/related` parser namespace, typed error handling, and JSON envelope completion metadata.
- `tests/test_wikify_cli.py` - add parser and CLI envelope tests for agent subcommands.
- `README.md` - document agent export artifacts, command usage, context pack behavior, and trust boundaries.
- `LLM-Wiki-Cli-README.md` - mirror public CLI usage and artifact contract.
- `scripts/fokb_protocol.md` - document agent command protocol, schemas, output envelopes, and backward-compatible legacy query boundary.
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` - update after execution, not during initial implementation tasks.
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-01-SUMMARY.md`
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-02-SUMMARY.md`
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-03-SUMMARY.md`
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-01-VERIFICATION.md`
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-02-VERIFICATION.md`
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-03-VERIFICATION.md`

## Non-Patterns

- Do not overload legacy `wikify query`, `wikify search`, or `wikify graph` for the v0.2 object-aware agent surface.
- Do not run sync, wikiize, views, graph, provider calls, external agents, network fetchers, repository commands, or background watchers from `wikify agent export/context/cite/related`.
- Do not introduce embeddings, vector databases, hidden LLM selection, provider SDKs, or semantic rerankers in Phase 27.
- Do not reread raw source files for context packs; prioritize source-backed generated wiki pages and object/source references.
- Do not create a second knowledge store. Agent artifacts are derived indexes and context bundles over the existing object/source/wiki model.
- Do not fabricate citations. If evidence is missing, return empty evidence plus next actions.
- Do not silently truncate `llms-full.txt` or context packs. Include explicit budget and truncation metadata.
- Do not hide machine artifacts under `.wikify/` only; visible agent outputs belong under root files and `artifacts/agent/`.
