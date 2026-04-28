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

## v2 Requirements

### Agent Consumer

- **AGT-01**: A future command can consume `graph-agent-tasks.json` and propose patches.
- **AGT-02**: A future command can apply deterministic, preflighted repairs under explicit policy.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Built-in LLM execution | Provider configuration and rollback policy need a separate design phase. |
| Automatic semantic edits | Link repair and synthesis require judgment that V1 should hand to a review agent. |
| Interactive prompts | The user asked for low-interruption automation. |

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

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-04-28*
*Last updated: 2026-04-28 after Phase 2 completion*
