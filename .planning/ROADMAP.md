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
- [x] **Phase 9: Patch Bundle Request Contract** - Generate stable request artifacts that external agents can turn into deterministic patch bundles.
- [x] **Phase 10: Runner Bundle Request Handoff** - Let `run-task` automatically prepare the external-agent bundle request when a bundle is missing.
- [x] **Phase 11: External Patch Bundle Producer** - Invoke explicit external agent commands to produce and preflight patch bundles from request artifacts.
- [x] **Phase 12: Run Task Inline Producer Automation** - Let `run-task` explicitly invoke an external producer command and finish the task in one low-interruption flow.
- [x] **Phase 13: Batch Task Automation** - Process bounded batches of graph agent tasks through the audited task runner with structured per-task results.

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
- [x] 09-01: Build patch bundle request contract

### Phase 10: Runner Bundle Request Handoff
**Goal**: `wikify run-task --id <id>` automatically writes or previews the patch bundle request artifact when no patch bundle exists, so normal automation has one fewer manual orchestration step.
**Depends on**: Phase 9
**Requirements**: HND-01, HND-02, HND-03, HND-04, HND-05
**Why after Phase 9**: The request artifact contract is stable. The runner can now compose it safely without generating semantic content.
**Success Criteria** (what must be TRUE):
  1. Missing bundle in non-dry-run writes `sorted/graph-patch-bundle-requests/<task-id>.json`.
  2. Missing bundle in dry-run reports the request path but writes no request/proposal/lifecycle/content/application artifacts.
  3. `run-task` results expose request and suggested bundle paths.
  4. Existing bundle flow still applies patch and marks task done.
  5. Request-generation failures surface as structured `bundle_request_*` errors with `phase: bundle_request`.
  6. Docs describe `run-task` as the preferred automation entrypoint and `bundle-request` as explicit refresh/manual handoff.
  7. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 10-01: Build runner bundle request handoff

### Phase 11: External Patch Bundle Producer
**Goal**: `wikify produce-bundle --request-path <path> --agent-command <command>` invokes an explicit external agent command, writes the resulting patch bundle, and validates it with deterministic preflight.
**Depends on**: Phase 10
**Requirements**: EBP-01, EBP-02, EBP-03, EBP-04, EBP-05, EBP-06, EBP-07
**Why after Phase 10**: The runner now creates request artifacts automatically. This phase adds the explicit bridge from request artifact to generated bundle without hard-coding any provider.
**Success Criteria** (what must be TRUE):
  1. A command can produce a bundle from a request via stdin/stdout/env contract.
  2. The produced bundle is written to `suggested_bundle_path`.
  3. A command that writes the bundle file itself is accepted.
  4. Produced bundles pass deterministic apply preflight before success.
  5. Dry-run reports the invocation contract without executing the command.
  6. Structured errors cover missing request, failed command, timeout, invalid output, and invalid bundle.
  7. Docs describe the external command contract and explicit-provider boundary.
  8. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 11-01: Build external patch bundle producer

### Phase 12: Run Task Inline Producer Automation
**Goal**: `wikify run-task --id <id> --agent-command <command>` composes proposal, bundle request, explicit external bundle production, deterministic apply, and lifecycle completion in one command.
**Depends on**: Phase 11
**Requirements**: RTP-01, RTP-02, RTP-03, RTP-04, RTP-05, RTP-06, RTP-07
**Why after Phase 11**: The producer contract is now explicit and preflighted. The runner can safely compose it when the caller provides a command, reducing external orchestration without adding hidden provider defaults.
**Success Criteria** (what must be TRUE):
  1. Missing bundle plus `--agent-command` produces a bundle and continues to apply in the same run.
  2. Existing bundle flow still applies without executing the producer command.
  3. Dry-run with `--agent-command` reports the would-produce step without executing or writing.
  4. Producer errors surface through `run-task` with `phase: bundle_producer`.
  5. No hidden provider/key/retry behavior is introduced.
  6. Docs describe one-command automation and the explicit command boundary.
  7. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 12-01: Build run-task inline producer automation

### Phase 13: Batch Task Automation
**Goal**: `wikify run-tasks` selects a bounded set of graph agent tasks and executes them sequentially through the existing audited runner, returning stable per-task results.
**Depends on**: Phase 12
**Requirements**: BTA-01, BTA-02, BTA-03, BTA-04, BTA-05, BTA-06, BTA-07, BTA-08
**Why after Phase 12**: Single-task automation is now explicit and safe. Batch automation should compose that primitive with bounded defaults instead of introducing concurrency, hidden provider behavior, or new apply semantics.
**Success Criteria** (what must be TRUE):
  1. Batch selection supports status, action, id, and limit.
  2. Defaults are conservative: queued tasks, limit 5, sequential execution, stop on first failure.
  3. Each selected task uses the existing `run_agent_task` flow.
  4. Dry-run remains zero-write across the whole batch.
  5. Per-task outcomes include success, waiting, and structured failure entries.
  6. `--continue-on-error` allows later tasks to continue after a failure.
  7. Docs describe bounded automation and the explicit command boundary.
  8. Full unittest suite passes.
**Plans**: 1 plan

Plans:
- [x] 13-01: Build bounded batch task automation

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
| 9. Patch Bundle Request Contract | 1/1 | Complete | 2026-04-28 |
| 10. Runner Bundle Request Handoff | 1/1 | Complete | 2026-04-28 |
| 11. External Patch Bundle Producer | 1/1 | Complete | 2026-04-28 |
| 12. Run Task Inline Producer Automation | 1/1 | Complete | 2026-04-28 |
| 13. Batch Task Automation | 1/1 | Complete | 2026-04-28 |
