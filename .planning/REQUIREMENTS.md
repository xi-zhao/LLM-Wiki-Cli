# Requirements: Wikify

**Defined:** 2026-04-28
**Core Value:** Agents can maintain and improve a local Markdown wiki through deterministic, auditable command outputs without repeatedly interrupting the user.

## v1 Requirements

### Graph Maintenance

- [x] **GMT-01**: `wikify maintain` writes a graph agent task queue artifact for queued maintenance actions.
- [x] **GMT-02**: Agent task queue entries include source finding id, action, priority, target, evidence, write scope, instructions, acceptance checks, status, and `requires_user`.
- [x] **GMT-03**: Dry-run mode previews agent tasks in the JSON result but does not write task queue artifacts to `sorted/`.
- [x] **GMT-04**: Non-dry-run mode writes `sorted/graph-agent-tasks.json` alongside findings, plan, and history.
- [x] **GMT-05**: V1 task generation never edits content pages or calls an LLM.

### Protocol And Documentation

- [x] **DOC-01**: README and protocol docs describe the agent task queue artifact and V1 safety rule.
- [x] **DOC-02**: The CLI result exposes the task queue artifact path and summary count for downstream automation.

### Agent Task Consumption

- [x] **TSK-01**: `wikify tasks` reads `sorted/graph-agent-tasks.json` and returns a stable JSON envelope.
- [x] **TSK-02**: `wikify tasks` can filter tasks by `--status`, `--action`, `--id`, and `--limit`.
- [x] **TSK-03**: `wikify tasks --refresh` explicitly refreshes maintenance artifacts before reading tasks.
- [x] **TSK-04**: Missing task queue files return a structured non-retryable `agent_task_queue_missing` error.
- [x] **TSK-05**: Task reading does not edit content pages or mutate task status in V1.

## v1.1 Requirements

### Scoped Patch Proposal

- [x] **PRP-01**: `wikify propose --task-id <id>` reads one existing graph agent task and returns a stable JSON envelope.
- [x] **PRP-02**: Proposals are written to `sorted/graph-patch-proposals/<task-id>.json` unless `--dry-run` is used.
- [x] **PRP-03**: Every proposed file path is validated against the selected task `write_scope`.
- [x] **PRP-04**: Proposal generation never applies patches, rewrites content pages, or mutates task status.
- [x] **PRP-05**: Missing task, missing write scope, invalid write path, and missing queue cases return structured errors with exit code 2.
- [x] **PRP-06**: Proposal artifacts include evidence, planned edits, acceptance checks, risk level, and a preflight summary.

### Agent Task Lifecycle

- [x] **LIF-01**: Task state supports explicit transitions among queued, proposed, in_progress, done, failed, blocked, and rejected.
- [x] **LIF-02**: Lifecycle commands support retry, cancel, restore, and mark-done semantics without content edits.
- [x] **LIF-03**: Every task state transition appends an event to an audit artifact.
- [x] **LIF-04**: Invalid transitions return structured non-retryable errors.
- [x] **LIF-05**: Existing read-only `wikify tasks` behavior remains backward compatible.

### Graph Relevance Scoring

- [x] **REL-01**: Graph analysis computes explainable relevance signals for direct links, source overlap, common neighbors, and type affinity.
- [x] **REL-02**: Relevance scores are attached to findings and agent tasks with signal-level evidence.
- [x] **REL-03**: Relevance scores prioritize and explain suggestions but do not trigger automatic writes.
- [x] **REL-04**: Low-confidence relevance results are informational and do not generate high-priority tasks.

### Purpose-Aware Proposals

- [x] **PUR-01**: Wikify supports an optional purpose artifact, such as `purpose.md` or `wikify-purpose.md`, for project direction.
- [x] **PUR-02**: Proposal generation can include purpose evidence when the artifact exists.
- [x] **PUR-03**: Missing purpose context is non-blocking and explicitly reported in proposal metadata.
- [x] **PUR-04**: Purpose context influences proposal rationale, not path safety rules.

## v1.2 Requirements

### Patch Apply And Rollback Contract

- [x] **APP-01**: `wikify apply` reads one patch proposal and one agent-generated patch bundle, then returns a stable JSON envelope.
- [x] **APP-02**: Patch bundle operations are validated against the proposal `write_scope` and wiki-root path safety rules.
- [x] **APP-03**: `wikify apply --dry-run` performs preflight validation without writing content or audit records.
- [x] **APP-04**: Non-dry-run apply supports deterministic text replacement only when the expected source text matches exactly once.
- [x] **APP-05**: Successful apply writes an audit record with task id, proposal path, bundle path, affected paths, before/after hashes, and rollback metadata.
- [x] **APP-06**: `wikify rollback` restores an application only when current content still matches the recorded post-apply hash.

## v2 Requirements

### Agent Task Workflow Runner

- [x] **RUN-01**: `wikify run-task --id <id>` reads one graph agent task and returns a stable workflow run envelope.
- [x] **RUN-02**: The runner creates or reuses a scoped patch proposal for the task.
- [x] **RUN-03**: If no patch bundle exists, the runner returns `waiting_for_patch_bundle` with agent-facing next actions and no content mutation.
- [x] **RUN-04**: If a patch bundle exists, the runner applies it through the existing deterministic apply contract.
- [x] **RUN-05**: Successful non-dry-run application marks the task `done` through lifecycle events.
- [x] **RUN-06**: `run-task --dry-run` writes no proposals, task events, content changes, or application records.
- [x] **RUN-07**: Workflow errors are structured and preserve already-auditable intermediate state.

### Patch Bundle Request Contract

- [x] **BND-01**: `wikify bundle-request --task-id <id>` reads one graph agent task, creates or reuses its proposal context, and returns a stable request envelope.
- [x] **BND-02**: Non-dry-run writes `sorted/graph-patch-bundle-requests/<task-id>.json`; `--dry-run` writes nothing.
- [x] **BND-03**: Request artifacts include task/proposal evidence, intended write scope, allowed operation contract, target file snapshots, and content hashes.
- [x] **BND-04**: Request generation never edits content pages and never mutates task lifecycle state.
- [x] **BND-05**: Missing task queue, missing task, unsafe paths, and missing target files return structured errors with exit code 2.
- [x] **BND-06**: Docs define how an external agent should turn a request into a `wikify.patch-bundle.v1` artifact.

### Runner Bundle Request Handoff

- [x] **HND-01**: `wikify run-task --id <id>` writes or refreshes a patch bundle request artifact when the patch bundle is missing.
- [x] **HND-02**: `run-task --dry-run` previews bundle request handoff without writing proposal, request, lifecycle events, content changes, or application records.
- [x] **HND-03**: `run-task` results expose `artifacts.patch_bundle_request`, `summary.bundle_request_path`, and `summary.suggested_bundle_path`.
- [x] **HND-04**: Bundle request generation errors inside `run-task` are structured with `details.phase = "bundle_request"` and preserve already-auditable intermediate state.
- [x] **HND-05**: Docs explain that normal automation can call `run-task` first; a separate `bundle-request` command remains available for explicit handoff refreshes.

### External Patch Bundle Producer

- [x] **EBP-01**: `wikify produce-bundle --request-path <path> --agent-command <command>` invokes an explicit external command to generate a patch bundle.
- [x] **EBP-02**: The producer passes the request JSON on stdin and exposes request/bundle paths through environment variables.
- [x] **EBP-03**: The producer writes valid stdout JSON to the request's `suggested_bundle_path`, or accepts a command-written bundle at that path.
- [x] **EBP-04**: Produced bundles are validated with the deterministic apply preflight before returning success.
- [x] **EBP-05**: `produce-bundle --dry-run` does not execute the external command and writes no bundle.
- [x] **EBP-06**: Command failures, timeouts, missing requests, invalid output, and patch preflight failures return structured errors.
- [x] **EBP-07**: Docs define the external command contract and make clear that provider/key/retry semantics stay outside hidden CLI defaults.

### Run Task Producer Automation

- [x] **RTP-01**: `wikify run-task --id <id> --agent-command <command>` invokes the explicit producer when no patch bundle exists.
- [x] **RTP-02**: A non-dry-run command can complete proposal, lifecycle proposed state, bundle request, bundle production, deterministic apply, and mark-done in one flow.
- [x] **RTP-03**: Existing patch bundles are applied without executing the producer command.
- [x] **RTP-04**: `run-task --dry-run --agent-command <command>` does not execute the command and writes no proposal, request, lifecycle event, bundle, content, or application record.
- [x] **RTP-05**: Producer failures inside `run-task` return structured errors with `details.phase = "bundle_producer"` and preserve already-auditable intermediate artifacts.
- [x] **RTP-06**: The CLI exposes producer timeout control without introducing hidden provider/key/retry defaults.
- [x] **RTP-07**: Docs describe the one-command automation flow and its explicit external-command safety boundary.

### Batch Task Automation

- [x] **BTA-01**: `wikify run-tasks` selects tasks from the graph agent task queue by status, action, id, and limit.
- [x] **BTA-02**: Batch runs default to `status=queued`, `limit=5`, and sequential execution.
- [x] **BTA-03**: Each selected task is executed through the existing `run_agent_task` workflow with optional explicit `--agent-command`.
- [x] **BTA-04**: Batch dry-run writes no proposals, requests, bundles, lifecycle events, content changes, or application records.
- [x] **BTA-05**: Existing per-task safety rules remain intact: no hidden provider execution, deterministic apply only, and explicit producer command only when provided.
- [x] **BTA-06**: Per-task successes, waiting states, and failures are returned in a stable `wikify.agent-task-batch-run.v1` result.
- [x] **BTA-07**: Batch execution stops on the first per-task failure by default and supports explicit `--continue-on-error`.
- [x] **BTA-08**: Docs describe the batch command, bounded defaults, stop-on-error behavior, and explicit external-command boundary.

### Maintenance Run Automation

- [x] **MRA-01**: `wikify maintain-run` refreshes graph maintenance artifacts before task selection.
- [x] **MRA-02**: The command executes selected tasks through the existing bounded `run_agent_tasks` workflow.
- [x] **MRA-03**: Defaults are conservative: balanced maintenance policy, queued task status, limit 5, sequential execution, and stop-on-error.
- [x] **MRA-04**: `--agent-command` remains explicit and is only forwarded to the batch runner when provided.
- [x] **MRA-05**: `--dry-run` previews maintenance and task selection intent without executing task producers, writing lifecycle events, applying bundles, or mutating content.
- [x] **MRA-06**: Results use a stable `wikify.maintenance-run.v1` schema with maintenance summary, batch summary or preview, artifacts, and next actions.
- [x] **MRA-07**: Structured errors preserve phase context for maintenance refresh and batch execution failures.

### Agent Profile Configuration

- [x] **AGP-01**: `wikify agent-profile --set <name>` persists a named external agent command profile in a versioned project config artifact.
- [x] **AGP-02**: `wikify agent-profile --list`, `--show <name>`, and `--unset <name>` return stable JSON envelopes.
- [x] **AGP-03**: Profiles store command, optional timeout, description, and timestamps, but do not store provider secrets or hidden retry/model defaults.
- [x] **AGP-04**: `produce-bundle`, `run-task`, `run-tasks`, and `maintain-run` accept `--agent-profile <name>`.
- [x] **AGP-05**: Profile resolution passes the explicit stored command into the existing producer flow without changing preflight/apply/lifecycle semantics.
- [x] **AGP-06**: Passing both `--agent-command` and `--agent-profile` returns a structured non-retryable ambiguity error.
- [x] **AGP-07**: Missing profile/config cases return structured errors without executing producer commands.
- [x] **AGP-08**: Docs describe the profile artifact, command usage, and explicit external-agent safety boundary.

### Explicit Default Agent Profile

- [x] **DFP-01**: Profile config stores an optional `default_profile` field.
- [x] **DFP-02**: `wikify agent-profile --set-default <name>` validates and persists an existing profile as default.
- [x] **DFP-03**: `wikify agent-profile --show-default` and `--clear-default` return stable JSON envelopes.
- [x] **DFP-04**: Unsetting the current default profile clears `default_profile`.
- [x] **DFP-05**: Automation commands parse bare `--agent-profile` as the explicit default-profile shorthand.
- [x] **DFP-06**: Missing default profile cases return structured errors without executing producer commands.
- [x] **DFP-07**: Docs clarify that default profiles do not trigger external execution unless `--agent-profile` is explicitly present.

### Maintenance Loop Automation

- [x] **MLP-01**: `wikify maintain-loop` repeats `maintain-run` rounds with bounded defaults.
- [x] **MLP-02**: The loop enforces positive `--max-rounds`, `--task-budget`, and per-round `--limit` values.
- [x] **MLP-03**: The loop stops on no selected tasks, waiting states, batch failures, task budget exhaustion, max rounds, or dry-run preview.
- [x] **MLP-04**: The loop forwards explicit `--agent-command` or `--agent-profile` execution into each round without introducing hidden provider behavior.
- [x] **MLP-05**: Dry-run executes one preview round only and does not execute producer commands or mutate task/content artifacts.
- [x] **MLP-06**: Results include aggregate summary counts, stop reason, per-round outcomes, artifacts, and next actions.
- [x] **MLP-07**: Docs describe loop automation, stop conditions, default bounds, and explicit external-agent safety.
- [x] **MLP-08**: Full unittest and compile verification pass.

### Agent Verifier Gate

- [x] **VFG-01**: `wikify verify-bundle` builds a verifier request from proposal, patch bundle, and deterministic preflight output.
- [x] **VFG-02**: Verifier commands receive JSON on stdin and must return a `wikify.patch-bundle-verdict.v1` JSON verdict.
- [x] **VFG-03**: Accepted verifier verdicts write `sorted/graph-patch-verifications/<task-id>.json` and allow downstream apply.
- [x] **VFG-04**: Rejected verifier verdicts write an audit artifact and block apply before content mutation or lifecycle mark-done.
- [x] **VFG-05**: `run-task`, `run-tasks`, `maintain-run`, and `maintain-loop` accept explicit `--verifier-command` and `--verifier-profile` flags.
- [x] **VFG-06**: Dry-run paths do not execute verifier commands or write verification artifacts.
- [x] **VFG-07**: Invalid verifier output, command failure, and timeout return structured non-retryable errors.
- [x] **VFG-08**: Docs and tests cover verifier contract, profile shorthand, and explicit external-agent boundaries.

### Verifier Rejection Feedback

- [ ] **VRF-01**: Verifier rejection in `run-task` marks the selected task `blocked`.
- [ ] **VRF-02**: Blocked task metadata includes verifier rejection summary, findings, and verification artifact path.
- [ ] **VRF-03**: The lifecycle event for the block includes the same feedback details.
- [ ] **VRF-04**: `patch_bundle_verification_rejected` error details expose `agent_tasks`, `task_events`, and `verification_path`.
- [ ] **VRF-05**: Rejected verifier feedback does not mutate content or write application records.
- [ ] **VRF-06**: Retrying or restoring blocked work clears stale verifier rejection metadata.
- [ ] **VRF-07**: Docs and tests describe rejection feedback and retry behavior.

### Agent Consumer

- **AGT-01**: A future command can generate provider-backed patch bundles with explicit provider/key/retry semantics.
- **AGT-02**: A future command can run provider-backed semantic generation with explicit provider/key/retry semantics.
- **AGT-03**: A future command can support richer multi-operation patch bundles after sequential hash semantics are designed.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Built-in LLM execution | Provider configuration and rollback policy need a separate design phase. |
| Automatic semantic edits | Link repair and synthesis require judgment that V1/V1.1 should hand to a proposal agent. |
| Interactive prompts | The user asked for low-interruption automation. |
| GPL code reuse from `nashsu/llm_wiki` | Wikify can borrow ideas but must not copy GPLv3 implementation into an MIT project. |
| Desktop UI parity | Wikify is CLI-first and agent-facing. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GMT-01 | Phase 1 | Complete |
| GMT-02 | Phase 1 | Complete |
| GMT-03 | Phase 1 | Complete |
| GMT-04 | Phase 1 | Complete |
| GMT-05 | Phase 1 | Complete |
| DOC-01 | Phase 1 | Complete |
| DOC-02 | Phase 1 | Complete |
| TSK-01 | Phase 2 | Complete |
| TSK-02 | Phase 2 | Complete |
| TSK-03 | Phase 2 | Complete |
| TSK-04 | Phase 2 | Complete |
| TSK-05 | Phase 2 | Complete |
| PRP-01 | Phase 3 | Complete |
| PRP-02 | Phase 3 | Complete |
| PRP-03 | Phase 3 | Complete |
| PRP-04 | Phase 3 | Complete |
| PRP-05 | Phase 3 | Complete |
| PRP-06 | Phase 3 | Complete |
| LIF-01 | Phase 4 | Complete |
| LIF-02 | Phase 4 | Complete |
| LIF-03 | Phase 4 | Complete |
| LIF-04 | Phase 4 | Complete |
| LIF-05 | Phase 4 | Complete |
| REL-01 | Phase 5 | Complete |
| REL-02 | Phase 5 | Complete |
| REL-03 | Phase 5 | Complete |
| REL-04 | Phase 5 | Complete |
| PUR-01 | Phase 6 | Complete |
| PUR-02 | Phase 6 | Complete |
| PUR-03 | Phase 6 | Complete |
| PUR-04 | Phase 6 | Complete |
| APP-01 | Phase 7 | Complete |
| APP-02 | Phase 7 | Complete |
| APP-03 | Phase 7 | Complete |
| APP-04 | Phase 7 | Complete |
| APP-05 | Phase 7 | Complete |
| APP-06 | Phase 7 | Complete |
| RUN-01 | Phase 8 | Complete |
| RUN-02 | Phase 8 | Complete |
| RUN-03 | Phase 8 | Complete |
| RUN-04 | Phase 8 | Complete |
| RUN-05 | Phase 8 | Complete |
| RUN-06 | Phase 8 | Complete |
| RUN-07 | Phase 8 | Complete |
| BND-01 | Phase 9 | Complete |
| BND-02 | Phase 9 | Complete |
| BND-03 | Phase 9 | Complete |
| BND-04 | Phase 9 | Complete |
| BND-05 | Phase 9 | Complete |
| BND-06 | Phase 9 | Complete |
| HND-01 | Phase 10 | Complete |
| HND-02 | Phase 10 | Complete |
| HND-03 | Phase 10 | Complete |
| HND-04 | Phase 10 | Complete |
| HND-05 | Phase 10 | Complete |
| EBP-01 | Phase 11 | Complete |
| EBP-02 | Phase 11 | Complete |
| EBP-03 | Phase 11 | Complete |
| EBP-04 | Phase 11 | Complete |
| EBP-05 | Phase 11 | Complete |
| EBP-06 | Phase 11 | Complete |
| EBP-07 | Phase 11 | Complete |
| RTP-01 | Phase 12 | Complete |
| RTP-02 | Phase 12 | Complete |
| RTP-03 | Phase 12 | Complete |
| RTP-04 | Phase 12 | Complete |
| RTP-05 | Phase 12 | Complete |
| RTP-06 | Phase 12 | Complete |
| RTP-07 | Phase 12 | Complete |
| BTA-01 | Phase 13 | Complete |
| BTA-02 | Phase 13 | Complete |
| BTA-03 | Phase 13 | Complete |
| BTA-04 | Phase 13 | Complete |
| BTA-05 | Phase 13 | Complete |
| BTA-06 | Phase 13 | Complete |
| BTA-07 | Phase 13 | Complete |
| BTA-08 | Phase 13 | Complete |
| MRA-01 | Phase 14 | Complete |
| MRA-02 | Phase 14 | Complete |
| MRA-03 | Phase 14 | Complete |
| MRA-04 | Phase 14 | Complete |
| MRA-05 | Phase 14 | Complete |
| MRA-06 | Phase 14 | Complete |
| MRA-07 | Phase 14 | Complete |
| AGP-01 | Phase 15 | Complete |
| AGP-02 | Phase 15 | Complete |
| AGP-03 | Phase 15 | Complete |
| AGP-04 | Phase 15 | Complete |
| AGP-05 | Phase 15 | Complete |
| AGP-06 | Phase 15 | Complete |
| AGP-07 | Phase 15 | Complete |
| AGP-08 | Phase 15 | Complete |
| DFP-01 | Phase 16 | Complete |
| DFP-02 | Phase 16 | Complete |
| DFP-03 | Phase 16 | Complete |
| DFP-04 | Phase 16 | Complete |
| DFP-05 | Phase 16 | Complete |
| DFP-06 | Phase 16 | Complete |
| DFP-07 | Phase 16 | Complete |
| MLP-01 | Phase 17 | Complete |
| MLP-02 | Phase 17 | Complete |
| MLP-03 | Phase 17 | Complete |
| MLP-04 | Phase 17 | Complete |
| MLP-05 | Phase 17 | Complete |
| MLP-06 | Phase 17 | Complete |
| MLP-07 | Phase 17 | Complete |
| MLP-08 | Phase 17 | Complete |
| VFG-01 | Phase 18 | Complete |
| VFG-02 | Phase 18 | Complete |
| VFG-03 | Phase 18 | Complete |
| VFG-04 | Phase 18 | Complete |
| VFG-05 | Phase 18 | Complete |
| VFG-06 | Phase 18 | Complete |
| VFG-07 | Phase 18 | Complete |
| VFG-08 | Phase 18 | Complete |
| VRF-01 | Phase 19 | Planned |
| VRF-02 | Phase 19 | Planned |
| VRF-03 | Phase 19 | Planned |
| VRF-04 | Phase 19 | Planned |
| VRF-05 | Phase 19 | Planned |
| VRF-06 | Phase 19 | Planned |
| VRF-07 | Phase 19 | Planned |

**Coverage:**
- v1 requirements: 12 total
- v1.1 requirements: 19 total
- v1.2 requirements: 6 total
- v2 runner requirements: 7 total
- v2 bundle request requirements: 6 total
- v2 handoff requirements: 5 total
- v2 producer requirements: 7 total
- v2 run-task producer automation requirements: 7 total
- v2 batch automation requirements: 8 total
- v2 maintenance run automation requirements: 7 total
- v2 agent profile requirements: 8 total
- v2 default profile requirements: 7 total
- v2 maintenance loop requirements: 8 total
- v2 agent verifier gate requirements: 8 total
- v2 verifier rejection feedback requirements: 7 total
- Mapped to phases: 122
- Unmapped: 0

---
*Requirements defined: 2026-04-28*
*Last updated: 2026-04-29 for Phase 19 planning*
