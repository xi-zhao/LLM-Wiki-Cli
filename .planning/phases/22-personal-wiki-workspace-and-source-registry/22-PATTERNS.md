# Phase 22: Pattern Map

**Phase:** 22 - Personal Wiki Workspace And Source Registry
**Created:** 2026-04-29

## Closest Existing Patterns

### CLI Command Wiring

- **Analog:** `wikify/cli.py`
- **Pattern:** Native Wikify commands are added by extending the legacy `fokb` parser in `build_parser()`, then assigning a `cmd_*` function that returns `envelope_ok()` or `envelope_error()`.
- **Use for Phase 22:** Add top-level `init` and grouped `source add/list/show` commands in `wikify/cli.py` using the same envelope return style.

### JSON Envelopes

- **Analog:** `wikify/envelope.py`
- **Pattern:** Commands return `(payload, exit_code)` where `payload.ok`, `payload.command`, `payload.exit_code`, and either `payload.result` or `payload.error` are stable.
- **Use for Phase 22:** `init`, `source.add`, `source.list`, and `source.show` must expose stable JSON envelopes. Error cases should use structured codes and details.

### Project-Root Resolution

- **Analog:** `wikify/config.py`
- **Pattern:** Base path currently resolves from `WIKIFY_BASE`, then `FOKB_BASE`, then app root.
- **Use for Phase 22:** Preserve existing env behavior while adding workspace manifest awareness. Do not break legacy callers that rely on `WIKIFY_BASE` or `FOKB_BASE`.

### JSON State Modules

- **Analog:** `wikify/maintenance/agent_profile.py`
- **Pattern:** A focused module owns JSON schema constants, path helpers, validation, load/write functions, structured custom errors, timestamps, and CLI-facing result dictionaries.
- **Use for Phase 22:** Create a focused workspace/source registry module rather than extending `scripts/source_index_manager.py`.

### Filesystem Tests

- **Analog:** `tests/test_maintenance_agent_profile.py`, `tests/test_wikify_cli.py`, `tests/test_markdown_index.py`
- **Pattern:** Tests use `tempfile`/`Path` workspaces, import modules directly, and assert exact parser args or result dictionary fields.
- **Use for Phase 22:** Add focused tests for workspace initialization, registry persistence, duplicate add, source inspection, CLI parsing, and envelope outputs.

## New Files Expected

- `wikify/workspace.py` - workspace manifest, registry path helpers, source add/list/show, bounded local fingerprinting, and structured errors.
- `tests/test_workspace.py` - focused module-level tests for Phase 22 behavior.

## Modified Files Expected

- `wikify/config.py` - add manifest-aware discovery helpers while preserving `WIKIFY_BASE` and `FOKB_BASE` precedence.
- `wikify/cli.py` - add `init` and `source add/list/show` commands and envelope error handling.
- `tests/test_wikify_cli.py` - parser and command-level CLI tests.
- `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md` - document Phase 22 commands and artifact contracts.

## Non-Patterns

- Do not promote `scripts/source_index_manager.py` into the new registry model; it is a legacy Markdown table index helper.
- Do not reuse `topics/`, `sources/`, `sorted/`, or `articles/` as the canonical v0.2 workspace model.
- Do not add provider calls, network fetches, recursive scans, wikiization, human view generation, or agent exports in Phase 22.
