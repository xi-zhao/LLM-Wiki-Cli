# Wikify

## What This Is

Wikify is an agent-facing Markdown knowledge base control CLI. It gives agents stable JSON commands for ingest, maintenance, decision, execution, and graph understanding while keeping Markdown as the human-readable source of truth.

The current product direction fuses LLM Wiki-style markdown-first knowledge management with Graphify-style structural insight, then turns graph findings into autonomous maintenance work that can survive messy agent-written code.

## Core Value

Agents can maintain and improve a local Markdown wiki through deterministic, auditable command outputs without repeatedly interrupting the user.

## Requirements

### Validated

- ✓ `wikify` is the primary CLI and `fokb` remains a compatibility alias.
- ✓ Graph artifacts are generated from compiled Markdown wiki objects.
- ✓ `wikify maintain` builds graph artifacts, findings, plan, execution classification, and history without editing content pages.

### Active

- [ ] Add a graph agent task queue so queued maintenance work becomes directly consumable by a later agent pass.
- [ ] Preserve V1 safety: no content-page edits from `wikify maintain`.
- [ ] Keep all task artifacts deterministic JSON with enough evidence for automation.

### Out of Scope

- Hidden LLM calls inside the CLI — provider/key/retry semantics should be explicit in a later phase.
- Automatic content rewrites during `wikify maintain` V1 — semantic repairs require a separate agent consumer.
- Interactive user approval during maintenance runs — unsafe work should be queued, not prompted.

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
| Add GSD `.planning` for future work | User requested GSD implementation discipline | — Pending |

---
*Last updated: 2026-04-28 after GSD initialization*
