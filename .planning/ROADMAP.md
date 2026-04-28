# Roadmap: Wikify

## Overview

The current milestone turns graph maintenance from "audit artifacts exist" into "agents have a deterministic task queue they can consume without asking the user." Phase 2 adds the read API for that queue; future milestones can add safe patch proposal and execution.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions marked with INSERTED

- [x] **Phase 1: Graph Agent Task Queue** - Convert queued graph maintenance steps into an agent-consumable task artifact.
- [ ] **Phase 2: Agent Task Reader** - Add a stable CLI entrypoint for listing and inspecting queued graph agent tasks.

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
- [ ] 02-01: Build agent task reader command

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Graph Agent Task Queue | 1/1 | Complete | 2026-04-28 |
| 2. Agent Task Reader | 0/1 | Not started | - |
