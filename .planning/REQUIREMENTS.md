# Requirements: Wikify

**Defined:** 2026-04-30
**Milestone:** v0.3.0 Trusted Agent Ingest Experience
**Core Value:** Humans ask trusted agents to save and organize knowledge; agents use Wikify to create a traceable, recoverable, human-readable wiki.

## v0.3.0 Requirements

### Trusted Agent Ingest

- [x] **TAI-01**: Product documentation describes the primary human experience as natural-language requests to an agent, with `wikify ingest` as the agent-facing tool contract.
- [x] **TAI-02**: `wikify ingest` writes a trusted agent work request artifact for every successful non-dry-run ingest.
- [x] **TAI-03**: The trusted agent work request includes source metadata, cleaned content pointers, workspace context, full-control permission semantics, recovery instructions, and high-quality page standards.
- [x] **TAI-04**: `wikify ingest --dry-run` reports the planned trusted agent request path without writing request or source artifacts.
- [x] **TAI-05**: `wikify ingest` returns a completion summary that helps the calling agent tell the human what was saved, where the final wiki entry is or will be, and what the agent should do next.
- [x] **TAI-06**: The trusted ingest request and completion behavior are covered by focused unit tests and documented as agent-facing contracts.

### Future Trusted Maintenance

- [ ] **TAI-07**: Broad trusted-agent rewrites, merges, splits, and deletes create operation records and snapshots before mutation.
- [ ] **TAI-08**: Rollback can restore prior wiki content from trusted-agent operation records without manual file reconstruction.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hidden provider execution inside `wikify ingest` | Wikify is the agent tool contract; the calling agent performs semantic judgment. |
| GUI-first save flow | The first target user works through agents and local CLI artifacts. |
| Human approval for every agent decision | The model is trusted-agent autonomy with recovery, not approval-gated editing. |
| Mandatory vector search | Existing deterministic object, source, view, and graph artifacts are enough for this slice. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TAI-01 | Phase 29 | Complete |
| TAI-02 | Phase 29 | Complete |
| TAI-03 | Phase 29 | Complete |
| TAI-04 | Phase 29 | Complete |
| TAI-05 | Phase 29 | Complete |
| TAI-06 | Phase 29 | Complete |
| TAI-07 | Phase 30 | Planned |
| TAI-08 | Phase 30 | Planned |

---
*Requirements defined: 2026-04-30 from `docs/superpowers/specs/2026-04-30-trusted-agent-ingest-experience-design.md`.*
