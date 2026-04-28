# Wikify

## What This Is

Wikify is an agent-facing Markdown knowledge base control CLI. It gives agents stable JSON commands for ingest, maintenance, decision, execution, and graph understanding while keeping Markdown as the human-readable source of truth.

The current product direction fuses LLM Wiki-style markdown-first knowledge management with Graphify-style structural insight, then turns graph findings into autonomous maintenance work that can survive messy agent-written code.

## Core Value

Agents can maintain and improve a local Markdown wiki through deterministic, auditable command outputs without repeatedly interrupting the user.

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

---
*Last updated: 2026-04-28 after Phase 8 completion*
