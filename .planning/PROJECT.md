# Wikify

## What This Is

Wikify is an agent-facing Markdown knowledge base control CLI. It gives agents stable JSON commands for ingest, maintenance, decision, execution, and graph understanding while keeping Markdown as the human-readable source of truth.

The current product direction fuses LLM Wiki-style markdown-first knowledge management with Graphify-style structural insight, then turns graph findings into autonomous maintenance work that can survive messy agent-written code.

## Core Value

Agents can maintain and improve a local Markdown wiki through deterministic, auditable command outputs without repeatedly interrupting the user.

## Current State

**Shipped milestone:** v0.1.0a2 Agentic Maintenance Automation (2026-04-29)

Wikify now has a complete CLI-first agent maintenance loop: graph findings become task artifacts, tasks produce scoped proposals, explicit external producer commands generate deterministic patch bundles, verifier agents can block unsafe bundles, and rejected bundles can be repaired with durable feedback. The milestone audit passed with 20 standalone phase verification artifacts for phases 1-20 plus Phase 21 closure metadata.

## Next Milestone Goals

- Decide whether the next milestone should focus on provider-backed semantic generation, release packaging, or a narrower hardening pass.
- Define fresh requirements before implementation; `.planning/REQUIREMENTS.md` is intentionally removed during milestone close and should be recreated by `$gsd-new-milestone`.
- Preserve the existing explicit-agent boundary unless a future requirements phase deliberately designs provider/key/retry semantics.


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

### Out of Scope

- Hidden LLM calls inside the CLI — provider/key/retry semantics should be explicit in a later phase.
- Hidden content generation during `wikify maintain` V1 — semantic repairs require explicit patch bundles and audit records.
- Interactive user approval during maintenance runs — unsafe work should be queued, not prompted.
- Copying GPLv3 code from `nashsu/llm_wiki`; only product ideas and architecture lessons may be borrowed.
- Desktop/Tauri UI work from `llm_wiki`; Wikify remains a CLI-first agent surface.
- Provider-backed semantic patch generation before explicit provider/key/retry semantics are designed and tested.

## Context

- Python 3.10+ package using stdlib, `argparse`, and `unittest`.
- Tests are run with `python3 -m unittest discover -s tests -v`; `pytest` is not installed locally.
- Current maintenance modules live in `wikify/maintenance/`.
- Current graph modules live in `wikify/graph/`.
- Existing docs: `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md`.

## Constraints

- **Runtime**: stdlib-only implementation unless a future requirement justifies dependencies.
- **Compatibility**: `fokb` compatibility must not be broken while `wikify` becomes the preferred surface.
- **Safety**: Graph maintenance may write audit artifacts but must not rewrite topic, parsed, source, or sorted content pages in V1.
- **Automation**: Outputs should be machine-readable JSON envelopes and artifacts, not prose-only stdout.
- **Testing**: New behavior must be covered by `unittest` with red/green verification where practical.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `wikify maintain` as the autonomous loop entrypoint | Keeps graph maintenance separate from legacy incremental `maintenance` history query | ✓ Good |
| Queue semantic/content actions instead of executing them in V1 | Prevents silent content damage while still enabling autonomous follow-up | ✓ Good |
| Add GSD `.planning` for future work | User requested GSD implementation discipline | ✓ Active |
| Learn from `nashsu/llm_wiki` without copying code | Its GPLv3 license conflicts with Wikify's MIT direction, but product patterns are useful | ✓ Good |
| Sequence proposal before lifecycle and apply | Agents need auditable proposals before state mutation or content mutation becomes useful | ✓ Good |
| Keep relevance scoring advisory first | Scores should improve prioritization before they drive automatic writes | ✓ Good |
| Keep patch proposals read-only | Lets agents review planned edits while preserving V1 no-content-mutation safety | ✓ Good |
| Make lifecycle mutation explicit | Default task reads stay safe while `--mark-*`, `--retry`, `--restore`, and `--cancel` provide durable automation state | ✓ Good |
| Keep graph relevance advisory | Relevance improves explanation and prioritization without becoming an automatic write trigger | ✓ Good |
| Keep purpose context explanatory | Purpose files should enrich proposal rationale, not expand write scope or apply content changes | ✓ Good |
| Require structured patch bundles for apply | Agents may generate patch content, but CLI applies only deterministic, scoped operations with rollback evidence | ✓ Good |
| Stop at missing patch bundles | Workflow automation should return an agent action instead of prompting the user or inventing content | ✓ Good |
| Generate patch bundle requests before provider execution | A stable request artifact lets any external agent generate bundle content without hidden CLI LLM calls | ✓ Good |
| Let runner prepare bundle requests | The main workflow should create the agent handoff artifact automatically when it reaches `waiting_for_patch_bundle` | ✓ Good |
| Add external agent adapter before provider SDKs | A command adapter lets users bring Codex/Claude/other agents explicitly while Wikify keeps audit and validation boundaries | ✓ Good |
| Let run-task compose producer automation only when explicitly commanded | One-command automation should reduce orchestration without hiding provider execution or changing safety boundaries | ✓ Good |
| Batch automation must be bounded and sequential first | Limit and stop-on-error defaults reduce blast radius before any concurrent or provider-backed execution exists | ✓ Good |
| Maintenance run automation composes existing primitives | The low-interruption entrypoint should refresh maintenance and run bounded batches without hidden provider behavior or new apply semantics | ✓ Good |
| Agent profiles are aliases, not providers | Reduces repeated command input while keeping provider/model/key/retry behavior outside hidden Wikify defaults | ✓ Good |
| Default profiles require explicit flags | A default profile reduces typing only when `--agent-profile` is present; it must not silently trigger external execution | ✓ Good |
| Maintenance loop composes maintain-run | Repeating the audited primitive keeps automation useful without broadening patch or provider semantics | ✓ Good |
| Verifier gate runs before apply | Agent review should block unsafe bundles before content mutation while keeping user interruption low | ✓ Good |
| Verifier rejection becomes task feedback | Automation should leave actionable state, not only transient errors | ✓ Good |
| Repair rejected bundles before provider SDKs | Feedback-fed repair improves automation while preserving explicit external command boundaries | ✓ Good |

---
*Last updated: 2026-04-29 after v0.1.0a2 milestone completion*
