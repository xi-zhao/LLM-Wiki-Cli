# Phase 26: Pattern Map

**Phase:** 26 - Human Wiki Views And Local Static Output
**Created:** 2026-04-29

## Closest Existing Patterns

### Generated Artifact Pipeline

- **Analog:** `wikify/wikiize.py`
- **Pattern:** A top-level command loads workspace control artifacts, plans deterministic output paths, supports dry-run with zero writes, writes visible product artifacts plus `.wikify/` run reports, and returns a stable JSON envelope.
- **Use for Phase 26:** Implement `wikify views` as a rendering command that plans and writes Markdown views under `views/`, static HTML under `views/site/`, `.wikify/views/last-views.json`, `.wikify/views/view-manifest.json`, and `.wikify/queues/view-tasks.json`.

### Object And Source Data Loading

- **Analog:** `wikify/objects.py`, `wikify/object_validation.py`, `wikify/workspace.py`, `wikify/sync.py`
- **Pattern:** Wiki object JSON artifacts are machine-authoritative under `artifacts/objects/`; source registry and source item facts stay in `.wikify/registry/` and `.wikify/sync/`; validation returns structured records.
- **Use for Phase 26:** Build views from `artifacts/objects/object-index.json`, object JSON files, `.wikify/registry/sources.json`, `.wikify/sync/source-items.json`, ingest queue entries, wikiization tasks, and validation records. Do not reread raw source files or create a parallel view store.

### Hash-Guarded Visible Output

- **Analog:** `wikify/wikiize.py` generated page update guard.
- **Pattern:** Visible generated Markdown is overwritten only when stored generated hashes prove current content still matches the previous generated output. Drift becomes machine-readable task work instead of silent replacement.
- **Use for Phase 26:** Use `.wikify/views/view-manifest.json` to track generated Markdown and HTML hashes. If a generated Markdown view drifted, report a conflict and create `.wikify/queues/view-tasks.json` rather than overwriting it.

### Markdown Metadata And Rendering

- **Analog:** `wikify/frontmatter.py`
- **Pattern:** Generated Markdown can carry small, deterministic metadata using stdlib-only front matter serialization.
- **Use for Phase 26:** View Markdown can include bounded front matter with `schema_version`, `id`, `type`, `title`, `view_path`, `generated_at`, and source object ids where useful. The human body remains readable without JSON tooling.

### Static HTML Rendering

- **Analog:** `wikify/graph/html.py`
- **Pattern:** Existing graph HTML uses stdlib `html.escape`, inline/local CSS, and no external assets.
- **Use for Phase 26:** Add a dedicated bounded Markdown-to-HTML renderer for view pages. Reuse the safety pattern, not graph coupling. HTML output lives under `views/site/` and is local-file friendly.

### CLI Command Wiring

- **Analog:** `wikify/cli.py`
- **Pattern:** Native commands import focused module entry points, expose top-level parsers, catch typed module errors, attach completion metadata, and return `envelope_ok()` or `envelope_error()`.
- **Use for Phase 26:** Add `cmd_views`, parser flags `--dry-run`, `--no-html`, and optional `--section`, catch `ViewGenerationError`, and return command name `views`.

### Tests

- **Analog:** `tests/test_wikiize.py`, `tests/test_object_validation.py`, `tests/test_wikify_cli.py`
- **Pattern:** Tests use `unittest`, temporary directories, workspace init helpers, direct module calls, CLI `main()` invocation, and JSON stdout assertions.
- **Use for Phase 26:** Add `tests/test_views.py` covering dry-run, Markdown view generation, source pages, collections, review views, graph/timeline empty states, static HTML, hash guard conflicts, missing-data behavior, and validation failure behavior. Extend CLI tests for parser and command envelope behavior.

## New Files Expected

- `wikify/views.py` - data loading, view planning, Markdown rendering, HTML rendering, manifests, drift conflicts, view task queue, reports, and run entry point.
- `tests/test_views.py` - module-level tests for human view generation.

## Modified Files Expected

- `wikify/cli.py` - add `wikify views` command, flags, typed error handling, and envelope completion metadata.
- `tests/test_wikify_cli.py` - add parser and CLI envelope tests for `wikify views`.
- `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md` - document command, artifacts, schemas, static site output, boundaries, and missing-data behavior.
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` - update after execution, not during initial implementation tasks.
- `.planning/phases/26-human-wiki-views-and-local-static-output/26-01-SUMMARY.md` and `26-01-VERIFICATION.md` - write after execution.

## Non-Patterns

- Do not run `wikify sync`, `wikify wikiize`, `wikify graph`, external agents, providers, network fetchers, repository commands, or background watchers from `wikify views`.
- Do not infer missing topics, people, projects, decisions, timeline events, or citations from raw page text in Phase 26.
- Do not create a separate human-only database or object store.
- Do not add Markdown, YAML, templating, JS framework, web server, browser automation, vector database, or provider dependencies.
- Do not overwrite user-edited visible view Markdown without a manifest hash match.
- Do not build `llms.txt`, context packs, agent query APIs, or maintenance targeting in Phase 26.
