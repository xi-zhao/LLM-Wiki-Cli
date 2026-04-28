# Roadmap: Wikify

## Overview

The current milestone turns graph maintenance from "audit artifacts exist" into "agents can safely drive the next maintenance action." Phase 1 created an agent task queue. Phase 2 exposed a read-only task API. The sequence then added scoped proposals, lifecycle state, graph relevance, purpose-aware proposal rationale, deterministic patch bundle apply/rollback, and low-interruption task workflow orchestration.

The roadmap incorporates product lessons from `nashsu/llm_wiki` while preserving Wikify's CLI-first, stdlib-only, MIT-compatible direction.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions marked with INSERTED

- [x] **Phase 1: Graph Agent Task Queue** - Convert queued graph maintenance steps into an agent-consumable task artifact.
- [x] **Phase 2: Agent Task Reader** - Add a stable CLI entrypoint for listing and inspecting queued graph agent tasks.
- [x] **Phase 3: Scoped Patch Proposal** - Let agents generate auditable, scoped patch proposals from one queued task without applying edits.
- [x] **Phase 4: Agent Task Lifecycle** - Add durable task state transitions, retry/cancel/restore, and append-only lifecycle events.
- [x] **Phase 5: Graph Relevance Scoring** - Rank findings and tasks using explainable graph relevance signals.
- [x] **Phase 6: Purpose-Aware Proposals** - Add optional purpose context so proposals align with the wiki's goals.
- [x] **Phase 7: Patch Apply And Rollback Contract** - Apply deterministic agent-generated patch bundles with audit and rollback safety.
- [x] **Phase 8: Agent Task Workflow Runner** - Orchestrate proposal, patch bundle detection, apply, and task lifecycle with minimal user interruption.
- [ ] **Phase 9: Patch Bundle Request Contract** - Generate stable request artifacts that external agents can turn into deterministic patch bundles.

## Phase Details

### Phase 1: Graph Agent Task Queue
**Goal**: `wikify maintain` produces `sorted/graph-agent-tasks.json` and includes task queue summary/path in its result without editing content pages.
**Depends on**: Existing `wikify maintain` graph findings, plan, executor, and runner.
**Requirements**: GMT-01, GMT-02, GMT-03, GMT-04, GMT-05, DOC-01, DOC-02
**Success Criteria** (what must be TRUE):
  1. Agent tasks are generated from queued maintenance plan steps.
  2. Dry-run returns task previews but writes no task queue artifact.
  3. Normal run writes `sorted/graph-agent-tasks.json`.
  4. Docs describe how a later agent should consume the artifact.
  5. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 01-01: Build graph agent task queue artifact

### Phase 2: Agent Task Reader
**Goal**: `wikify tasks` reads, filters, and returns queued graph agent tasks without mutating content or task state.
**Depends on**: Phase 1
**Requirements**: TSK-01, TSK-02, TSK-03, TSK-04, TSK-05
**Success Criteria** (what must be TRUE):
  1. Agent can list current queued graph tasks through `wikify tasks`.
  2. Agent can inspect one task by id.
  3. Agent can filter by status/action and limit result size.
  4. Missing queue artifacts return a structured error telling the caller to run `wikify maintain`.
  5. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 02-01: Build agent task reader command

### Phase 3: Scoped Patch Proposal
**Goal**: `wikify propose --task-id <id>` reads one queued task, validates its write scope, and writes a patch proposal artifact without applying edits.
**Depends on**: Phase 2
**Requirements**: PRP-01, PRP-02, PRP-03, PRP-04, PRP-05, PRP-06
**Why now**: This is the next safety boundary. It gives an agent something actionable to review and execute later while still preventing silent wiki rewrites.
**Success Criteria** (what must be TRUE):
  1. A proposal can be generated for one existing task id.
  2. The proposal artifact path is `sorted/graph-patch-proposals/<task-id>.json`.
  3. Every proposed path is inside the task `write_scope`.
  4. `--dry-run` returns the proposal but writes no proposal artifact.
  5. Proposal generation does not mutate task status or content files.
  6. Structured errors cover missing queue, missing task, missing write scope, and out-of-scope paths.
  7. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 03-01: Build scoped patch proposal command

### Phase 4: Agent Task Lifecycle
**Goal**: Add explicit task state mutation commands and append-only lifecycle events after proposals exist.
**Depends on**: Phase 3
**Requirements**: LIF-01, LIF-02, LIF-03, LIF-04, LIF-05
**Why after Phase 3**: A `proposed` state is only meaningful once proposal artifacts exist.
**Success Criteria** (what must be TRUE):
  1. Task transitions are validated against a finite state machine.
  2. Retry, cancel, restore, block, reject, and mark-done operations are represented as structured commands.
  3. Every transition appends an audit event.
  4. Read-only `wikify tasks` remains backward compatible.
  5. No lifecycle command rewrites content pages.
**Plans**: 1 plan

Plans:
- [x] 04-01: Build graph agent task lifecycle commands

### Phase 5: Graph Relevance Scoring
**Goal**: Improve maintenance priority by computing direct-link, source-overlap, common-neighbor, and type-affinity relevance signals.
**Depends on**: Phase 4
**Requirements**: REL-01, REL-02, REL-03, REL-04
**Why after lifecycle**: Scoring should improve ordering and task selection once tasks have durable state.
**Success Criteria** (what must be TRUE):
  1. Relevance scores are deterministic and stdlib-only.
  2. Score outputs include signal-level evidence.
  3. Findings/tasks include relevance metadata.
  4. Scores affect priority and explanation only, not automatic writes.
  5. Low-confidence signals remain informational.
**Plans**: 1 plan

Plans:
- [x] 05-01: Build graph relevance scoring

### Phase 6: Purpose-Aware Proposals
**Goal**: Let proposal generation include optional purpose context so edits are meaningful for the wiki's stated goals.
**Depends on**: Phase 5
**Requirements**: PUR-01, PUR-02, PUR-03, PUR-04
**Why last in this sequence**: Purpose context is most useful after proposal and scoring artifacts have stable places to carry rationale.
**Success Criteria** (what must be TRUE):
  1. Wikify can discover optional purpose context.
  2. Missing purpose context is reported but non-blocking.
  3. Proposal rationale includes purpose evidence when present.
  4. Purpose context never weakens path/write safety rules.
**Plans**: 1 plan

Plans:
- [x] 06-01: Build purpose-aware patch proposals

### Phase 7: Patch Apply And Rollback Contract
**Goal**: `wikify apply` can validate and apply deterministic patch bundles generated by an agent, while `wikify rollback` can restore applied changes from audit evidence.
**Depends on**: Phase 6
**Requirements**: APP-01, APP-02, APP-03, APP-04, APP-05, APP-06
**Why after Phase 6**: Proposals now carry task evidence, safety scope, lifecycle context, relevance, and purpose rationale. Apply should consume those artifacts rather than inventing its own intent.
**Success Criteria** (what must be TRUE):
  1. Apply requires both a proposal artifact and a patch bundle artifact.
  2. Patch operations are limited to deterministic text replacement in this phase.
  3. Every operation path is inside proposal `write_scope` and the wiki root.
  4. Dry-run validates without writing content or audit records.
  5. Non-dry-run writes content changes and an application audit record with rollback evidence.
  6. Rollback restores only when current content matches the recorded post-apply hash.
  7. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 07-01: Build deterministic patch apply and rollback

### Phase 8: Agent Task Workflow Runner
**Goal**: `wikify run-task --id <id>` advances one graph agent task through proposal, patch bundle detection, deterministic apply, and lifecycle completion when enough artifacts exist.
**Depends on**: Phase 7
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04, RUN-05, RUN-06, RUN-07
**Why after Phase 7**: The runner can now compose audited primitives instead of inventing patch behavior. It should automate glue, not semantic generation.
**Success Criteria** (what must be TRUE):
  1. Runner returns a stable `wikify.agent-task-run.v1` result for one task id.
  2. Runner creates or reuses a scoped proposal.
  3. Missing patch bundle returns `waiting_for_patch_bundle` and agent-facing next actions.
  4. Existing patch bundle is applied through deterministic apply.
  5. Successful apply marks the task done through lifecycle events.
  6. Dry-run writes no proposals, events, content, or application records.
  7. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 08-01: Build agent task workflow runner

### Phase 9: Patch Bundle Request Contract
**Goal**: `wikify bundle-request --task-id <id>` generates an agent-facing request artifact with proposal context, write scope, target snapshots, hashes, and the allowed patch bundle operation contract.
**Depends on**: Phase 8
**Requirements**: BND-01, BND-02, BND-03, BND-04, BND-05, BND-06
**Why after Phase 8**: The runner can already stop at `waiting_for_patch_bundle`; this phase turns that waiting state into a deterministic handoff for an external agent.
**Success Criteria** (what must be TRUE):
  1. A request can be generated for one existing task id.
  2. The request artifact path is `sorted/graph-patch-bundle-requests/<task-id>.json`.
  3. The request includes proposal/task evidence, target file snapshots, hashes, write scope, and allowed `replace_text` contract.
  4. `--dry-run` returns the request but writes no request or proposal artifacts.
  5. Request generation never mutates content pages or task lifecycle state.
  6. Structured errors cover missing queue, missing task, invalid paths, and missing target files.
  7. Docs describe how an external agent should write `sorted/graph-patch-bundles/<task-id>.json`.
  8. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [ ] 09-01: Build patch bundle request contract

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Graph Agent Task Queue | 1/1 | Complete | 2026-04-28 |
| 2. Agent Task Reader | 1/1 | Complete | 2026-04-28 |
| 3. Scoped Patch Proposal | 1/1 | Complete | 2026-04-28 |
| 4. Agent Task Lifecycle | 1/1 | Complete | 2026-04-28 |
| 5. Graph Relevance Scoring | 1/1 | Complete | 2026-04-28 |
| 6. Purpose-Aware Proposals | 1/1 | Complete | 2026-04-28 |
| 7. Patch Apply And Rollback Contract | 1/1 | Complete | 2026-04-28 |
| 8. Agent Task Workflow Runner | 1/1 | Complete | 2026-04-28 |
| 9. Patch Bundle Request Contract | 0/1 | Planned | |
