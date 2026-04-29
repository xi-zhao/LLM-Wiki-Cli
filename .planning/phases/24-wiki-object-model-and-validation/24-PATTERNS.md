# Phase 24: Pattern Map

**Phase:** 24 - Wiki Object Model And Validation
**Created:** 2026-04-29

## Closest Existing Patterns

### Schema Constants And Artifact Helpers

- **Analog:** `wikify/workspace.py`, `wikify/sync.py`
- **Pattern:** Focused modules own explicit schema version constants, path helpers, deterministic ids, structured errors, timestamp helpers, JSON load/write helpers, and result dictionaries.
- **Use for Phase 24:** Add `wikify/objects.py` and `wikify/object_validation.py` instead of burying object schema logic in scripts or graph extractors.

### Source And Source Item Truth

- **Analog:** `wikify/workspace.py`, `wikify/sync.py`
- **Pattern:** Source registry and source item index are durable control-plane JSON artifacts under `.wikify/`.
- **Use for Phase 24:** Validate source refs against `.wikify/registry/sources.json` and `.wikify/sync/source-items.json` when present. Provide adapters, not duplicate registries.

### CLI Command Wiring

- **Analog:** `wikify/cli.py`
- **Pattern:** Native Wikify commands extend `build_parser()`, implement `cmd_*`, catch typed exceptions, and return `envelope_ok()` or `envelope_error()`.
- **Use for Phase 24:** Add top-level `wikify validate` with `--path` and `--strict`, preserving existing commands.

### JSON Envelopes

- **Analog:** `wikify/envelope.py`
- **Pattern:** Stable machine output has `ok`, `command`, `exit_code`, and either `result` or `error`.
- **Use for Phase 24:** Validation success returns `result.schema_version == "wikify.object-validation.v1"`. Validation failure returns `error.code == "object_validation_failed"` with the full validation document in `error.details.validation`.

### Markdown Object Scanning

- **Analog:** `wikify/markdown_index.py`
- **Pattern:** Graph and maintenance use a lightweight immutable `WikiObject` shape with absolute path, relative path, title, text, and line tuples.
- **Use for Phase 24:** Extend the shape additively with metadata/object id/canonical type. Keep existing `type` and `relative_path` semantics.

### Graph Compatibility

- **Analog:** `wikify/graph/model.py`, `wikify/graph/extractors.py`, `tests/test_graph_extractors.py`
- **Pattern:** Graph nodes are path-id based; graph edges use `source`, `target`, `type`, `provenance`, `confidence`, `source_path`, `line`, and `label`.
- **Use for Phase 24:** Add object id metadata to nodes while preserving path ids. Keep `GraphEdge` shape aligned with `wikify.graph-edge.v1`.

### Front Matter Writing

- **Analog:** `scripts/topic_maintainer.py`, `scripts/generate_topic_digest.py`
- **Pattern:** Existing scripts write small YAML-like front matter manually and avoid adding a YAML dependency.
- **Use for Phase 24:** Centralize a small stdlib parser/serializer in `wikify/frontmatter.py`; support deterministic scalar and JSON-flow values.

### Tests

- **Analog:** `tests/test_workspace.py`, `tests/test_sync.py`, `tests/test_wikify_cli.py`, `tests/test_markdown_index.py`, `tests/test_graph_extractors.py`
- **Pattern:** Tests use `unittest`, temporary directories, direct imports, and CLI `main()` calls with JSON stdout assertions.
- **Use for Phase 24:** Add focused module tests for objects/front matter/validation, then extend CLI, Markdown index, and graph extractor tests.

## New Files Expected

- `wikify/objects.py` - schema versions, object type vocabulary, required fields, artifact paths, constructors, id helpers, and source/source-item adapters.
- `wikify/frontmatter.py` - constrained front matter parser/serializer.
- `wikify/object_validation.py` - validation scanner, structured validation records, source/link resolution, and report helpers.
- `tests/test_objects.py` - object model and schema constructor tests.
- `tests/test_frontmatter.py` - front matter parser/serializer round-trip and invalid syntax tests.
- `tests/test_object_validation.py` - validator result, strict/default behavior, duplicate id, unresolved link, and unresolved source ref tests.

## Modified Files Expected

- `wikify/markdown_index.py` - add metadata/object id/canonical type without breaking current object scanning.
- `wikify/graph/model.py` - add optional node object id metadata while preserving existing node fields.
- `wikify/graph/extractors.py` - populate graph node object id from `WikiObject`.
- `wikify/cli.py` - add `validate` command and error handling.
- `tests/test_markdown_index.py` - assert metadata/front matter behavior and existing compatibility.
- `tests/test_graph_extractors.py` - assert graph path ids remain stable and object ids are exposed.
- `tests/test_wikify_cli.py` - add parser and command-level tests for `wikify validate`.
- `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md` - document object schemas, front matter subset, validation command, result shape, and Phase 24 boundary.
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` - update after execution, not during initial implementation tasks.

## Non-Patterns

- Do not introduce Pydantic, JSON Schema, YAML libraries, SQLite, vector databases, or provider calls.
- Do not process `.wikify/queues/ingest-items.json` into wiki pages in Phase 24.
- Do not rewrite Markdown files to add front matter during validation.
- Do not change path-based graph ids or require generated content mutation for graph extraction.
- Do not duplicate Phase 22 source registry or Phase 23 source item index.
- Do not build human views, `llms.txt`, context packs, citation exports, semantic entity inference, or maintenance repair flows in Phase 24.
