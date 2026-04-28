# Roadmap: Wikify

## Overview

The current milestone turns graph maintenance from "audit artifacts exist" into "agents have a deterministic task queue they can consume without asking the user." Future milestones can add agent consumers and safe patch execution after this artifact contract is stable.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions marked with INSERTED

- [x] **Phase 1: Graph Agent Task Queue** - Convert queued graph maintenance steps into an agent-consumable task artifact.

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

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Graph Agent Task Queue | 1/1 | Complete | 2026-04-28 |
