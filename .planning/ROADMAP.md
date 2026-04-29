# Roadmap: Wikify

## Milestones

- [x] **v0.1.0a2 Agentic Maintenance Automation** - Phases 1-21 shipped 2026-04-29. Archive: `.planning/milestones/v0.1.0a2-ROADMAP.md`
- [ ] **v0.2.0 Personal Wiki Core & Views** - Phases 22-28 planned 2026-04-29.

## Current Roadmap

### Milestone Goal

Build the core personal wiki object model, ingest flow, human-facing generated views, and agent-facing context interfaces.

### Phase 22: Personal Wiki Workspace And Source Registry

**Status:** Complete 2026-04-29

**Goal:** Add the workspace and source registry foundation for personal knowledge sources.

**Requirements:** SRC-01, SRC-02, SRC-03, SRC-04

**Success Criteria:**
1. User can initialize a personal wiki workspace with explicit locations for sources, wiki pages, artifacts, and views.
2. User can register files, directories, URLs, repositories, and Markdown note paths as durable sources.
3. Source registry artifacts include stable ids, source types, locators, fingerprint metadata, status, timestamps, and errors.
4. `wikify` returns stable JSON for source list/inspect commands.
5. Existing `wikify` and `fokb` entrypoints remain compatible.

**Dependencies:** None.

**Verification:** Unit tests for source registration, registry persistence, duplicate handling, source inspection JSON, and compatibility entrypoints.

**Plans:**
- [x] **22-01 Build Personal Wiki Workspace And Source Registry** - Implement `wikify init`, `wikify source add/list/show`, workspace manifest persistence, and canonical source registry persistence.

**Wave 1:** 22-01 can run independently.

**Cross-cutting constraints:**
- No hidden network, provider, sync, wikiization, view generation, or agent export behavior in Phase 22.
- Source identity must use opaque immutable ids, with duplicate detection through `locator_key`.
- Human-visible workspace outputs and internal `.wikify/` control state must remain separate.

### Phase 23: Incremental Sync And Ingest Queue

**Status:** Planned; ready to execute

**Goal:** Detect source changes and produce deterministic ingest queue/status artifacts.

**Requirements:** ING-01, ING-02, ING-03, ING-04

**Success Criteria:**
1. User can sync registered sources and classify source items as new, changed, missing, unchanged, skipped, or errored.
2. Sync creates queue/status artifacts for pending wikiization work.
3. Dry-run sync reports planned changes without writing artifacts.
4. Repeated syncs are stable when source content has not changed.
5. Errors are recorded per source item without aborting unrelated sources.

**Dependencies:** Phase 22.

**Verification:** Unit tests for file, directory, URL metadata, repository path, dry-run, unchanged repeat sync, missing source handling, and queue artifact shape.

**Plans:**
- [ ] **23-01 Build Incremental Sync And Ingest Queue** - Implement `wikify sync`, source item discovery/classification, source item index, sync report, ingest queue artifact, registry sync metadata, docs, and verification.

**Wave 1:** 23-01 can run independently after Phase 22.

**Cross-cutting constraints:**
- Sync must not fetch URLs, clone repositories, call providers, run `wikify ingest`, generate wiki pages, generate views, build graph artifacts, or export agent context.
- Sync artifacts are internal control-plane state under `.wikify/sync/` and `.wikify/queues/`.
- Source item identity must be deterministic so repeated syncs are stable and queue entries do not duplicate.

### Phase 24: Wiki Object Model And Validation

**Goal:** Define the canonical object model shared by human views, agent interfaces, graph extraction, and maintenance.

**Requirements:** OBJ-01, OBJ-02, OBJ-03, OBJ-04

**Success Criteria:**
1. Schemas exist for source, source item, wiki page, topic, project, person, decision, timeline entry, citation, graph edge, and context pack objects.
2. Wiki pages can carry required metadata as JSON artifacts and Markdown front matter.
3. Validation catches missing required fields, invalid links, duplicate ids, and unresolved source references.
4. Validation returns structured JSON errors suitable for agent consumption.
5. Existing graph builders can be pointed at the model without requiring content mutation.

**Dependencies:** Phase 22, Phase 23.

**Verification:** Unit tests for schema constructors/parsers, Markdown front matter round trips, object validation, invalid artifact reporting, and graph integration smoke tests.

### Phase 25: Source-Backed Wikiization Pipeline

**Goal:** Convert ingested source items into structured, source-backed Markdown wiki pages.

**Requirements:** WIK-01, WIK-02, WIK-03, WIK-04, WIK-05

**Success Criteria:**
1. User can run a wikiization command that processes queued source items into generated wiki pages.
2. Generated pages include source references for summaries, extracted claims, and relationships.
3. Incremental wikiization updates generated pages without overwriting user-edited content outside explicit patch/apply flow.
4. Ambiguous, conflicting, or low-confidence transformations create review/maintenance tasks.
5. External semantic enrichment uses explicit request/proposal/bundle artifacts rather than hidden provider calls.

**Dependencies:** Phase 22, Phase 23, Phase 24.

**Verification:** Unit tests for page generation, source traceability, incremental updates, user-edit protection, review task creation, and external agent handoff artifacts.

### Phase 26: Human Wiki Views And Local Static Output

**Goal:** Make the generated knowledge base readable and navigable for people.

**Requirements:** VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05

**Success Criteria:**
1. Wikify generates a human-facing wiki home page with recent updates, core topics, source groups, and entry points.
2. Wikify generates source pages showing source status, contributed pages, citations, and unresolved issues.
3. Wikify generates topic, project, person, and decision pages with summaries, related pages, and source-backed references.
4. Wikify generates local static HTML using stdlib-compatible rendering.
5. Human views include graph and timeline entry points derived from the same wiki object model.

**Dependencies:** Phase 24, Phase 25.

**Verification:** Unit tests for Markdown view generation, HTML output, navigation links, source pages, topic pages, graph/timeline entry files, and missing-data behavior.

### Phase 27: Agent Wiki Interfaces And Context Packs

**Goal:** Expose the personal wiki as stable machine-readable context for agents.

**Requirements:** AGT-01, AGT-02, AGT-03, AGT-04, AGT-05

**Success Criteria:**
1. Wikify exports `llms.txt` and `llms-full.txt` from the wiki object model.
2. Wikify exports `graph.json`, citation index, and page index artifacts.
3. Agent can request a task-specific context pack with relevant pages, citations, and graph neighbors within a size budget.
4. Agent can query source-backed citations for a topic or claim.
5. Agent can query related topics/pages with ranking explanations.

**Dependencies:** Phase 24, Phase 25, Phase 26.

**Verification:** Unit tests for llms exports, graph/citation/page indexes, context-pack budgeting, cite query output, related query ranking, and JSON envelope stability.

### Phase 28: Maintenance Integration And Compatibility

**Goal:** Connect the v0.2.0 personal wiki model to the existing graph task, verifier, repair, and compatibility flows.

**Requirements:** MAINT-01, MAINT-02, MAINT-03, MAINT-04

**Success Criteria:**
1. Existing graph maintenance can read the v0.2.0 wiki object model.
2. Maintenance findings can target personal wiki pages, source pages, human views, and agent exports.
3. Verifier and repair flows preserve source references and review status when updating generated wiki pages.
4. v0.1.0a2 commands remain compatible unless explicitly deprecated.
5. End-to-end local workflow works: add source -> sync -> wikiize -> view -> agent context -> maintenance task.

**Dependencies:** Phase 22, Phase 23, Phase 24, Phase 25, Phase 26, Phase 27.

**Verification:** Unit tests and an integration-style fixture covering source add, sync, wikiize, view generation, agent export, graph maintenance, verifier rejection, and repair feedback.

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRC-01 | Phase 22 | Complete |
| SRC-02 | Phase 22 | Complete |
| SRC-03 | Phase 22 | Complete |
| SRC-04 | Phase 22 | Complete |
| ING-01 | Phase 23 | Pending |
| ING-02 | Phase 23 | Pending |
| ING-03 | Phase 23 | Pending |
| ING-04 | Phase 23 | Pending |
| OBJ-01 | Phase 24 | Pending |
| OBJ-02 | Phase 24 | Pending |
| OBJ-03 | Phase 24 | Pending |
| OBJ-04 | Phase 24 | Pending |
| WIK-01 | Phase 25 | Pending |
| WIK-02 | Phase 25 | Pending |
| WIK-03 | Phase 25 | Pending |
| WIK-04 | Phase 25 | Pending |
| WIK-05 | Phase 25 | Pending |
| VIEW-01 | Phase 26 | Pending |
| VIEW-02 | Phase 26 | Pending |
| VIEW-03 | Phase 26 | Pending |
| VIEW-04 | Phase 26 | Pending |
| VIEW-05 | Phase 26 | Pending |
| AGT-01 | Phase 27 | Pending |
| AGT-02 | Phase 27 | Pending |
| AGT-03 | Phase 27 | Pending |
| AGT-04 | Phase 27 | Pending |
| AGT-05 | Phase 27 | Pending |
| MAINT-01 | Phase 28 | Pending |
| MAINT-02 | Phase 28 | Pending |
| MAINT-03 | Phase 28 | Pending |
| MAINT-04 | Phase 28 | Pending |

**Coverage:** 31/31 v0.2.0 requirements mapped.

## Archived Phase History

Detailed phase plans, summaries, and verification artifacts from v0.1.0a2 remain in `.planning/phases/` for local execution history. Milestone-level roadmap and requirements archives live in `.planning/milestones/`.

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
| v0.2.0 Personal Wiki Core & Views | 22-28 | 1/7 | In Progress | — |
