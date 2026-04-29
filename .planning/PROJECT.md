# Wikify

## What This Is

Wikify is a CLI-first personal knowledge base generator and maintenance tool. It turns scattered files, directories, URLs, repositories, notes, and other source material into an incremental local wiki that is useful to both humans and agents.

The generated wiki is the product artifact: readable and navigable for people, while exposing stable machine interfaces that coding and research agents can query, cite, and use as durable context.

## Core Value

Users can turn scattered personal and project knowledge into a living local wiki that people can browse and agents can reliably call.

## Current State

**Shipped milestone:** v0.1.0a2 Agentic Maintenance Automation (2026-04-29)

Wikify has a complete CLI-first agent maintenance loop: graph findings become task artifacts, tasks produce scoped proposals, explicit external producer commands generate deterministic patch bundles, verifier agents can block unsafe bundles, and rejected bundles can be repaired with durable feedback.

The product direction for v0.2.0 expands the target object from project Markdown wiki maintenance to a personal knowledge base with first-class human and agent views. Phase 22 shipped the workspace manifest and source registry foundation; Phase 23 shipped deterministic incremental sync and ingest queue artifacts; Phase 24 shipped the canonical wiki object model, Markdown front matter metadata bridge, structured object validation, graph object-id compatibility, and `wikify validate`.

## Current Milestone: v0.2.0 Personal Wiki Core & Views

**Goal:** Build the core personal wiki object model, ingest flow, human-facing generated views, and agent-facing context interfaces.

**Target features:**
- Source registry for files, directories, URLs, repositories, and notes.
- Incremental ingest and sync artifacts for changed source material.
- Wiki object model for sources, pages, topics, projects, people, decisions, timelines, citations, and context packs.
- Wikiization pipeline that produces source-backed Markdown pages.
- Human wiki views: index pages, source pages, topic pages, recent updates, graph/timeline entry points, and local static output.
- Agent wiki interfaces: `llms.txt`, `llms-full.txt`, `graph.json`, citation index, related-topic queries, and task-specific context packs.
- Maintenance integration so the existing graph task, verifier, and repair loop can improve personal wiki content.

## Requirements

### Validated

- [x] `wikify` is the primary CLI and `fokb` remains a compatibility alias.
- [x] Graph artifacts are generated from compiled Markdown wiki objects.
- [x] `wikify maintain` builds graph artifacts, findings, plan, execution classification, and history without editing content pages.
- [x] `wikify maintain` writes a deterministic graph agent task queue artifact.
- [x] `wikify tasks` lets agents read, filter, and inspect queued graph tasks without mutating task state.
- [x] `wikify propose` generates scoped patch proposal artifacts from one graph agent task without applying edits.
- [x] `wikify tasks` explicit lifecycle actions persist task status and append audit events.
- [x] Graph relevance scoring explains node/task priority with direct links, source overlap, common neighbors, and type affinity.
- [x] Purpose-aware proposals include optional wiki goal context and rationale without weakening path safety.
- [x] `wikify apply` and `wikify rollback` support deterministic agent-generated patch bundles with audit and hash-guarded rollback.
- [x] `wikify run-task` orchestrates proposal, bundle detection, apply, and lifecycle completion with low user interruption.
- [x] `wikify bundle-request` generates a stable agent-facing request artifact for producing explicit patch bundles.
- [x] `wikify run-task` automatically prepares a patch bundle request when no bundle exists.
- [x] `wikify produce-bundle` invokes an explicit external agent command to produce and preflight a patch bundle.
- [x] `wikify run-task --agent-command <command>` can complete request, external bundle production, apply, and lifecycle in one explicit automation flow.
- [x] `wikify run-tasks` can process a bounded batch of selected agent tasks with explicit producer automation and structured per-task results.
- [x] `wikify maintain-run` refreshes maintenance artifacts and advances a bounded queued task batch in one explicit automation flow.
- [x] `wikify agent-profile` stores named external command profiles that automation commands can use explicitly.
- [x] `wikify agent-profile --set-default` lets bare `--agent-profile` resolve a default while preserving explicit execution intent.
- [x] `wikify maintain-loop` repeats bounded maintenance runs until no work remains or a configured stop condition is reached.
- [x] `wikify verify-bundle` lets an explicit verifier agent review patch bundles before apply.
- [x] Verifier rejection blocks the task with durable feedback for later agents to inspect and retry.
- [x] `wikify run-task --agent-command` can repair verifier-blocked tasks by regenerating rejected bundles with feedback.
- [x] `wikify init [BASE]` creates a personal wiki workspace with `wikify.json`, `.wikify/registry/sources.json`, and visible `sources/`, `wiki/`, `artifacts/`, and `views/` directories.
- [x] `wikify source add/list/show` registers and exposes durable source records for files, directories, URLs, repositories, and notes through stable JSON envelopes.
- [x] `wikify sync` discovers registered source items, classifies freshness, writes `.wikify/sync/` status artifacts, and maintains `.wikify/queues/ingest-items.json`.
- [x] `wikify sync --dry-run` previews source item and queue changes without writing sync artifacts or registry metadata.
- [x] URL and remote repository sync remain offline with `network_checked: false`; local repository sync scans files without repository commands.
- [x] Wikify defines canonical object schemas for source, source item, wiki page, topic, project, person, decision, timeline entry, citation, graph edge, and context pack objects.
- [x] Wiki page objects include stable ids, titles, summaries, body paths, source references, links, timestamps, confidence, and review status.
- [x] Markdown front matter can expose object metadata using the supported scalar and JSON-flow subset.
- [x] JSON object artifacts live under visible `artifacts/objects/` product output paths.
- [x] `wikify validate` returns `wikify.object-validation.v1` records for missing fields, duplicate ids, unresolved links/source refs, invalid schema fields, and malformed front matter.
- [x] `wikify graph` preserves path-based node ids while exposing canonical object ids as additive metadata.

### Active

- [ ] Source-backed wikiization pipeline.
- [ ] Generated human wiki views and local static browsing.
- [ ] Agent context exports and query commands.
- [ ] Maintenance-loop integration for the personal wiki model.

### Out of Scope

- Hidden LLM calls inside the CLI - provider/key/retry semantics should be explicit in a later milestone.
- Obsidian or Notion replacement features - Wikify produces and maintains a wiki, but does not become a full manual note-taking app.
- Chat-first RAG UI - agent access should be command/artifact driven before chat workflows are considered.
- Desktop/Tauri UI parity with `llm_wiki` - local static output is enough for v0.2.0.
- Public cloud sync, account systems, or hosted sharing - v0.2.0 is local-first.
- Vector database dependency - relevance should start from deterministic indexes and graph artifacts.
- Copying GPLv3 code from `nashsu/llm_wiki` - only product ideas and architecture lessons may be borrowed.
- Selling audit logs or rollback as the headline value - they remain trust infrastructure behind safe automation.

## Context

- Python 3.10+ package using stdlib, `argparse`, and `unittest`.
- Tests are run with `python3 -m unittest discover -s tests -v`; `pytest` is not installed locally.
- Current maintenance modules live in `wikify/maintenance/`.
- Current graph modules live in `wikify/graph/`.
- Existing docs: `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md`, and `AGENTS.md`.
- `gsd-sdk` is not available in PATH in this environment, so GSD artifacts are maintained manually while preserving the workflow structure.
- v0.2.0 should absorb Graphify as graph intelligence and LLM Wiki as wikiization/ingest inspiration without cloning either product.

## Constraints

- **Runtime**: Keep the implementation stdlib-only unless a future phase justifies a dependency.
- **Compatibility**: `fokb` compatibility must not be broken while `wikify` becomes the preferred surface.
- **Source of truth**: Human views and agent views must be generated from the same wiki model.
- **Local-first**: v0.2.0 should work without accounts, hosted services, or mandatory provider credentials.
- **Automation**: Outputs should be machine-readable JSON envelopes and artifacts, not prose-only stdout.
- **Display**: The wiki must be a human-facing result, not only an agent backend.
- **Testing**: New behavior must be covered by `unittest` with red/green verification where practical.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `wikify maintain` as the autonomous loop entrypoint | Keeps graph maintenance separate from legacy incremental `maintenance` history query | Good |
| Queue semantic/content actions instead of executing them silently | Prevents silent content damage while still enabling autonomous follow-up | Good |
| Add GSD `.planning` for future work | User requested GSD implementation discipline | Active |
| Learn from `nashsu/llm_wiki` without copying code | Its GPLv3 license conflicts with Wikify's MIT direction, but product patterns are useful | Good |
| Require structured patch bundles for apply | Agents may generate patch content, but CLI applies only deterministic, scoped operations with rollback evidence | Good |
| Add external agent adapter before provider SDKs | A command adapter lets users bring Codex, Claude, OpenClaw, or other agents explicitly while Wikify keeps audit and validation boundaries | Good |
| Verifier gate runs before apply | Agent review should block unsafe bundles before content mutation while keeping user interruption low | Good |
| Repair rejected bundles before provider SDKs | Feedback-fed repair improves automation while preserving explicit external command boundaries | Good |
| Treat the generated wiki as the product artifact | Human readability matters because the knowledge base is an outcome, not only internal agent context | Active |
| Keep human and agent views on one source of truth | Separate stores would create drift and make generated knowledge harder to trust | Active |
| Position v0.2.0 around personal knowledge, not only project knowledge | Project wiki generation is a use case; the broader product is a personal agent-callable wiki | Active |
| Keep CLI-first control while adding human-facing views | The CLI is the operation surface, but `wikify open`/static output should make the result inspectable | Active |
| Treat audit and rollback as trust infrastructure, not the headline promise | Users care about safe automation and recoverability, not internal control-plane terminology | Active |
| Keep source registration shallow in Phase 22 | `source add` should only record durable source identity and bounded offline metadata; sync/wikiization/views stay explicit later commands | Good |
| Keep Phase 23 sync offline and artifact-first | `sync` should classify freshness and prepare queue work without hidden network, repository, provider, ingest, wikiization, view, or agent export side effects | Good |
| Keep Phase 24 object contracts artifact-first | Object JSON and Markdown metadata should define/validate the wiki model without consuming queues or generating pages before Phase 25 | Good |
| Preserve graph path ids while exposing object ids | Existing graph/maintenance compatibility matters; canonical ids can be additive until generated pages are migrated | Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? Move to Out of Scope with reason.
2. Requirements validated? Move to Validated with phase reference.
3. New requirements emerged? Add to Active.
4. Decisions to log? Add to Key Decisions.
5. "What This Is" still accurate? Update if drifted.

**After each milestone**:
1. Full review of all sections.
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state.

---
*Last updated: 2026-04-29 after completing Phase 24*
