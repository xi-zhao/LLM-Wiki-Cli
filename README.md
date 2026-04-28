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
```

`graph-agent-tasks.json` is the handoff artifact for later agents. Each queued task carries the source finding, action, target, evidence, write scope, agent instructions, acceptance checks, and `requires_user: false`.

`wikify tasks` is the read API for that handoff artifact. By default it only reads `sorted/graph-agent-tasks.json`; `--refresh` explicitly runs `wikify maintain` first. If the artifact is missing, the command returns `agent_task_queue_missing`.

`wikify propose` turns one queued graph agent task into `sorted/graph-patch-proposals/<task-id>.json`. It validates every proposed path against the task `write_scope`. `--dry-run` returns the proposal JSON without writing the artifact.

V1 safety rule: `wikify maintain`, `wikify tasks`, and `wikify propose` do not edit content pages or call hidden LLMs. Semantic repairs and generated-content work are queued as plan steps, agent tasks, and scoped patch proposals; only deterministic maintenance bookkeeping can be marked executed.

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

## Current status

Alpha, but already usable as an agent-facing control plane.

Implemented areas include:
- stable JSON envelope
- maintenance contract
- decision / execution loop
- autonomous graph maintenance loop
- scoped patch proposal generation from graph agent tasks
- completion contract for write actions
- Obsidian-friendly topic, digest, article, brief, and navigation outputs
- local graph artifact generation with JSON, Markdown report, and optional HTML

## License

MIT
