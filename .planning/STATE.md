# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** Agents can maintain and improve a local Markdown wiki through deterministic, auditable command outputs without repeatedly interrupting the user.
**Current focus:** Phase 13 planning: bounded batch task automation.

## Current Position

Phase: 13 of 13 (Batch Task Automation)
Plan: 1 of 1 in current phase
Status: Planning
Last activity: 2026-04-28 - Added Phase 13 bounded batch task automation.

Progress: █████████░ 92%

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: 1 session
- Total execution time: 12 sessions

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
| 8. Agent Task Workflow Runner | 1/1 | 1 session | 1 session |
| 9. Patch Bundle Request Contract | 1/1 | 1 session | 1 session |
| 10. Runner Bundle Request Handoff | 1/1 | 1 session | 1 session |
| 11. External Patch Bundle Producer | 1/1 | 1 session | 1 session |
| 12. Run Task Inline Producer Automation | 1/1 | 1 session | 1 session |
| 13. Batch Task Automation | 0/1 | In progress | TBD |

**Recent Trend:**
- Last 5 plans: 08-01, 09-01, 10-01, 11-01, 12-01
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
- [Phase 8]: `run-task` composes audited primitives and stops at `waiting_for_patch_bundle` when semantic patch content is missing.
- [Phase 8]: Successful run-task apply marks tasks done through lifecycle events.
- [Planning]: Generate patch bundle requests as explicit handoff artifacts before any provider-backed consumer work.
- [Phase 9]: `bundle-request` packages target snapshots, hashes, proposal context, and bundle schema instructions for external agents.
- [Phase 9]: Bundle request generation does not mutate content pages or lifecycle state.
- [Planning]: `run-task` should prepare the request handoff automatically when bundle content is missing.
- [Phase 10]: `run-task` writes a patch bundle request artifact automatically when it reaches `waiting_for_patch_bundle`.
- [Phase 10]: `run-task --dry-run` reports request paths but remains zero-write.
- [Planning]: Use an explicit external command adapter before any provider-specific SDK integration.
- [Phase 11]: `produce-bundle` uses an explicit external command adapter, not hidden provider execution.
- [Phase 11]: Produced bundles are preflighted before success and do not mutate content.
- [Planning]: `run-task --agent-command` should compose producer automation only when the command is explicit.
- [Phase 12]: `run-task --agent-command` composes request, external production, deterministic apply, and mark-done in one command.
- [Phase 12]: Existing bundles and dry-run paths do not execute the producer command.
- [Planning]: Batch task automation should use bounded sequential execution before any concurrent execution.

### Pending Todos

- Execute Phase 13: Build bounded batch task automation.

### Blockers/Concerns

- `gsd-sdk` is not available in PATH; GSD files are maintained manually in this session.
- Task lifecycle remains separate from content mutation; apply/rollback handles content changes and lifecycle commands handle task status.

### Roadmap Evolution

- Phase 7 added: Patch Apply And Rollback Contract.
- Phase 8 added: Agent Task Workflow Runner.
- Phase 9 added: Patch Bundle Request Contract.
- Phase 10 added: Runner Bundle Request Handoff.
- Phase 11 added: External Patch Bundle Producer.
- Phase 11 completed: External Patch Bundle Producer.
- Phase 12 added: Run Task Inline Producer Automation.
- Phase 12 completed: Run Task Inline Producer Automation.
- Phase 13 added: Batch Task Automation.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Agent execution | Built-in LLM task consumer | Deferred | Phase 1 planning |
| Content generation | Provider-backed semantic patch generation | Deferred | Phase 7 completion |
| UI | Desktop/Tauri parity with `llm_wiki` | Out of scope | llm_wiki reference planning |

## Session Continuity

Last session: 2026-04-28
Stopped at: Phase 13 planning.
Resume file: None
