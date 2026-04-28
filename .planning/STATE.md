# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** Agents can maintain and improve a local Markdown wiki through deterministic, auditable command outputs without repeatedly interrupting the user.
**Current focus:** Phase 8 planning: low-interruption agent task workflow runner.

## Current Position

Phase: 8 of 8 (Agent Task Workflow Runner)
Plan: 0 of 1 in current phase
Status: Added and ready to plan
Last activity: 2026-04-28 - Added Phase 8 agent task workflow runner.

Progress: ████████░░ 88%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 1 session
- Total execution time: 7 sessions

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Graph Agent Task Queue | 1/1 | 1 session | 1 session |
| 2. Agent Task Reader | 1/1 | 1 session | 1 session |
| 3. Scoped Patch Proposal | 1/1 | 1 session | 1 session |
| 4. Agent Task Lifecycle | 1/1 | 1 session | 1 session |
| 5. Graph Relevance Scoring | 1/1 | 1 session | 1 session |
| 6. Purpose-Aware Proposals | 1/1 | 1 session | 1 session |
| 7. Patch Apply And Rollback Contract | 1/1 | 1 session | 1 session |
| 8. Agent Task Workflow Runner | 0/1 | Not started | - |

**Recent Trend:**
- Last 5 plans: 03-01, 04-01, 05-01, 06-01, 07-01
- Trend: Stable

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 1]: Use artifact-first task queue, not embedded LLM execution.
- [Phase 1]: Preserve V1 no-content-edit safety boundary.
- [Phase 1]: Dry-run returns task queue preview but writes no task artifact.
- [Phase 2]: Default task reading is read-only; `--refresh` is the explicit write-producing path.
- [Phase 2]: Missing task queue and missing task id return structured exit-code-2 errors.
- [Planning]: Borrow `llm_wiki` product ideas, not GPLv3 implementation code.
- [Planning]: Execute proposal before lifecycle so task states have meaningful artifacts to point to.
- [Planning]: Keep relevance scoring advisory before it affects automation.
- [Phase 3]: `wikify propose` is read-only with respect to content pages and task status.
- [Phase 3]: Proposal paths must pass task `write_scope` validation before artifact write.
- [Phase 3]: `--dry-run` returns proposal JSON without writing `graph-patch-proposals`.
- [Phase 4]: Default `wikify tasks` remains read-only; lifecycle writes require explicit action flags.
- [Phase 4]: Lifecycle state changes append `graph-agent-task-events.json`.
- [Phase 4]: Invalid lifecycle transitions return structured exit-code-2 errors.
- [Phase 5]: Relevance scoring is stdlib-only and advisory.
- [Phase 5]: Relevance signals are direct links, source overlap, common neighbors, and type affinity.
- [Phase 5]: Low-confidence relevance remains informational and does not escalate task priority.
- [Phase 6]: Purpose context is optional and prefers `purpose.md` over `wikify-purpose.md`.
- [Phase 6]: Purpose context enriches proposal rationale only; write-scope validation remains independent.
- [Phase 7]: Patch content must arrive as an explicit agent-generated patch bundle.
- [Phase 7]: Apply supports deterministic `replace_text` only, with exact-once source matching and one operation per path.
- [Phase 7]: Rollback is hash-guarded and refuses drifted content.

### Pending Todos

- Plan and execute Phase 8 agent task workflow runner.

### Blockers/Concerns

- `gsd-sdk` is not available in PATH; GSD files are maintained manually in this session.
- Task lifecycle remains separate from content mutation; apply/rollback handles content changes and lifecycle commands handle task status.

### Roadmap Evolution

- Phase 7 added: Patch Apply And Rollback Contract.
- Phase 8 added: Agent Task Workflow Runner.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Agent execution | Built-in LLM task consumer | Deferred | Phase 1 planning |
| Content generation | Provider-backed semantic patch generation | Deferred | Phase 7 completion |
| UI | Desktop/Tauri parity with `llm_wiki` | Out of scope | llm_wiki reference planning |

## Session Continuity

Last session: 2026-04-28
Stopped at: Phase 8 added and ready to plan.
Resume file: None
