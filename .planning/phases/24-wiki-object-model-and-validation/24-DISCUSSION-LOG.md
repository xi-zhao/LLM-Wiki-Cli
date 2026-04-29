# Phase 24: Wiki Object Model And Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 24-wiki-object-model-and-validation
**Areas discussed:** Schema set and boundaries, Object identity, Markdown and JSON artifacts, Validation command and result shape, Compatibility and graph integration

---

## Schema Set And Boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| Broad model now | Define all roadmap-required object families in Phase 24 so later phases build on one contract. | ✓ |
| Minimal page-only model | Define only wiki page/topic schemas now and add the rest later. | |
| Let later phases define their own schemas | Faster short-term, but risks human/agent/graph drift. | |

**User's choice:** Inferred from prior product direction and roadmap: broad model now.
**Notes:** Phase 24 explicitly covers source, source item, wiki page, topic, project, person, decision, timeline entry, citation, graph edge, and context pack objects.

---

## Object Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical object ids | Agents and graph edges reference stable object ids; paths remain secondary metadata. | ✓ |
| Path ids only | Reuse existing graph behavior as the long-term model. | |
| Title/slug ids | More readable, but unstable when titles change. | |

**User's choice:** Recommended default selected due non-interactive runtime: canonical object ids.
**Notes:** Existing path ids remain compatibility ids until generated pages carry explicit front matter ids.

---

## Markdown And JSON Artifacts

| Option | Description | Selected |
|--------|-------------|----------|
| JSON authoritative, front matter mirror | Best fit for agent stability plus human-readable wiki pages. | ✓ |
| Front matter authoritative | Simple for people, weaker for machine validation and indexing. | |
| JSON only | Agent-friendly but weakens the wiki as a human-facing artifact. | |

**User's choice:** Recommended default selected due non-interactive runtime: JSON authoritative, front matter mirror.
**Notes:** Use visible `artifacts/objects/` for object artifacts because the wiki object model is part of the product output, not only internal control state.

---

## Validation Command And Result Shape

| Option | Description | Selected |
|--------|-------------|----------|
| `wikify validate` | Clear top-level command for agents and humans; matches object-model requirement. | ✓ |
| Reuse `lint` | Existing legacy command, but less precise for v0.2 object contracts. | |
| Library-only validation | Useful internally but misses required CLI JSON error surface. | |

**User's choice:** Recommended default selected due non-interactive runtime: `wikify validate`.
**Notes:** Default validation should be compatibility-tolerant; strict mode should enforce declared v0.2 object documents.

---

## Compatibility And Graph Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Adapter bridge | Keep existing graph path semantics while adding object id metadata. | ✓ |
| Rewrite graph around object ids now | Cleaner eventually, too risky for Phase 24. | |
| Leave graph untouched | Safest short-term, but fails the roadmap criterion that graph builders can be pointed at the model. | |

**User's choice:** Recommended default selected due non-interactive runtime: adapter bridge.
**Notes:** `wikify graph`, `wikify maintain`, legacy `fokb`, and sample KB layouts must keep working.

---

## the agent's Discretion

- Exact module names.
- Exact artifact file names under `artifacts/objects/`.
- Exact object id hash length and slug normalization.
- Exact decomposition of parser, schema helpers, validator, and CLI handler.
- Exact warning/error split for legacy Markdown compatibility.

## Deferred Ideas

- Wikiization from queue to pages.
- Human views and static HTML.
- Agent exports and context packs.
- Maintenance repair against v0.2 wiki pages.
- Full YAML parser dependency, JSON Schema dependency, Pydantic, SQLite object store, vector retrieval, and entity-resolution inference.
