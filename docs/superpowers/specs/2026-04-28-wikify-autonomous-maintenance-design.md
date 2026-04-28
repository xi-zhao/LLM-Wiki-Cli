# Wikify Autonomous Maintenance Design

Date: 2026-04-28

## Purpose

Wikify should not ask the user to manually inspect every graph issue. The graph layer should feed an autonomous agent maintenance loop that can build structure, review findings, choose safe actions, execute low-risk maintenance, and record what happened.

The product goal is:

> `wikify maintain` lets the agent keep the wiki healthy without interrupting the user.

The user sets policy. The agent handles routine review and maintenance.

## Product Command

Primary command:

```bash
wikify maintain
wikify maintain --policy conservative
wikify maintain --policy balanced
wikify maintain --policy aggressive
wikify maintain --dry-run
```

Default policy: `balanced`.

Default behavior:

- Build or refresh graph artifacts.
- Produce graph findings.
- Build an action plan.
- Apply safe deterministic actions allowed by policy.
- Write findings, plan, and run history.
- Return a JSON envelope with summary and artifacts.
- Never prompt the user during the run.

## Product Loop

```text
compiled Markdown wiki
  -> wikify graph
  -> graph findings
  -> autonomous action plan
  -> policy gate
  -> safe auto-apply
  -> history/state artifacts
  -> final JSON envelope
```

This is an agent loop, not a human review loop. Reports are still written for observability, but the primary consumer is the next agent step.

## Data Ownership

- `wikify graph` owns `graph/graph.json`, `graph/GRAPH_REPORT.md`, and `graph/graph.html`.
- `wikify maintain` owns `sorted/graph-findings.json`, `sorted/graph-maintenance-plan.json`, and `sorted/graph-maintenance-history.json`.
- Existing ingest/maintenance history in `sorted/maintenance-history.json` remains owned by the older control loop until a later migration.
- V1 `wikify maintain` must not rewrite article bodies, topic bodies, parsed notes, or source material.

## Finding Schema

Every finding must be machine-actionable:

```json
{
  "id": "broken-link:topics/topics-moc.md:24:wikilink",
  "type": "broken_link",
  "severity": "warning",
  "title": "Broken wikilink",
  "subject": "topics/topics-moc.md",
  "evidence": {
    "source": "topics/topics-moc.md",
    "target": "wikilink",
    "line": 24,
    "label": "unresolved_wikilink"
  },
  "recommended_action": "queue_link_repair",
  "can_auto_apply": false,
  "policy_minimum": "conservative"
}
```

Finding types for V1:

- `broken_link`
- `orphan_node`
- `god_node`
- `mature_community`
- `thin_graph`

Severity:

- `info`: useful but not urgent.
- `warning`: should be handled by a future agent pass.
- `critical`: structural issue blocks reliable automation.

V1 should prefer `info` and `warning`. Critical is reserved for unreadable or malformed graph data.

## Action Plan Schema

```json
{
  "schema_version": "wikify.maintenance-plan.v1",
  "policy": "balanced",
  "steps": [
    {
      "id": "queue-link-repair:topics/topics-moc.md:24",
      "action": "queue_link_repair",
      "finding_id": "broken-link:topics/topics-moc.md:24:wikilink",
      "target": "topics/topics-moc.md",
      "status": "planned",
      "can_execute": false,
      "risk": "semantic",
      "reason": "Broken wikilink requires semantic target selection."
    }
  ]
}
```

Action types for V1:

- `queue_link_repair`
- `queue_orphan_attachment`
- `queue_digest_refresh`
- `queue_community_synthesis`
- `record_graph_health_snapshot`

V1 execution is conservative even under aggressive policy: it may write queue/history artifacts and graph health snapshots, but it does not edit content pages.

## Policy Semantics

### Conservative

Automatic:

- Build graph.
- Write findings.
- Write plan.
- Write history.

Queued:

- Link repair.
- Orphan attachment.
- Digest refresh.
- Community synthesis.

### Balanced

Automatic:

- Everything in conservative.
- Mark duplicate repeated findings as already-seen in history.
- Include recommended next command strings for agent continuation.

Queued:

- Any content modification.

### Aggressive

Automatic in V1:

- Same as balanced.

Reserved for later:

- Deterministic source index cleanup.
- Deterministic generated-page refresh.

Aggressive must not edit content pages until a later spec defines safe write contracts.

## Module Design

```text
wikify/
  maintenance/
    __init__.py
    findings.py      # graph -> findings
    planner.py       # findings -> action plan
    executor.py      # policy-gated safe writes
    history.py       # append-only maintenance history
    runner.py        # orchestration for wikify maintain
```

Responsibilities:

- `findings.py` reads graph data only.
- `planner.py` creates steps only; it does not write files.
- `executor.py` applies safe file writes to `sorted/` only.
- `history.py` appends run records and deduplicates repeated finding ids.
- `runner.py` wires graph build, findings, planning, execution, and envelope result.
- `cli.py` parses `maintain` and calls `runner.py`; it does not hold maintenance rules.

## Data Flow

```text
WIKIFY_BASE
  -> graph.builder.build_graph_artifacts()
  -> maintenance.findings.build_findings(graph)
  -> maintenance.planner.build_plan(findings, policy)
  -> maintenance.executor.apply_plan(plan, policy, dry_run)
  -> maintenance.history.append_run(run_record)
  -> envelope_ok("maintain", result)
```

The result envelope includes:

```json
{
  "ok": true,
  "command": "maintain",
  "exit_code": 0,
  "result": {
    "policy": "balanced",
    "dry_run": false,
    "summary": {
      "finding_count": 4,
      "planned_count": 4,
      "executed_count": 3,
      "queued_count": 1
    },
    "artifacts": {
      "graph_json": "/abs/kb/graph/graph.json",
      "findings": "/abs/kb/sorted/graph-findings.json",
      "plan": "/abs/kb/sorted/graph-maintenance-plan.json",
      "history": "/abs/kb/sorted/graph-maintenance-history.json"
    },
    "next_commands": [
      "wikify show topics/topics-moc.md --meta-only"
    ],
    "completion": {}
  }
}
```

## Non-Interruption Rule

`wikify maintain` must not ask questions, open prompts, or require interactive approval. When a step is unsafe, it is queued as a plan item with enough evidence for a later agent to handle.

The user only sees the final summary unless they ask for details.

## Anti-Mess Constraints

1. No maintenance rules in `wikify/cli.py`.
2. No content-page edits in V1 autonomous maintenance.
3. No hidden LLM calls.
4. Findings must be deterministic from `graph.json`.
5. Every planned action must reference a finding id.
6. Every executed action must write an execution record.
7. `--dry-run` must produce findings and plan without writing findings/plan/history artifacts.
8. `maintain` must work on an empty or tiny KB without crashing.

## Testing Strategy

Required tests:

- Parser accepts `maintain`, `--policy`, and `--dry-run`.
- Findings are produced for broken links and orphan nodes.
- Findings are summarized by type and severity.
- Planner maps each finding to a step with a stable action.
- Executor writes findings, plan, and history under `sorted/`.
- `--dry-run` returns the same plan shape without writing maintenance artifacts.
- `wikify maintain` builds graph artifacts first.
- `wikify maintain` returns a stable JSON envelope.
- Full test suite remains green.

## Future Extensions

After V1:

- Add `wikify decide --graph` as a view over the latest maintenance plan.
- Add safe generated-page refresh contracts for digest and community synthesis.
- Add optional LLM-assisted semantic repair behind an explicit provider flag.
- Merge graph maintenance history with the older maintenance history after schemas converge.

