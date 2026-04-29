# Phase 28: Maintenance Integration And Compatibility - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 28-maintenance-integration-and-compatibility
**Areas discussed:** Compatibility anchor, target model, finding sources, task queue metadata, repair safety, E2E verification

---

## Compatibility Anchor

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing graph maintenance commands | Preserves v0.1.0a2 command compatibility while making the loop object-aware. | yes |
| Introduce a new maintenance namespace | Cleaner naming, but creates migration work before the object-aware behavior is proven. | |
| Rewrite maintenance around v0.2 only | Simpler new model, but breaks the existing automation surface. | |

**User's choice:** Non-interactive fallback selected compatibility-first extension.
**Notes:** The user previously requested low-interruption automation and strong architecture; this choice minimizes churn while improving the product object.

---

## Target Model

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral target resolver over existing artifacts | Maps graph subjects to object ids, page paths, view paths, source refs, and agent artifacts without creating another store. | yes |
| Persistent maintenance target database | Faster repeated lookup in theory, but adds a second source of truth too early. | |
| Path-only targeting | Fully compatible, but cannot express personal wiki pages, views, or agent exports cleanly. | |

**User's choice:** Non-interactive fallback selected an ephemeral v0.2 target resolver.
**Notes:** The same object/source/control artifacts must feed human views, agent interfaces, and maintenance.

---

## Finding Sources

| Option | Description | Selected |
|--------|-------------|----------|
| Graph findings plus v0.2 artifact health | Keeps Graphify-style graph intelligence and adds object/view/agent maintenance targets. | yes |
| Graph-only findings | Stable but too narrow for Phase 28 requirements. | |
| Raw-source reanalysis during maintenance | More coverage, but violates explicit pipeline boundaries and risks hidden expensive work. | |

**User's choice:** Non-interactive fallback selected graph plus v0.2 artifact health.
**Notes:** Object validation records, view tasks, wikiization tasks, and agent export state can produce findings.

---

## Task Queue Metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Add optional typed metadata to existing task schema | Keeps legacy fields stable while exposing object/view/agent semantics to new agents. | yes |
| Change task schema version and require new consumers | Cleaner contract, but unnecessary compatibility risk. | |
| Store v0.2 details only in evidence blobs | Minimal schema changes, but hard for agents to query reliably. | |

**User's choice:** Non-interactive fallback selected optional additive metadata.
**Notes:** Existing fields such as `target`, `write_scope`, and `action` remain stable.

---

## Repair Safety

| Option | Description | Selected |
|--------|-------------|----------|
| Add deterministic preservation checks for generated pages | Enforces `source_refs` and `review_status` preservation independent of external verifier quality. | yes |
| Rely only on external verifier prompts | Flexible, but too weak for the Phase 28 trust requirement. | |
| Forbid generated page repairs entirely | Safe, but blocks meaningful maintenance of the generated wiki. | |

**User's choice:** Non-interactive fallback selected deterministic preservation checks.
**Notes:** External verifiers remain useful, but local checks should reject metadata loss.

---

## Derived Artifact Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Prefer regeneration tasks for views and agent exports | Prevents patching stale derived outputs and keeps source of truth clean. | yes |
| Patch generated views and agent exports directly | Sometimes faster, but risks divergence from object/source artifacts. | |
| Silently regenerate inside `maintain` | Convenient, but violates explicit command boundaries. | |

**User's choice:** Non-interactive fallback selected explicit regeneration tasks.
**Notes:** `maintain` should surface work; `wikify views` and `wikify agent export` own derived artifact generation.

---

## E2E Verification

| Option | Description | Selected |
|--------|-------------|----------|
| Integration-style local workflow fixture | Verifies the real product loop from source registration to maintenance task. | yes |
| Unit tests only | Faster, but misses cross-phase breakage. | |
| Real external model verifier | Closer to production, but non-deterministic and not suitable for unit tests. | |

**User's choice:** Non-interactive fallback selected a deterministic local integration fixture.
**Notes:** The fixture should use local sample scripts for agent/verifier behavior when needed.

---

## the agent's Discretion

- Exact helper module names and organization.
- Exact optional metadata field order.
- Exact warning/finding codes.
- Whether the implementation lands in one plan or several dependent plans.

## Deferred Ideas

- Renaming legacy graph maintenance artifacts.
- A new maintenance command namespace.
- Built-in provider-backed repair generation.
- Vector/embedding prioritization.
- Raw source reread during maintenance.
