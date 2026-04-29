# Phase 25: Pattern Map

**Phase:** 25 - Source-Backed Wikiization Pipeline
**Created:** 2026-04-29

## Closest Existing Patterns

### Queue And Source Item State

- **Analog:** `wikify/sync.py`
- **Pattern:** Source item discovery and ingest queue state are current-state JSON artifacts with explicit schema versions, deterministic ids, timestamp fields, structured errors, and atomic JSON writes.
- **Use for Phase 25:** Read `.wikify/queues/ingest-items.json` and `.wikify/sync/source-items.json` together. Select queued `wikiize_source_item` entries, update lifecycle status per entry, and write a separate wikiization run report so agents can inspect outcomes without diffing queue state.

### Object And Markdown Contracts

- **Analog:** `wikify/objects.py`, `wikify/frontmatter.py`, `wikify/object_validation.py`
- **Pattern:** Wiki object dictionaries are machine-authoritative JSON artifacts under `artifacts/objects/`; Markdown front matter mirrors object metadata through a bounded stdlib parser/serializer; validation emits structured records and optional reports.
- **Use for Phase 25:** Generate `wikify.wiki-page.v1` objects with source refs, render matching front matter into `wiki/pages/`, update `artifacts/objects/object-index.json`, and run strict validation before marking queue entries completed.

### CLI Command Wiring

- **Analog:** `wikify/cli.py`
- **Pattern:** Native Wikify commands add a top-level parser, implement a `cmd_*` handler, catch typed module exceptions, and return `envelope_ok()` or `envelope_error()`.
- **Use for Phase 25:** Add top-level `wikify wikiize` with `--dry-run`, bounded selectors, and explicit agent execution flags. Use command name `wikiize` in the JSON envelope.

### Explicit Agent Execution

- **Analog:** `wikify/maintenance/agent_profile.py`, `wikify/maintenance/bundle_request.py`, `wikify/maintenance/bundle_producer.py`
- **Pattern:** External semantic work uses visible request artifacts, explicit `--agent-command` or `--agent-profile` selection, stdin JSON contracts, captured stdout/stderr, timeout handling, and no hidden provider calls.
- **Use for Phase 25:** Build a `wikify.wikiization-request.v1` artifact when semantic enrichment is requested, invoke only explicit agent commands, accept a structured result artifact/stdout, and keep Wikify responsible for path validation, front matter rendering, object validation, and final writes.

### Review Task Artifacts

- **Analog:** `wikify/maintenance/task_queue.py`
- **Pattern:** Ambiguous work becomes machine-readable tasks with evidence, write scope, agent instructions, acceptance checks, `requires_user`, and status.
- **Use for Phase 25:** Create `.wikify/queues/wikiization-tasks.json` for remote-without-content, unsupported, low-confidence, drifted, or failed wikiization work. Do not overload graph-specific `sorted/graph-agent-tasks.json`.

### User Edit Protection

- **Analog:** `wikify/maintenance/patch_apply.py`, Phase 25 context decisions
- **Pattern:** Existing content mutation paths are hash-guarded and refuse drift instead of silently overwriting.
- **Use for Phase 25:** Store generated content hash and source item fingerprint metadata. Existing generated pages can be replaced only when the stored generated hash still matches the current file. Unknown drift creates a wikiization task and queue `needs_review` status.

### Tests

- **Analog:** `tests/test_sync.py`, `tests/test_object_validation.py`, `tests/test_wikify_cli.py`
- **Pattern:** Tests use `unittest`, temporary directories, direct imports, CLI `main()` invocations with JSON stdout assertions, and no external services.
- **Use for Phase 25:** Add focused `tests/test_wikiize.py` for queue consumption, page/object generation, source refs, incremental updates, edit protection, task creation, validation, and explicit agent handoff. Extend CLI tests for parser flags and envelope behavior.

## New Files Expected

- `wikify/wikiize.py` - queue selection, deterministic page generation, wikiization run reports, wikiization task queue, object writes, validation gate, and explicit agent handoff support.
- `tests/test_wikiize.py` - module-level tests for the wikiization pipeline.

## Modified Files Expected

- `wikify/cli.py` - add `wikiize` command, selector flags, dry-run flag, and explicit agent command/profile flags.
- `tests/test_wikify_cli.py` - add parser and command-level tests for `wikify wikiize`.
- `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md` - document command, artifacts, schemas, lifecycle statuses, source traceability, edit protection, review tasks, and explicit agent handoff.
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` - update after execution, not during initial implementation tasks.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-01-SUMMARY.md` and `25-01-VERIFICATION.md` - write after execution.

## Non-Patterns

- Do not call `scripts/ingest_any_url.py`, legacy `wikify ingest`, provider SDKs, network fetchers, `git clone`, or background watchers from `wikify wikiize`.
- Do not generate source pages, topic pages, home pages, static HTML, `llms.txt`, context packs, agent query APIs, or broad graph maintenance flows in Phase 25.
- Do not store generated wiki pages only as JSON; the human-readable Markdown page is a required product artifact.
- Do not silently overwrite user-edited generated pages or legacy wiki files.
- Do not put wikiization tasks in `sorted/graph-agent-tasks.json`; keep them in a wikiization-specific queue.
- Do not introduce Pydantic, JSON Schema, YAML dependencies, SQLite, vector databases, or hidden LLM/provider calls.
