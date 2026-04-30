# Phase 29: Trusted Agent Ingest Handoff - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning
**Source:** `docs/superpowers/specs/2026-04-30-trusted-agent-ingest-experience-design.md`

<domain>
## Phase Boundary

This phase makes `wikify ingest` produce an explicit trusted-agent handoff artifact and agent-friendly completion summary. It does not implement the full future trusted-write snapshot/rollback system for arbitrary wiki rewrites.

</domain>

<decisions>
## Implementation Decisions

### Product Surface
- Humans ask agents to save or organize knowledge through natural language.
- `wikify ingest` is the agent-facing tool call, not the main human mental model.
- Human-facing docs must say people read the final wiki while agents operate Wikify.

### Trusted Agent Model
- The calling agent is trusted to organize the wiki.
- Wikify should give the agent context, permission semantics, page quality standards, and recovery instructions.
- This phase should not add a human approval gate.

### Ingest Contract
- Successful non-dry-run ingest must write a request artifact under `.wikify/ingest/requests/`.
- Dry-run must report the planned request path without writing artifacts.
- The request must include source metadata, content artifact paths, workspace context, permission model, recovery instructions, page standard, and completion summary contract.

### Completion
- `wikify ingest` should return a completion summary suitable for a calling agent to translate into a human message.
- The summary should emphasize saved source, page path or next agent work, related artifacts, and source preservation rather than queue/internal ids.

### the agent's Discretion
- Exact schema name and helper module layout.
- How much workspace context to include in V1 as long as it is deterministic and safe when optional artifacts are missing.

</decisions>

<canonical_refs>
## Canonical References

### Product Design
- `docs/superpowers/specs/2026-04-30-trusted-agent-ingest-experience-design.md` - Defines trusted-agent ingest experience, permission model, page quality, and completion summary.

### Existing Ingest Implementation
- `wikify/ingest/pipeline.py` - Current `run_ingest` orchestration.
- `wikify/ingest/artifacts.py` - Current ingest path helpers and control artifact writers.
- `wikify/cli.py` - Current CLI completion envelope for `wikify ingest`.
- `tests/test_ingest_pipeline.py` - Existing ingest unit tests and best place for focused contract coverage.

### Product Documentation
- `README.md` - English primary docs.
- `LLM-Wiki-Cli-README.md` - Chinese/expanded product docs.
- `scripts/fokb_protocol.md` - Protocol documentation.

</canonical_refs>

<specifics>
## Specific Ideas

- Add schema `wikify.trusted-agent-ingest-request.v1`.
- Add request path `.wikify/ingest/requests/<run-id>.json`.
- Include `trusted_agent.permissions` with read/write/reorganize/delete_merge/repair semantics.
- Include `task.user_intent` as `save_and_organize_personal_wiki`.
- Include a page quality checklist for conclusion, why worth saving, core ideas, reusable insights, related topics, knowledge relationships, and source evidence.
- Include `completion_summary_contract` for added pages, updated pages, related topics, extracted value, source status, warnings, and next steps.

</specifics>

<deferred>
## Deferred Ideas

- Full operation snapshot implementation for arbitrary broad trusted-agent writes.
- Provider-backed model calls from inside `wikify ingest`.
- GUI or browser interaction for save flows.

</deferred>

---

*Phase: 29-trusted-agent-ingest-handoff*
*Context gathered: 2026-04-30 via GSD inline planning*
