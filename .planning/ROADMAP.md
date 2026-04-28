# Roadmap: Wikify

## Overview

The current milestone turns graph maintenance from "audit artifacts exist" into "agents can safely drive the next maintenance action." Phase 1 created an agent task queue. Phase 2 exposed a read-only task API. The sequence then added scoped proposals, lifecycle state, graph relevance, and purpose-aware proposal rationale.

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

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Graph Agent Task Queue | 1/1 | Complete | 2026-04-28 |
| 2. Agent Task Reader | 1/1 | Complete | 2026-04-28 |
| 3. Scoped Patch Proposal | 1/1 | Complete | 2026-04-28 |
| 4. Agent Task Lifecycle | 1/1 | Complete | 2026-04-28 |
| 5. Graph Relevance Scoring | 1/1 | Complete | 2026-04-28 |
| 6. Purpose-Aware Proposals | 1/1 | Complete | 2026-04-28 |
