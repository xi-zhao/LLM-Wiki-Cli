# Wikify

## What This Is

Wikify is a CLI-first personal knowledge base generator and maintenance tool. It turns scattered files, directories, URLs, repositories, notes, and other source material into an incremental local wiki that is useful to both humans and agents.

The generated wiki is the product artifact: readable and navigable for people, while exposing stable machine interfaces that coding and research agents can query, cite, and use as durable context.

## Core Value

Users can turn scattered personal and project knowledge into a living local wiki that people can browse and agents can reliably call.

## Current State

**Shipped milestone:** v0.2.0 Personal Wiki Core & Views (2026-04-30)

Wikify now has the core personal wiki loop: users can initialize a wiki workspace, register sources, sync changed local material into deterministic queues, wikiize source items into source-backed pages, generate human-facing Markdown/static views, export agent context, and run object-aware maintenance without creating a second knowledge store.

The v0.1.0a2 maintenance loop remains compatible: graph findings still become task artifacts, tasks still produce scoped proposals and explicit patch bundles, verifier gates still block unsafe changes, and repair feedback remains durable. v0.2.0 extends that foundation to personal knowledge sources and shared human/agent wiki artifacts.

## Current Milestone: v0.3.0 Trusted Agent Ingest Experience

**Goal:** Make Wikify feel like the knowledge base operating system for trusted agents. Humans ask agents to save or organize knowledge; agents call Wikify to capture sources, prepare context, update the wiki, validate outputs, and report the final knowledge changes.

**Completed slice:**
- Phase 29: Trusted Agent Ingest Handoff.
- Phase 30: Trusted Agent Operation Snapshots.

**Candidate later slices:**
- Provider runtime for explicit model calls, budgets, retries, and audit records.
- Search and retrieval improvements such as hybrid ranking or optional embeddings.
- Richer review/maintenance ergonomics for generated pages, source issues, and agent context quality.

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
- [x] `wikify wikiize` turns queued local text/Markdown source items into source-backed generated pages under `wiki/pages/` and `wikify.wiki-page.v1` objects under `artifacts/objects/wiki_pages/`.
- [x] Generated wiki pages preserve source refs with source id, item id, locator/path evidence, fingerprint evidence, confidence, and front matter metadata.
- [x] Wikiization updates generated pages only when stored generated hashes prove it is safe, and turns user-edited drift into review tasks.
- [x] Remote-without-content, unsupported, ambiguous, or failed wikiization work creates `.wikify/queues/wikiization-tasks.json` instead of fake pages.
- [x] External semantic enrichment for wikiization uses explicit `wikify.wikiization-request.v1` and `wikify.wikiization-result.v1` artifacts through `--agent-command` or `--agent-profile`.
- [x] `wikify views` renders human-facing Markdown views for home, pages, sources, collections, timeline, graph, and review from object/source/control artifacts.
- [x] `wikify views` produces local static HTML under `views/site/` with stdlib-only rendering and no server or external assets.
- [x] Generated view Markdown is hash-guarded through `.wikify/views/view-manifest.json`, with drift converted into `.wikify/queues/view-tasks.json`.
- [x] `wikify agent export` writes `llms.txt`, `llms-full.txt`, page/citation/related indexes, an agent graph export, and `.wikify/agent/last-agent-export.json`.
- [x] `wikify agent context` writes deterministic, budgeted, source-backed `wikify.context-pack.v1` context packs and matching context pack objects.
- [x] `wikify agent cite` returns explicit citation evidence before page source-ref fallback evidence and returns empty evidence rather than fabricated citations.
- [x] `wikify agent related` returns ranked related objects with signal-level explanations.
- [x] `wikify maintain` can read v0.2 object, source, page, validation, wikiization, human view, and agent export artifacts through an additive target resolver.
- [x] Maintenance findings can target personal wiki pages, generated page drift, validation records, human view regeneration, and agent export refresh work.
- [x] Generated page repair proposals, bundle requests, verifier preflight, and apply preflight preserve `source_refs` and `review_status` deterministically.
- [x] v0.1.0a2 maintenance commands, `sorted/graph-*` artifact paths, JSON envelopes, and `wikify.graph-agent-tasks.v1` task fields remain compatible.

- [x] Trusted agents can explicitly begin, complete, and rollback broad wiki operations with content snapshots and hash guards.
- [x] `wikify ingest` writes a trusted-agent handoff request that includes source metadata, content pointers, workspace context, full-control permissions, recovery instructions, high-quality page standards, and a completion summary contract.
- [x] Product docs frame normal use as humans asking agents to save or organize knowledge, with `wikify ingest` as the agent-facing tool call.
- [x] Ingest completion returns an agent-friendly summary that can be translated into a human-facing knowledge-base change report.

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
- v0.2.0 absorbed Graphify as graph intelligence and LLM Wiki as wikiization/ingest inspiration without cloning either product.

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
| Keep Phase 25 wikiization source-backed and explicit | `wikiize` should make the source-to-page loop real while avoiding hidden fetch/provider behavior and protecting user edits | Good |
| Keep Phase 26 views explicit and artifact-derived | `views` should render existing wiki objects without implicitly running sync, wikiize, graph, providers, agents, or network work | Good |
| Hash-guard generated human views | Visible wiki pages may be edited by people or agents, so drift should create repair tasks instead of silent overwrites | Good |
| Keep Phase 27 agent interfaces object-aware and explicit | `wikify agent` should expose durable context without overloading legacy search/query/graph commands or hiding provider behavior | Good |
| Keep context selection deterministic before vectors | Budgeted context packs should be explainable from local objects, source refs, citations, links, and graph signals before optional semantic retrieval is added | Good |
| Keep Phase 28 maintenance object-aware but additive | Maintenance should see the same personal wiki artifacts as human and agent views while preserving legacy graph task compatibility | Good |
| Treat derived views and agent exports as explicit regeneration work | `wikify maintain` should queue `wikify views` and `wikify agent export` work instead of silently patching derived artifacts | Good |
| Preserve generated page traceability locally | `source_refs` and `review_status` must be protected by deterministic preflight, not only by external verifier prompts | Good |
| Treat `wikify ingest` as an agent-facing handoff | Humans should use natural-language save/organize requests; the calling agent uses Wikify to capture source, prepare context, validate, and report final wiki changes | Active |
| Give trusted agents full wiki control with recovery | The product should trust agents to organize pages while Wikify preserves traceability, snapshots, operation records, validation, and rollback paths | Active |
| Use explicit trusted operation snapshots for broad edits | Wikify cannot intercept arbitrary agent file edits, so agents must create begin/complete records around high-blast-radius wiki rewrites | Good |

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
*Last updated: 2026-04-30 after completing Phase 30 trusted operation snapshots*
