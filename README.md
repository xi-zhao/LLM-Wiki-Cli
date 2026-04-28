# Wikify

Agent-facing CLI for maintaining a local Markdown knowledge base.

`wikify` gives agents a stable control surface for ingest, maintenance, decision, execution, and graph understanding, while keeping Markdown notes as the human-readable source of truth.

This project is explicitly inspired by Andrej Karpathy's LLM Wiki / markdown-first knowledge workflow, then pushed further toward agent-facing control, automation, and protocolized outputs.

`fokb` remains available as a compatibility alias for older scripts.

## Why this exists

Most knowledge tooling optimizes for either:
- human note-taking, or
- retrieval over a pile of source files

Wikify takes a different path, in the spirit of Karpathy's LLM Wiki idea:
- raw materials are preserved
- agents compile them into structured Markdown objects
- follow-up maintenance happens incrementally
- every important action returns machine-readable JSON

In short:

**JSON contract for agents, Markdown notes for humans and Obsidian.**

## What it does

- Ingest URLs into a local wiki
- Maintain parsed articles, briefs, topics, timelines, and digests
- Return stable JSON envelopes for automation
- Emit maintenance verdicts after write operations
- Produce decision plans and optional execution steps
- Keep an Obsidian-friendly navigation layer alongside the CLI layer
- Build graph artifacts that explain wiki structure, central nodes, communities, and broken links

## 30-second example

```bash
pip install -e .

wikify check
wikify stats
wikify ingest "https://example.com"
wikify maintenance --last
wikify graph
wikify maintain --dry-run
```

Example success envelope:

```json
{
  "ok": true,
  "command": "digest",
  "exit_code": 0,
  "result": {
    "topic": "agent-knowledge-loops.md",
    "output": "/abs/path/sorted/agent-knowledge-loops-digest.md",
    "completion": {
      "status": "completed",
      "summary": "digest completed, output written to /abs/path/sorted/agent-knowledge-loops-digest.md",
      "artifacts": [
        "/abs/path/sorted/agent-knowledge-loops-digest.md"
      ]
    }
  }
}
```

## Repo shape

This public repo is meant to contain:
- product docs
- CLI and helper scripts
- protocol docs
- tests
- a small `sample-kb/`

It is **not** meant to be a dump of a private working knowledge base.

Your real KB should normally live in:
- another repo, or
- this repo but ignored locally

## Try the sample KB

A minimal public example lives in `sample-kb/`.

```bash
export WIKIFY_BASE="$(pwd)/sample-kb"

wikify stats
wikify show agent-knowledge-loops --scope topics
wikify show 2026-04-10_agent-knowledge-loops --scope parsed
wikify digest agent-knowledge-loops.md
wikify graph --no-html
wikify maintain
```

`wikify graph` writes:
- `graph/graph.json` for agents and automation
- `graph/GRAPH_REPORT.md` for human-readable structure review
- `graph/graph.html` unless `--no-html` is passed

Graph analytics include advisory graph relevance scoring. Signals are direct links, source overlap, common neighbors, and type affinity. Relevance metadata appears in `graph.json`, related findings, and graph agent tasks so agents can prioritize with evidence.

`wikify maintain` runs the autonomous graph maintenance loop:
- rebuilds graph artifacts without HTML
- writes `sorted/graph-findings.json`
- writes `sorted/graph-maintenance-plan.json`
- writes `sorted/graph-agent-tasks.json` for downstream agents
- appends `sorted/graph-maintenance-history.json`

Useful modes:

```bash
wikify maintain --dry-run
wikify maintain --policy conservative
wikify maintain --policy balanced
wikify maintain --policy aggressive
wikify tasks
wikify tasks --status queued --limit 5
wikify tasks --refresh --id agent-task-1
wikify propose --task-id agent-task-1
wikify propose --task-id agent-task-1 --dry-run
wikify bundle-request --task-id agent-task-1 --dry-run
wikify bundle-request --task-id agent-task-1
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py" --dry-run
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py"
wikify apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json --dry-run
wikify apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json
wikify rollback --application-path sorted/graph-patch-applications/<application-id>.json --dry-run
wikify rollback --application-path sorted/graph-patch-applications/<application-id>.json
wikify run-task --id agent-task-1 --dry-run
wikify run-task --id agent-task-1
wikify run-task --id agent-task-1 --agent-command "python3 agent.py" --producer-timeout 120
wikify run-tasks --limit 5 --agent-command "python3 agent.py"
wikify run-tasks --status queued --action queue_link_repair --limit 5 --continue-on-error --agent-command "python3 agent.py"
wikify tasks --id agent-task-1 --mark-proposed --proposal-path sorted/graph-patch-proposals/agent-task-1.json
wikify tasks --id agent-task-1 --start
wikify tasks --id agent-task-1 --mark-done
```

`graph-agent-tasks.json` is the handoff artifact for later agents. Each queued task carries the source finding, action, target, evidence, write scope, agent instructions, acceptance checks, and `requires_user: false`.

`wikify tasks` is the read API for that handoff artifact. By default it only reads `sorted/graph-agent-tasks.json`; `--refresh` explicitly runs `wikify maintain` first. If the artifact is missing, the command returns `agent_task_queue_missing`.

`wikify propose` turns one queued graph agent task into `sorted/graph-patch-proposals/<task-id>.json`. It validates every proposed path against the task `write_scope`. `--dry-run` returns the proposal JSON without writing the artifact.

Patch proposals are purpose-aware when the wiki root contains `purpose.md` or `wikify-purpose.md`. The proposal includes `purpose_context` and `rationale` so downstream agents can explain why the repair matters. Missing purpose context is explicit and non-blocking; it never expands `write_scope` or weakens path validation.

`wikify bundle-request` turns one task and its proposal context into `sorted/graph-patch-bundle-requests/<task-id>.json`. The request includes target file snapshots, SHA-256 hashes, proposal evidence, the default bundle output path, and the allowed `wikify.patch-bundle.v1` `replace_text` contract. It remains useful as an explicit refresh or manual handoff command; `--dry-run` returns the request without writing request or proposal artifacts.

`wikify produce-bundle` invokes an explicit external agent command to turn a `wikify.patch-bundle-request.v1` file into a `wikify.patch-bundle.v1` artifact. The request JSON is passed on stdin, and `WIKIFY_BASE`, `WIKIFY_PATCH_BUNDLE_REQUEST`, and `WIKIFY_PATCH_BUNDLE` are exposed as environment variables. The external command may print bundle JSON to stdout or write the suggested bundle path directly. Wikify preflights the produced bundle before returning `bundle_ready`; `--dry-run` does not execute the command or write a bundle.

`wikify apply` consumes a proposal plus an agent-generated patch bundle. V1.2 supports deterministic `replace_text` operations only: each source text must match exactly once, each path must stay inside the proposal `write_scope`, and `--dry-run` writes nothing. A real apply writes `sorted/graph-patch-applications/<application-id>.json` with before/after hashes. `wikify rollback` restores from that application record only when the current file hash still matches the recorded post-apply hash.

`wikify run-task` is the low-interruption workflow runner. It creates or reuses a proposal, looks for `sorted/graph-patch-bundles/<task-id>.json`, applies it when present, and marks the task done after a successful apply. If the patch bundle is missing, it writes `sorted/graph-patch-bundle-requests/<task-id>.json`, returns `waiting_for_patch_bundle`, and exposes both `artifacts.patch_bundle_request` and `summary.suggested_bundle_path`. An external agent can consume that request through `wikify produce-bundle`, then call `wikify run-task --id <task-id>` again.

For one-command automation, `wikify run-task --id <task-id> --agent-command "<command>"` writes the request, invokes that explicit external command through the same producer contract, applies the preflighted bundle, and marks the task done. `--dry-run --agent-command` does not execute the command or write artifacts, and existing bundle files are applied without executing the command.

`wikify run-tasks` is the bounded batch runner. By default it selects queued tasks, limits the batch to 5, runs tasks sequentially through the same audited `run-task` workflow, and stops on the first per-task failure. Use `--continue-on-error` to keep going after a failed item. `--dry-run` writes nothing across the whole batch, and `--agent-command` remains an explicit external command passed into each task run.

Explicit lifecycle actions on `wikify tasks` persist task status changes and append `sorted/graph-agent-task-events.json`. Supported actions include `--mark-proposed`, `--start`, `--mark-done`, `--mark-failed`, `--block`, `--cancel`, `--retry`, and `--restore`. Invalid transitions return `invalid_agent_task_transition`.

Safety rule: `wikify maintain`, `wikify tasks`, `wikify propose`, `wikify bundle-request`, and `wikify produce-bundle` do not edit content pages or call hidden LLMs. `run-task --agent-command`, `run-tasks --agent-command`, and `produce-bundle` only invoke the explicit command supplied by the caller and preflight its bundle output. `wikify apply` remains the deterministic content mutation path.

## Documentation map

- Product doc: `LLM-Wiki-Cli-README.md`
- Protocol: `scripts/fokb_protocol.md`
- Script index: `scripts/README.md`
- Quickstart: `QUICKSTART.md`
- Schema: `WIKI_SCHEMA.md`
- Release hygiene: `RELEASE-CHECKLIST.md`

## Core ideas

- Agents should consume stable JSON, not parse prose
- Markdown should stay readable and editable by humans
- Maintenance should be incremental, not only full-library rescans
- Obsidian-facing notes and agent-facing contracts can coexist cleanly
- Graph understanding should be derived from explicit wiki structure with provenance-rich edges
- Graph relevance should explain priority with source overlap, common neighbors, and type affinity, not silently trigger writes
- Purpose-aware proposals should explain alignment when `purpose.md` or `wikify-purpose.md` exists, without changing safety rules
- Patch bundle requests should package target snapshots and bundle instructions for external agents instead of hiding provider calls in the CLI
- Patch bundle production should be an explicit external-command adapter with stdin/env contracts and deterministic preflight, not a hidden provider integration
- Patch application should require explicit patch bundle input, exact preflight, audit records, and hash-guarded rollback
- Agent task runners should prepare a patch bundle request at `waiting_for_patch_bundle` instead of prompting users or generating hidden content
- Batch automation should be bounded, sequential, and stop-on-error by default before any concurrent execution exists

## Current status

Alpha, but already usable as an agent-facing control plane.

Implemented areas include:
- stable JSON envelope
- maintenance contract
- decision / execution loop
- autonomous graph maintenance loop
- scoped patch proposal generation from graph agent tasks
- purpose-aware patch proposal rationale
- patch bundle request artifacts for external agents
- explicit external patch bundle producer command
- deterministic patch bundle apply and rollback
- low-interruption agent task runner
- bounded batch task runner
- completion contract for write actions
- Obsidian-friendly topic, digest, article, brief, and navigation outputs
- local graph artifact generation with JSON, Markdown report, and optional HTML

## License

MIT
