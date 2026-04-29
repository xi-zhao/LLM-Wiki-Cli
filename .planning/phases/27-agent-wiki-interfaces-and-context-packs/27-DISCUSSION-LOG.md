# Phase 27: Agent Wiki Interfaces And Context Packs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 27-agent-wiki-interfaces-and-context-packs
**Areas discussed:** Command surface, artifact layout, export content, context pack selection, citation evidence, validation and data flow

---

## Command Surface

| Option | Description | Selected |
|--------|-------------|----------|
| New `wikify agent` namespace | Keeps v0.2 object-aware agent commands separate from legacy Markdown `query/search` commands. | ✓ |
| Reuse legacy `wikify query` | Lower CLI surface area, but risks breaking compatibility and mixing old path-based behavior with object-model behavior. | |
| Many top-level commands | Direct commands such as `wikify cite` and `wikify related`, but increases top-level clutter. | |

**User's choice:** Non-interactive fallback selected the recommended `wikify agent` namespace.
**Notes:** This preserves `fokb` and legacy `query` compatibility while making the agent interface explicit.

---

## Artifact Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Root `llms.txt` plus `artifacts/agent/` JSON | Conventional llms files at root; machine indexes are visible product artifacts. | ✓ |
| Everything under `.wikify/agent/` | Keeps root clean, but hides agent artifacts and weakens the product artifact model. | |
| Reuse `views/` for agent artifacts | Simple directory count, but mixes human and machine surfaces. | |

**User's choice:** Non-interactive fallback selected root llms files plus visible `artifacts/agent/` JSON.
**Notes:** Control reports/manifests still belong under `.wikify/agent/`.

---

## Export Content

| Option | Description | Selected |
|--------|-------------|----------|
| Compact `llms.txt`, richer `llms-full.txt` | Gives agents a small entry point and a fuller local context file without raw-source rereads. | ✓ |
| Only JSON indexes | Easier to parse, but misses the `llms.txt` convention and quick agent onboarding path. | |
| Full raw-source export | Maximal text, but violates source-of-truth and scope boundaries. | |

**User's choice:** Non-interactive fallback selected compact plus richer llms exports.
**Notes:** `llms-full.txt` should expose truncation metadata if budgets are used.

---

## Context Pack Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic lexical/object/graph selection | Stdlib-only, explainable, testable, and aligned with v0.2 constraints. | ✓ |
| Embedding/vector search | Better semantic recall, but explicitly deferred in v0.2.0. | |
| Hidden LLM selector | Potentially flexible, but violates explicit provider/agent boundaries. | |

**User's choice:** Non-interactive fallback selected deterministic local selection.
**Notes:** Context packs need budget accounting, selection rationale, source refs, and truncation flags.

---

## Citation Evidence

| Option | Description | Selected |
|--------|-------------|----------|
| Merge citation objects and page source refs | Uses strongest available evidence while preserving useful fallback evidence. | ✓ |
| Citation objects only | Cleaner evidence model, but too sparse until richer extraction exists. | |
| Infer citations from raw sources | More complete in theory, but out of scope and risks uncited claims. | |

**User's choice:** Non-interactive fallback selected merged explicit/fallback citation evidence.
**Notes:** Outputs must distinguish explicit citations from weaker page-level source refs.

---

## Validation And Data Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Validate before non-dry-run writes | Matches Phase 26 and prevents stale/broken object exports. | ✓ |
| Best-effort export despite validation errors | More permissive, but unsafe for durable agent context. | |
| Always rebuild upstream graph/views | Convenient but violates explicit command boundaries. | |

**User's choice:** Non-interactive fallback selected pre-write validation and no hidden upstream rebuilds.
**Notes:** Missing optional graph/views/citations should degrade gracefully; malformed required artifacts should return structured errors.

---

## the agent's Discretion

- Exact module/package names.
- Exact schema field ordering and default budget values.
- Exact relatedness scoring weights, provided signal-level explanations are present.
- Whether context pack JSON has an optional Markdown companion.

## Deferred Ideas

- Vector embeddings and semantic retrieval.
- Chat-first RAG UI.
- Provider-backed context selection or summarization.
- Phase 28 maintenance integration for personal wiki artifacts.
- Hosted publishing and direct IDE/plugin installation helpers.
