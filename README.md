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

- Initialize a personal wiki workspace with a source registry
- Register source files, directories, URLs, repositories, and notes without hidden fetch/sync work
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

wikify init ~/personal-wiki
export WIKIFY_BASE="$HOME/personal-wiki"
wikify source add "https://example.com" --type url
wikify source list
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

## Workspace and source registry

`wikify init [BASE]` creates a personal wiki workspace. It writes:
- `wikify.json`
- `.wikify/registry/sources.json`
- `sources/`
- `wiki/`
- `artifacts/`
- `views/`

`wikify source add <locator> --type <type>` registers a source in `.wikify/registry/sources.json`.

Supported source types are:
- `file`
- `directory`
- `url`
- `repository`
- `note`

Registration is deliberately shallow. It canonicalizes the locator, assigns a stable `src_<uuid>` source id, records local file metadata when available, and sets `last_sync_status` to `never_synced`. It does not fetch URLs, clone repositories, call providers, generate wiki pages, or build graph artifacts. Those are explicit later commands.

Useful commands:

```bash
wikify init ~/personal-wiki
export WIKIFY_BASE="$HOME/personal-wiki"
wikify source add ~/notes/research.md --type file
wikify source add "https://example.com/report" --type url
wikify source list
wikify source show src_<id>
```

When `WIKIFY_BASE` and `FOKB_BASE` are unset, `wikify` looks for `wikify.json` in the current directory or its parents before falling back to the application root.

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
wikify agent-profile --set default --agent-command "python3 agent.py" --producer-timeout 120
wikify agent-profile --set-default default
wikify agent-profile --list
wikify maintain-run --dry-run
wikify maintain-run --limit 5 --agent-command "python3 agent.py"
wikify maintain-run --limit 5 --agent-profile default
wikify maintain-run --limit 5 --agent-profile
wikify maintain-loop --max-rounds 3 --task-budget 15 --limit 5 --agent-profile
wikify tasks
wikify tasks --status queued --limit 5
wikify tasks --refresh --id agent-task-1
wikify propose --task-id agent-task-1
wikify propose --task-id agent-task-1 --dry-run
wikify bundle-request --task-id agent-task-1 --dry-run
wikify bundle-request --task-id agent-task-1
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py" --dry-run
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py"
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-profile default
wikify verify-bundle --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json --verifier-command "python3 verifier.py"
wikify apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json --dry-run
wikify apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json
wikify rollback --application-path sorted/graph-patch-applications/<application-id>.json --dry-run
wikify rollback --application-path sorted/graph-patch-applications/<application-id>.json
wikify run-task --id agent-task-1 --dry-run
wikify run-task --id agent-task-1
wikify run-task --id agent-task-1 --agent-command "python3 agent.py" --producer-timeout 120
wikify run-task --id agent-task-1 --agent-profile default --verifier-profile reviewer
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

`wikify bundle-request` turns one task and its proposal context into `sorted/graph-patch-bundle-requests/<task-id>.json`. The request includes target file snapshots, SHA-256 hashes, proposal evidence, the default bundle output path, and the allowed `wikify.patch-bundle.v1` `replace_text` contract. When prior verifier rejection feedback exists, the request also includes `repair_context` so a producer can address the verifier summary and findings. It remains useful as an explicit refresh or manual handoff command; `--dry-run` returns the request without writing request or proposal artifacts.

`wikify produce-bundle` invokes an explicit external agent command to turn a `wikify.patch-bundle-request.v1` file into a `wikify.patch-bundle.v1` artifact. The request JSON is passed on stdin, and `WIKIFY_BASE`, `WIKIFY_PATCH_BUNDLE_REQUEST`, and `WIKIFY_PATCH_BUNDLE` are exposed as environment variables. The external command may print bundle JSON to stdout or write the suggested bundle path directly. Wikify preflights the produced bundle before returning `bundle_ready`; `--dry-run` does not execute the command or write a bundle.

`wikify verify-bundle` invokes an explicit verifier command before apply. Wikify first runs deterministic preflight, then sends `wikify.patch-bundle-verification-request.v1` JSON on stdin with the proposal, bundle, preflight result, and verdict schema instructions. The verifier must print `wikify.patch-bundle-verdict.v1` JSON with boolean `accepted`. Accepted verdicts write `sorted/graph-patch-verifications/<task-id>.json`; rejected verdicts write the same audit artifact and return `patch_bundle_verification_rejected` before any content mutation. When rejection happens inside `run-task` automation, the selected task is also marked `blocked`, `blocked_feedback` stores the verifier summary, findings, verdict, and verification path, and the block event carries the same details. `--dry-run` builds the request and preflight but does not execute the verifier.

`wikify agent-profile` stores named external command profiles in `wikify-agent-profiles.json` at the wiki root. Profiles reduce repeated CLI typing for long agent adapters: `--agent-profile default` resolves to the stored command and timeout before the existing producer flow runs. `wikify agent-profile --set-default default` stores a default profile, and a bare `--agent-profile` flag uses that default. Passing both `--agent-command` and `--agent-profile` is rejected as ambiguous. Profiles are visible project config; do not store API keys or secrets in the command string.

`wikify apply` consumes a proposal plus an agent-generated patch bundle. V1.2 supports deterministic `replace_text` operations only: each source text must match exactly once, each path must stay inside the proposal `write_scope`, and `--dry-run` writes nothing. A real apply writes `sorted/graph-patch-applications/<application-id>.json` with before/after hashes. `wikify rollback` restores from that application record only when the current file hash still matches the recorded post-apply hash.

`wikify run-task` is the low-interruption workflow runner. It creates or reuses a proposal, looks for `sorted/graph-patch-bundles/<task-id>.json`, optionally runs a verifier gate, applies accepted bundles, and marks the task done after a successful apply. If the patch bundle is missing, it writes `sorted/graph-patch-bundle-requests/<task-id>.json`, returns `waiting_for_patch_bundle`, and exposes both `artifacts.patch_bundle_request` and `summary.suggested_bundle_path`. If the verifier rejects, `patch_bundle_verification_rejected` error details include `verification_path`, `agent_tasks`, and `task_events`, while content stays unchanged and no application record is written. If a verifier-blocked task is run again with an explicit `--agent-command`, Wikify retries the task, writes a repair request with `repair_context`, regenerates the previously rejected default bundle instead of reusing it, then re-runs verifier/apply gates.

For one-command automation, `wikify run-task --id <task-id> --agent-command "<command>"` writes the request, invokes that explicit external command through the same producer contract, applies the preflighted bundle, and marks the task done. Add `--verifier-command "<command>"` or `--verifier-profile <name>` to require agent review between preflight and apply. `--dry-run --agent-command` does not execute producer or verifier commands, and existing bundle files are applied without executing the producer command.

`wikify run-tasks` is the bounded batch runner. By default it selects queued tasks, limits the batch to 5, runs tasks sequentially through the same audited `run-task` workflow, and stops on the first per-task failure. Use `--status blocked --agent-command ... --verifier-command ...` to repair verifier-blocked tasks in a bounded batch. Use `--continue-on-error` to keep going after a failed item. `--dry-run` writes nothing across the whole batch, and `--agent-command` plus `--verifier-command` remain explicit external commands passed into each task run.

`wikify maintain-run` is the one-command maintenance automation entrypoint. It refreshes graph maintenance first, then executes a bounded `run-tasks` batch from the freshly written queue. Defaults stay conservative: balanced policy, queued status, limit 5, sequential execution, and stop on first failure. `--dry-run` refreshes graph artifacts and previews selection from the in-memory maintenance task queue; it does not execute producers, verifiers, apply bundles, write lifecycle events, or mutate content. `--agent-command`, `--agent-profile`, `--verifier-command`, and `--verifier-profile` are the explicit external agent boundaries.

`wikify maintain-loop` repeats that `maintain-run` primitive until a clear stop condition appears. Defaults are deliberately bounded: max rounds 3, task budget 15, per-round limit 5, queued status, balanced policy, sequential execution, and stop-on-error. The result uses `wikify.maintenance-loop.v1` and includes `stop_reason`, aggregate `summary`, per-round `rounds`, artifacts, and next actions. Stop reasons include `no_tasks`, `waiting_for_patch_bundle`, `failed_tasks`, `task_budget_exhausted`, `max_rounds_reached`, and `dry_run_preview`. Dry-run previews one round only, because repeated dry-runs would replay the same in-memory queue. `--agent-command`, `--agent-profile`, `--verifier-command`, and `--verifier-profile` remain explicit.

Explicit lifecycle actions on `wikify tasks` persist task status changes and append `sorted/graph-agent-task-events.json`. Supported actions include `--mark-proposed`, `--start`, `--mark-done`, `--mark-failed`, `--block`, `--cancel`, `--retry`, and `--restore`. `--retry` and `--restore` clear stale `blocked_feedback` so a repaired task does not carry an obsolete verifier verdict. Invalid transitions return `invalid_agent_task_transition`.

Safety rule: `wikify maintain`, `wikify tasks`, `wikify propose`, `wikify bundle-request`, `wikify produce-bundle`, and `wikify verify-bundle` do not edit content pages or call hidden LLMs. `maintain-loop`, `maintain-run`, `run-task`, `run-tasks`, `produce-bundle`, and `verify-bundle` only invoke an external command when the caller supplies an explicit command/profile flag. Every bundle output is still preflighted, and verifier rejection blocks apply; in task automation it also blocks the task with durable feedback. A configured default profile does nothing by itself; the command still needs the explicit profile flag. `wikify apply` remains the deterministic content mutation path.

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
- Agent profiles should remove repeated command typing without storing secrets or adding hidden provider behavior; default profiles must still require explicit use
- Patch application should require explicit patch bundle input, exact preflight, audit records, and hash-guarded rollback
- One-command maintenance automation should compose audited primitives instead of adding hidden provider behavior
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
- explicit agent command profiles
- deterministic patch bundle apply and rollback
- low-interruption agent task runner
- bounded batch task runner
- one-command maintenance run automation
- completion contract for write actions
- Obsidian-friendly topic, digest, article, brief, and navigation outputs
- local graph artifact generation with JSON, Markdown report, and optional HTML

## License

MIT
