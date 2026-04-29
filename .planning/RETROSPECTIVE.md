# Retrospective: Wikify

## Milestone: v0.1.0a2 - Agentic Maintenance Automation

**Shipped:** 2026-04-29
**Phases:** 21 | **Plans:** 21

### What Was Built

Wikify gained a complete explicit-agent maintenance loop: graph findings become scoped tasks; tasks produce proposals, bundle requests, deterministic patch bundles, verifier decisions, lifecycle events, and repair feedback. The loop can run one task, batches, maintenance refreshes, and bounded repeated rounds without hidden provider execution.

### What Worked

- Keeping external agents behind explicit command/profile flags made automation powerful without hiding provider behavior.
- Deterministic patch bundles plus hash-guarded rollback kept content mutation auditable.
- Verifier rejection feedback turned failures into durable repair context instead of one-off errors.
- GSD phase discipline kept many small features coherent across 21 phases.

### What Was Inefficient

- `gsd-sdk` was unavailable, so roadmap/state/audit files were maintained manually.
- Standalone phase verification artifacts were added retroactively instead of during each phase.
- Many docs updates were repeated across README variants and protocol docs.

### Patterns Established

- Explicit producer/verifier command boundary.
- Bounded automation defaults: sequential execution, conservative limits, stop-on-error.
- Artifact-first workflow: every semantic step produces inspectable JSON or Markdown evidence.
- Repair loops feed verifier feedback back into the producer request.

### Key Lessons

- Low-interruption automation needs durable machine-readable feedback more than prompts.
- A verifier gate is only truly useful once its rejection can be repaired automatically.
- Milestone closure should create verification artifacts as part of each phase, not after the fact.

### Cost Observations

- Runtime: Codex inline execution with manual GSD file maintenance.
- Sessions: One intensive milestone execution cycle.
- Notable: Manual GSD operation was workable but should be replaced by a functioning `gsd-sdk` path for long-term use.

## Cross-Milestone Trends

| Milestone | Smoothest Pattern | Friction | Follow-up |
|-----------|-------------------|----------|-----------|
| v0.1.0a2 | Explicit artifact contracts | Missing `gsd-sdk` and retroactive verification | Restore SDK workflow or keep a lightweight local helper |
