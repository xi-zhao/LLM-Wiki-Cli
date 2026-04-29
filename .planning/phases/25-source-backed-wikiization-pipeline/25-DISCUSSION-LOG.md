# Phase 25: Source-Backed Wikiization Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 25-source-backed-wikiization-pipeline
**Areas discussed:** Command boundary, queue lifecycle, output layout, object/front matter contract, source traceability, deterministic baseline generation, external agent handoff, user edit protection, review/task artifacts, validation and atomicity

---

## Context Capture Mode

The user asked to continue from Phase 24 with low interruption. Project config has `workflow.text_mode: true`, and prior product direction favors autonomous agent work with limited user interruption. The agent therefore captured recommended default decisions inline instead of presenting interactive question lists.

## Command Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| `wikify wikiize` | Dedicated v0.2 queue-to-wiki command aligned with Phase 23 `wikiize_source_item` queue action. | yes |
| Reuse `wikify ingest` | Lower command count but mixes legacy direct ingest with v0.2 queue consumption. | no |
| Hidden processing inside `sync` | Fewer commands but violates Phase 23 no-wikiization boundary. | no |

**User's choice:** Auto-selected recommended default based on prior decisions.
**Notes:** Keep sync, legacy ingest, and v0.2 queue consumption separate.

---

## Queue Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Update queue entries with lifecycle status | Lets agents inspect completed, failed, and needs-review item state. | yes |
| Remove completed entries immediately | Keeps queue small but loses status evidence. | no |
| Append-only queue events only | More audit detail but heavier than current-state JSON patterns. | no |

**User's choice:** Auto-selected recommended default.
**Notes:** Also write a run report so agents do not need to diff queue state.

---

## Output Layout

| Option | Description | Selected |
|--------|-------------|----------|
| `wiki/pages/` plus `artifacts/objects/wiki_pages/` | Visible generated pages and machine objects, separate from legacy sample layouts. | yes |
| Existing `articles/parsed` / `topics` paths | More legacy-compatible but confuses v0.2 generated object boundaries. | no |
| Only JSON objects | Agent-friendly but not human-facing enough for product direction. | no |

**User's choice:** Auto-selected recommended default.
**Notes:** Phase 26 handles source/topic/home/static views.

---

## Deterministic Generation

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative local text importer | Works offline and keeps claims tied to source refs. | yes |
| Require external agent for all pages | More semantic output but blocks baseline product loop. | no |
| Generate rich inferred entities immediately | Too much semantic scope for Phase 25. | no |

**User's choice:** Auto-selected recommended default.
**Notes:** Baseline must work without provider credentials.

---

## External Agent Handoff

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit request/result artifacts and command/profile flags | Matches existing safe automation patterns. | yes |
| Hidden provider calls | Violates product boundary and user preference. | no |
| No agent path at all | Would underserve semantic enrichment requirement WIK-05. | no |

**User's choice:** Auto-selected recommended default.
**Notes:** Wikify remains responsible for validation and final writes.

---

## User Edit Protection

| Option | Description | Selected |
|--------|-------------|----------|
| Hash/fingerprint guard before overwrite | Allows safe generated updates while protecting edits. | yes |
| Never update existing generated pages | Very safe but breaks incremental wikiization. | no |
| Always overwrite generated target | Unsafe for user-edited content. | no |

**User's choice:** Auto-selected recommended default.
**Notes:** Unknown drift creates review/task work rather than overwrite.

---

## Review And Task Artifacts

| Option | Description | Selected |
|--------|-------------|----------|
| New wikiization task queue under `.wikify/queues/` | Specific to source-backed page generation and avoids graph-task overload. | yes |
| Reuse `sorted/graph-agent-tasks.json` | Existing pattern but graph-specific semantics are wrong for wikiization. | no |
| Only per-run warnings | Too weak for agent follow-up. | no |

**User's choice:** Auto-selected recommended default.
**Notes:** Phase 28 can integrate wikiization tasks with broader maintenance.

---

## the agent's Discretion

- Exact module names and internal helper decomposition.
- Exact deterministic summary/excerpt heuristics.
- Exact selector flag set beyond dry-run and one focused item selector.
- Exact report schema names.
- Whether citation objects are implemented in Phase 25 or deferred.

## Deferred Ideas

- Human views and static HTML: Phase 26.
- Agent exports and context packs: Phase 27.
- Maintenance repair integration: Phase 28.
- Provider SDKs and hidden model runtimes: future provider-runtime work, not Phase 25.
