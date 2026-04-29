# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-29)

**Core value:** Users can turn scattered personal and project knowledge into a living local wiki that people can browse and agents can reliably call.
**Current focus:** v0.2.0 Personal Wiki Core & Views, Phase 26 human wiki views and local static output.

## Current Position

Milestone: v0.2.0 Personal Wiki Core & Views
Phase: 26 - Human Wiki Views And Local Static Output
Status: Context captured
Last activity: 2026-04-29 - Captured Phase 26 context for `wikify views`, human Markdown views, local static HTML, object-artifact source of truth, graph/timeline entry points, and view edit protection.

Progress: ██████░░░░ 57%

## Performance Metrics

**Velocity:**
- Total plans completed: 25
- Average duration: 1 session
- Total execution time: 25 sessions

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
| 13. Batch Task Automation | 1/1 | 1 session | 1 session |
| 14. Maintenance Run Automation | 1/1 | 1 session | 1 session |
| 15. Agent Profile Configuration | 1/1 | 1 session | 1 session |
| 16. Explicit Default Agent Profile | 1/1 | 1 session | 1 session |
| 17. Maintenance Loop Automation | 1/1 | 1 session | 1 session |
| 18. Agent Verifier Gate | 1/1 | 1 session | 1 session |
| 19. Verifier Rejection Feedback | 1/1 | 1 session | 1 session |
| 20. Verifier Repair Automation | 1/1 | 1 session | 1 session |
| 21. Milestone Verification Artifacts | 1/1 | 1 session | 1 session |
| 22. Personal Wiki Workspace And Source Registry | 1/1 | 1 session | 1 session |
| 23. Incremental Sync And Ingest Queue | 1/1 | 1 session | 1 session |
| 24. Wiki Object Model And Validation | 1/1 | 1 session | 1 session |
| 25. Source-Backed Wikiization Pipeline | 1/1 | 1 session | 1 session |

**Recent Trend:**
- Last 5 plans: 21-01, 22-01, 23-01, 24-01, 25-01
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
- [Phase 13]: `run-tasks` composes existing single-task runner results and returns per-task outcomes.
- [Phase 13]: Batch defaults are queued status, limit 5, sequential execution, and stop-on-error.
- [Planning]: Maintenance run automation should compose `maintain` and `run-tasks` without introducing hidden provider execution.
- [Phase 14]: `maintain-run` refreshes maintenance artifacts before selecting tasks and uses the bounded batch runner.
- [Phase 14]: Dry-run previews from the fresh in-memory maintenance task queue instead of stale on-disk queues.
- [Planning]: Agent profile configuration should reduce repeated command entry without hiding provider behavior.
- [Phase 15]: `agent-profile` stores visible project-level external command aliases in `wikify-agent-profiles.json`.
- [Phase 15]: `--agent-profile` is explicit and mutually exclusive with `--agent-command`.
- [Planning]: Default agent profiles must remain explicit shorthand; a default alone must not trigger external execution.
- [Phase 16]: Bare `--agent-profile` resolves `default_profile`, but commands without `--agent-profile` remain non-producing.
- [Phase 16]: Removing the current default profile clears the `default_profile` pointer.
- [Planning]: Maintenance loop automation should compose `maintain-run`, not introduce new patch or provider semantics.
- [Phase 17]: `maintain-loop` repeats `maintain-run` with conservative max rounds and task budget bounds.
- [Phase 17]: Dry-run previews one round only because repeated dry-runs would replay the same in-memory queue.
- [Planning]: Agent verifier gate should run after deterministic preflight and before apply, with no hidden provider behavior.
- [Phase 18]: Verifier rejection writes an audit artifact and blocks apply before content mutation.
- [Phase 18]: `--verifier-profile` reuses explicit project profiles but does not run unless the flag is present.
- [Planning]: Verifier rejection should block tasks with durable feedback so later agents can inspect and retry.
- [Phase 19]: Verifier rejection in `run-task` marks tasks blocked with `blocked_feedback`.
- [Phase 19]: Retry and restore clear stale verifier rejection feedback before the next attempt.
- [Planning]: Repair automation should reuse explicit producer/verifier command boundaries before any provider-backed SDK work.
- [Phase 20]: Bundle requests include `repair_context` from verifier rejection feedback.
- [Phase 20]: Explicit repair runs regenerate rejected default bundles before verifier/apply.
- [Milestone Audit]: Product requirements are satisfied, and v0.1.0a1 can be archived after Phase 21's standalone verification artifacts.
- [Phase 21]: Standalone verification artifacts close the milestone audit gap without changing product code.
- [Phase 22]: `source add` is shallow registration only; sync, wikiization, views, graph, and agent exports remain explicit later commands.
- [Phase 22]: Source identity uses opaque `src_` ids with duplicate detection through canonical `locator_key`.
- [Phase 23]: `wikify sync` discovers and classifies registered source items, but does not run ingest, fetch URLs, clone repositories, generate wiki pages, or call providers.
- [Phase 23]: Source items use deterministic ids derived from source id and item locator so repeated syncs can detect unchanged items.
- [Phase 23]: Sync writes current-state JSON artifacts under `.wikify/sync/` and `.wikify/queues/`, keeping human wiki directories separate from control-plane state.
- [Phase 23]: Only `new` and `changed` source items create active ingest queue entries; `missing`, `skipped`, and `errored` stay as status evidence.
- [Phase 24]: Object contracts are stdlib-only dictionaries/helpers and explicit schemas, not Pydantic, JSON Schema, YAML dependencies, or a database.
- [Phase 24]: Markdown front matter is a readable metadata bridge using a bounded scalar plus JSON-flow subset.
- [Phase 24]: Validation is compatibility-tolerant by default and strict for declared v0.2 object gaps.
- [Phase 24]: `wikify graph` keeps path-based ids and exposes canonical object ids as additive metadata.
- [Phase 24]: `artifacts/objects/` is the visible product artifact root for object JSON and validation reports.
- [Phase 25]: `wikify wikiize` is the explicit queue-to-wiki command; legacy `wikify ingest` remains separate.
- [Phase 25]: Local text/Markdown source items use deterministic source-backed generation without provider credentials.
- [Phase 25]: Remote-without-content and unsupported items create wikiization tasks instead of fake pages.
- [Phase 25]: Generated page updates are hash-guarded and preserve user-edited drift for review.
- [Phase 25]: External semantic enrichment uses visible request/result artifacts and explicit agent command/profile flags.
- [Phase 26]: `wikify views` should be the explicit human-view generation command, producing Markdown views and local static HTML without running sync, wikiize, graph, providers, or agents implicitly.
- [Phase 26]: Human views must render from `artifacts/objects/` plus source, queue, validation, and optional graph artifacts, not from a separate human-only knowledge store.
- [Phase 26]: Generated view Markdown should be hash-guarded through `.wikify/views/view-manifest.json`; missing optional data should produce honest empty states and next actions.

### Pending Todos

- None.

### Blockers/Concerns

- `gsd-sdk` is not available in PATH; GSD files are maintained manually in this session.
- Task lifecycle remains separate from content mutation; apply/rollback handles content changes and lifecycle commands handle task status.
- v0.2.0 changes product scope from project-only wiki maintenance to a personal knowledge base with shared human and agent views.

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
- Phase 13 completed: Batch Task Automation.
- Phase 14 added: Maintenance Run Automation.
- Phase 14 completed: Maintenance Run Automation.
- Phase 15 added: Agent Profile Configuration.
- Phase 15 completed: Agent Profile Configuration.
- Phase 16 added: Explicit Default Agent Profile.
- Phase 16 completed: Explicit Default Agent Profile.
- Phase 17 added: Maintenance Loop Automation.
- Phase 17 completed: Maintenance Loop Automation.
- Phase 18 added: Agent Verifier Gate.
- Phase 18 completed: Agent Verifier Gate.
- Phase 19 added: Verifier Rejection Feedback.
- Phase 19 completed: Verifier Rejection Feedback.
- Phase 20 added: Verifier Repair Automation.
- Phase 20 completed: Verifier Repair Automation.
- Milestone audit completed: v0.1.0a1 has a GSD process gap for missing phase verification artifacts.
- Phase 21 added: Milestone Verification Artifacts.
- Phase 21 completed: Milestone Verification Artifacts.
- Milestone v0.2.0 started: Personal Wiki Core & Views.
- Phase 22 context captured: workspace manifest, source identity, registration scope, CLI shape, and registry artifact decisions.
- Phase 22 planned: 1 plan covering workspace initialization, source registry module, CLI commands, docs, and verification.
- Phase 22 completed: workspace manifest, source registry module, CLI commands, docs, and verification shipped.
- Phase 23 context captured: sync command boundary, source item model, freshness classification, artifact paths, queue semantics, and registry sync metadata.
- Phase 23 planned: 1 TDD plan covering sync module tests, sync implementation, CLI wiring, docs, GSD updates, and verification.
- Phase 23 completed: `wikify sync`, deterministic source item index, sync report, ingest queue, dry-run, source selection, docs, and verification shipped.
- Phase 24 context captured: object schema set, object identity, JSON/front matter contract, validation command, source/citation references, graph edge compatibility, and deferred scope.
- Phase 24 planned: 1 TDD plan covering object schemas, front matter parser, object validation, graph object-id metadata bridge, `wikify validate`, docs, and verification.
- Phase 24 completed: canonical object schemas, front matter parser, object validation, graph object-id metadata bridge, `wikify validate`, docs, and verification artifacts shipped.
- Phase 25 context captured: queue-to-wiki command boundary, generated page/object layout, source refs, deterministic baseline generation, explicit agent enrichment handoff, edit protection, review tasks, and validation gates.
- Phase 25 planned: 1 TDD plan covering `wikify wikiize`, queue consumption, generated Markdown/object artifacts, source traceability, edit protection, wikiization tasks, explicit agent handoff, docs, and verification.
- Phase 25 completed: `wikify wikiize`, deterministic local wikiization, generated `wiki/pages/` Markdown, `wikify.wiki-page.v1` objects, object index updates, strict validation gate, edit protection, wikiization task queue, explicit agent handoff, docs, and verification shipped.
- Phase 26 context captured: `wikify views` command boundary, object-artifact source of truth, human Markdown view set, static HTML output, graph/timeline entry views, missing-data behavior, and view hash guards.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Agent execution | Built-in LLM task consumer | Deferred | Phase 1 planning |
| Content generation | Provider-backed semantic patch generation | Deferred | Phase 7 completion |
| UI | Desktop/Tauri parity with `llm_wiki` | Out of scope | llm_wiki reference planning |

## Session Continuity

Last session: 2026-04-29
Stopped at: Phase 26 context gathered.
Resume file: .planning/phases/26-human-wiki-views-and-local-static-output/26-CONTEXT.md
Next command: `$gsd-plan-phase 26`
