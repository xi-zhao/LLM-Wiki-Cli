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
- Sync registered sources into deterministic source item and ingest queue artifacts
- Wikiize queued source items into source-backed Markdown pages and wiki page objects
- Render human-facing wiki views and local static HTML from object/source artifacts
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
wikify sync --dry-run
wikify sync
wikify wikiize --dry-run
wikify wikiize
wikify validate
wikify views --dry-run
wikify views
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
wikify sync --dry-run
wikify sync
wikify sync --source src_<id>
```

When `WIKIFY_BASE` and `FOKB_BASE` are unset, `wikify` looks for `wikify.json` in the current directory or its parents before falling back to the application root.

## Incremental sync and ingest queue

`wikify sync` discovers registered source items, classifies each item as `new`, `changed`, `unchanged`, `missing`, `skipped`, or `errored`, and writes current control-plane artifacts:

- `.wikify/sync/source-items.json` using `wikify.source-items.v1`
- `.wikify/sync/last-sync.json` using `wikify.sync-run.v1`
- `.wikify/queues/ingest-items.json` using `wikify.ingest-queue.v1`

`wikify sync --source src_<id>` limits discovery to one source. `wikify sync --dry-run` returns the same planned status and queue summary without writing `.wikify/sync/`, `.wikify/queues/`, or registry sync metadata.

Sync uses deterministic local fingerprints for files and directories. Re-running without changes reports `unchanged` and does not duplicate queue entries. Only `new` and `changed` items become active pending wikiization work; `missing`, `skipped`, and `errored` items are recorded for status and troubleshooting.

Sync does not fetch URLs, clone repositories, call providers, run `wikify ingest`, generate wiki pages, generate views, or create agent exports. URL and remote repository sources are represented as offline remote items with `network_checked: false`.

## Source-backed wikiization

`wikify wikiize` consumes active `.wikify/queues/ingest-items.json` entries and turns eligible local text/Markdown source items into generated wiki pages.

Primary flow:

```bash
wikify source add ~/notes/research.md --type file
wikify sync
wikify wikiize --dry-run
wikify wikiize
wikify validate --strict --write-report
wikify views --dry-run
wikify views
```

Generated human-readable pages live under:
- `wiki/pages/`

Generated machine-readable objects live under:
- `artifacts/objects/wiki_pages/`
- `artifacts/objects/object-index.json`
- `artifacts/objects/validation.json`

Wikiization control artifacts live under:
- `.wikify/wikiization/last-wikiize.json`
- `.wikify/queues/wikiization-tasks.json`
- `.wikify/wikiization/requests/`
- `.wikify/wikiization/results/`

Useful options:

```bash
wikify wikiize --dry-run
wikify wikiize --queue-id queue_<id>
wikify wikiize --item item_<id>
wikify wikiize --source src_<id>
wikify wikiize --limit 5
wikify wikiize --agent-command "python3 agent.py"
wikify wikiize --agent-profile default
wikify wikiize --agent-profile
```

`--dry-run` reports selected queue entries and planned page/object/request/result paths without writing pages, objects, queue updates, task queues, or run reports.

Local text and Markdown sources use a deterministic baseline: title from the first Markdown H1 or filename, conservative summary from source text, source reference section, and bounded excerpt. Every generated page and object includes `source_refs` with source id, item id, locator/path evidence, fingerprint evidence, and confidence.

Incremental updates are hash guarded. Wikify stores generation metadata on generated page objects and only overwrites an existing generated page when the current file still matches the previous generated hash. If the page drifted, Wikify preserves the user edit, marks the queue entry `needs_review`, and writes a task to `.wikify/queues/wikiization-tasks.json`.

Remote URLs and remote repositories are not fetched by default. Without explicit enrichment they create wikiization tasks, not weak pages. Semantic enrichment requires an explicit `--agent-command` or `--agent-profile`; Wikify writes a `wikify.wikiization-request.v1` artifact, sends it on stdin, accepts a `wikify.wikiization-result.v1` result, then performs final path checks, rendering, object writes, and strict validation itself. There are no hidden provider calls.

`wikify wikiize` only creates source-backed pages and objects. Run `wikify views` to render those objects into human-facing navigation pages and static HTML. `llms.txt`, context packs, and agent query exports remain separate later surfaces.

## Human wiki views and static output

`wikify views` renders the knowledge base artifact for people. It reads existing object/source/control artifacts and writes Markdown views under `views/` plus optional local static HTML under `views/site/`.

Primary flow:

```bash
wikify sync
wikify wikiize
wikify validate --strict --write-report
wikify views --dry-run
wikify views
```

Generated Markdown views include:
- `views/index.md`
- `views/pages.md`
- `views/sources/index.md`
- `views/sources/<source-id>.md`
- `views/topics/index.md`
- `views/projects/index.md`
- `views/people/index.md`
- `views/decisions/index.md`
- `views/timeline.md`
- `views/graph.md`
- `views/review.md`

Static HTML is stdlib-only and local-file friendly:
- `views/site/index.html`
- `views/site/pages.html`
- `views/site/sources/index.html`
- `views/site/assets/style.css`

Control artifacts:
- `.wikify/views/last-views.json`
- `.wikify/views/view-manifest.json`
- `.wikify/queues/view-tasks.json`

Useful options:

```bash
wikify views --dry-run
wikify views --no-html
wikify views --section sources
```

`--dry-run` reports planned Markdown and HTML paths, counts, warnings, conflicts, and next actions without writing files. Non-dry-run validates object artifacts before rendering; hard validation errors return exit code `2` with `views_validation_failed`.

Generated Markdown views are hash guarded through `.wikify/views/view-manifest.json`. If a generated view was edited by a person or agent, Wikify preserves the edit, skips that path, returns `completed_with_conflicts`, and writes a non-interrupting task to `.wikify/queues/view-tasks.json`.

`wikify views` does not run `sync`, `wikiize`, `graph`, providers, external agents, repository commands, network fetchers, or background watchers. Missing optional graph, topic, project, person, decision, citation, timeline, and task artifacts produce honest empty-state views or warnings instead of invented content.

## Wiki object model and validation

Phase 24 defines the v0.2 wiki object contract and validation surface. Phase 25 consumes `.wikify/queues/ingest-items.json` through `wikify wikiize` to generate source-backed wiki pages. Phase 26 renders human views from those objects. Agent exports, provider-backed runtime integration, and broad maintenance repair flows remain separate later phases.

Visible object artifacts live under `artifacts/objects/`:
- `artifacts/objects/object-index.json` uses `wikify.object-index.v1`
- `artifacts/objects/validation.json` uses `wikify.object-validation.v1`
- object JSON files can be grouped under directories such as `artifacts/objects/wiki_pages/`

Supported object schemas are `wikify.wiki-page.v1`, `wikify.topic.v1`, `wikify.project.v1`, `wikify.person.v1`, `wikify.decision.v1`, `wikify.timeline-entry.v1`, `wikify.citation.v1`, `wikify.graph-edge.v1`, and `wikify.context-pack.v1`. Object types are `source`, `source_item`, `wiki_page`, `topic`, `project`, `person`, `decision`, `timeline_entry`, `citation`, `graph_edge`, and `context_pack`.

Wiki page objects require `schema_version`, `id`, `type`, `title`, `summary`, `body_path`, `source_refs`, `outbound_links`, `backlinks`, `created_at`, `updated_at`, `confidence`, and `review_status`. `review_status` is one of `generated`, `needs_review`, `approved`, `rejected`, or `stale`. Graph edge provenance uses `EXTRACTED`, `INFERRED`, or `AMBIGUOUS`.

Markdown front matter is a readable metadata mirror for object fields. Wikify supports a bounded subset: scalar values plus JSON-flow arrays/objects. It intentionally does not require full YAML parsing.

Validation commands:

```bash
wikify validate
wikify validate --path <path>
wikify validate --strict
wikify validate --write-report
```

Default validation is compatibility-tolerant: legacy Markdown without object front matter returns warnings and exits `0`. Hard validation failures return exit code `2` with structured records. Each record has `code`, `message`, `path`, `object_id`, `field`, `severity`, and `details`. Stable validation codes include `object_required_field_missing`, `object_duplicate_id`, `object_link_unresolved`, `object_source_ref_unresolved`, `object_frontmatter_invalid`, and `object_schema_invalid`.

Compatibility is preserved: `wikify graph` keeps relative-path node ids while exposing optional object ids, `wikify maintain` keeps its current graph maintenance flow, legacy `fokb` commands still work, and existing sample KB layouts remain readable.

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
