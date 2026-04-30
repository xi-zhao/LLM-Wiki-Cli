# Roadmap: Wikify

## Milestones

- [x] **v0.1.0a2 Agentic Maintenance Automation** - Phases 1-21 shipped 2026-04-29. Archive: `.planning/milestones/v0.1.0a2-ROADMAP.md`
- [x] **v0.2.0 Personal Wiki Core & Views** - Phases 22-28 shipped 2026-04-30. Archive: `.planning/milestones/v0.2.0-ROADMAP.md`
- [ ] **v0.3.0 Trusted Agent Ingest Experience** - Active. Implements the trusted-agent ingest handoff so humans ask agents to save knowledge and agents use Wikify as the recoverable wiki operating layer.

## Current Roadmap

### v0.3.0 Trusted Agent Ingest Experience

**Goal:** Make `wikify ingest` an agent-facing handoff contract that saves sources, gives trusted agents enough context to organize knowledge, and returns a completion summary suitable for human-facing replies.

- [x] Phase 29: Trusted Agent Ingest Handoff (1/1 plans) - completed 2026-04-30

Future phases may add full trusted-agent operation snapshots and rollback for broad wiki rewrites after the ingest handoff contract is stable.

## Shipped Phase Summary

<details>
<summary>✅ v0.2.0 Personal Wiki Core & Views (Phases 22-28) - SHIPPED 2026-04-30</summary>

- [x] Phase 22: Personal Wiki Workspace And Source Registry (1/1 plans) - completed 2026-04-29
- [x] Phase 23: Incremental Sync And Ingest Queue (1/1 plans) - completed 2026-04-29
- [x] Phase 24: Wiki Object Model And Validation (1/1 plans) - completed 2026-04-29
- [x] Phase 25: Source-Backed Wikiization Pipeline (1/1 plans) - completed 2026-04-29
- [x] Phase 26: Human Wiki Views And Local Static Output (1/1 plans) - completed 2026-04-29
- [x] Phase 27: Agent Wiki Interfaces And Context Packs (3/3 plans) - completed 2026-04-29
- [x] Phase 28: Maintenance Integration And Compatibility (4/4 plans) - completed 2026-04-30

Full phase details are archived in `.planning/milestones/v0.2.0-ROADMAP.md`.

</details>

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRC-01 | Phase 22 | Complete |
| SRC-02 | Phase 22 | Complete |
| SRC-03 | Phase 22 | Complete |
| SRC-04 | Phase 22 | Complete |
| ING-01 | Phase 23 | Complete |
| ING-02 | Phase 23 | Complete |
| ING-03 | Phase 23 | Complete |
| ING-04 | Phase 23 | Complete |
| OBJ-01 | Phase 24 | Complete |
| OBJ-02 | Phase 24 | Complete |
| OBJ-03 | Phase 24 | Complete |
| OBJ-04 | Phase 24 | Complete |
| WIK-01 | Phase 25 | Complete |
| WIK-02 | Phase 25 | Complete |
| WIK-03 | Phase 25 | Complete |
| WIK-04 | Phase 25 | Complete |
| WIK-05 | Phase 25 | Complete |
| VIEW-01 | Phase 26 | Complete |
| VIEW-02 | Phase 26 | Complete |
| VIEW-03 | Phase 26 | Complete |
| VIEW-04 | Phase 26 | Complete |
| VIEW-05 | Phase 26 | Complete |
| AGT-01 | Phase 27 | Complete |
| AGT-02 | Phase 27 | Complete |
| AGT-03 | Phase 27 | Complete |
| AGT-04 | Phase 27 | Complete |
| AGT-05 | Phase 27 | Complete |
| MAINT-01 | Phase 28 | Complete |
| MAINT-02 | Phase 28 | Complete |
| MAINT-03 | Phase 28 | Complete |
| MAINT-04 | Phase 28 | Complete |

**Coverage:** 31/31 v0.2.0 requirements mapped and complete.

Full requirements are archived in `.planning/milestones/v0.2.0-REQUIREMENTS.md`.

## Archived Phase History

Detailed phase plans, summaries, and verification artifacts remain in `.planning/phases/` for local execution history. Milestone-level roadmap and requirements archives live in `.planning/milestones/`.

## Backlog

- Built-in provider-backed patch bundle generation with explicit provider/key/retry semantics.
- Provider-backed semantic task consumer with explicit configuration and audit records.
- Richer multi-operation patch bundles after sequential hash semantics are designed.
- Optional vector/embedding retrieval after deterministic indexes and graph relevance are stable.
- Optional desktop/Tauri UI parity remains out of scope until CLI-generated wiki views stabilize.
- Public publishing or sync after local-first personal wiki workflows are proven.

## Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.1.0a2 Agentic Maintenance Automation | 1-21 | 21/21 | Complete | 2026-04-29 |
| v0.2.0 Personal Wiki Core & Views | 22-28 | 12/12 | Complete | 2026-04-30 |
| v0.3.0 Trusted Agent Ingest Experience | 29 | 1/1 | Active | 2026-04-30 |
