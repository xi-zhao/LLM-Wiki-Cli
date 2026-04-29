# Phase 23: Pattern Map

**Phase:** 23 - Incremental Sync And Ingest Queue
**Created:** 2026-04-29

## Closest Existing Patterns

### Workspace And Registry State

- **Analog:** `wikify/workspace.py`
- **Pattern:** Focused module owns schema constants, path helpers, structured errors, timestamp helpers, JSON load/write, and deterministic result dictionaries.
- **Use for Phase 23:** Add a focused sync module with schema constants for source items, sync run report, and ingest queue. Mirror the atomic JSON write style and structured `WorkspaceError`-like exception shape.

### CLI Command Wiring

- **Analog:** `wikify/cli.py`
- **Pattern:** Native Wikify commands extend the legacy `fokb` parser in `build_parser()`, expose `cmd_*` functions, and return `envelope_ok()` or `envelope_error()`.
- **Use for Phase 23:** Add top-level `wikify sync` with `--source` and `--dry-run`, using command name `sync` in the JSON envelope.

### JSON Envelopes

- **Analog:** `wikify/envelope.py`
- **Pattern:** Command handlers return `(payload, exit_code)` where `payload.ok`, `payload.command`, `payload.exit_code`, and `payload.result` or `payload.error` are stable.
- **Use for Phase 23:** `sync` must expose stable success/error output. Error details should include paths or ids when an artifact/source lookup fails.

### Current-State Queue Artifacts

- **Analog:** `wikify/maintenance/task_queue.py` and `wikify/maintenance/task_reader.py`
- **Pattern:** Queue artifacts are JSON documents with a schema version, generated timestamp, summary, and task/item list. Selection and filtering operate over current-state JSON.
- **Use for Phase 23:** Create `.wikify/queues/ingest-items.json` as a current-state queue. Do not introduce JSONL history or SQLite in this phase.

### Legacy Ingest Boundary

- **Analog:** `scripts/ingest_any_url.py`
- **Pattern:** Existing ingest uses subprocess calls and mutates parsed/topic/sorted outputs.
- **Use for Phase 23:** Treat this as an explicit non-pattern. Sync must not call this script or reuse its side-effectful behavior.

### Legacy Source Index

- **Analog:** `scripts/source_index_manager.py`
- **Pattern:** Markdown table source index used for old article/source note navigation.
- **Use for Phase 23:** Keep it out of the v0.2 sync core. Phase 23 writes machine-readable `.wikify/` artifacts, not Markdown table state.

### Tests

- **Analog:** `tests/test_workspace.py`, `tests/test_wikify_cli.py`, `tests/test_maintenance_task_reader.py`
- **Pattern:** Use `unittest`, temporary directories, direct module imports, and CLI `main()` invocation with JSON stdout assertions.
- **Use for Phase 23:** Add `tests/test_sync.py` for module behavior and extend `tests/test_wikify_cli.py` for parser/command behavior.

## New Files Expected

- `wikify/sync.py` - source item discovery, fingerprinting, classification, source item index persistence, sync report persistence, ingest queue persistence, registry sync metadata updates.
- `tests/test_sync.py` - focused module-level tests for sync behavior.

## Modified Files Expected

- `wikify/cli.py` - add `sync` command and error handling.
- `tests/test_wikify_cli.py` - add parser and command-level tests for `wikify sync`.
- `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md` - document command, schemas, artifacts, statuses, dry-run, and no-fetch/no-ingest boundary.
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` - update after execution, not during initial implementation tasks.

## Non-Patterns

- Do not call `scripts/ingest_any_url.py` or `wikify ingest` from sync.
- Do not fetch remote URLs, ping hosts, run `git`, clone repositories, or call providers.
- Do not write `graph/`, `sorted/`, `articles/`, `topics/`, `wiki/`, `artifacts/`, or `views/` from sync.
- Do not introduce background file watching, configurable sync policies, SQLite, or append-only sync history in Phase 23.
