# Requirements: Wikify

**Defined:** 2026-04-29
**Milestone:** v0.2.0 Personal Wiki Core & Views
**Core Value:** Users can turn scattered personal and project knowledge into a living local wiki that people can browse and agents can reliably call.

## v0.2.0 Requirements

### Source Registry

- [x] **SRC-01**: User can initialize a personal wiki workspace with explicit source, wiki, artifact, and view locations.
- [x] **SRC-02**: User can register files, directories, URLs, repositories, and note-like Markdown paths as durable sources.
- [x] **SRC-03**: Each registered source records a stable source id, type, locator, fingerprint metadata, discovery status, last sync status, timestamps, and errors.
- [x] **SRC-04**: User and agent can list and inspect registered sources through stable JSON CLI output.

### Incremental Ingest

- [x] **ING-01**: User can run a sync command that detects new, changed, missing, and unchanged source items without reprocessing unchanged items.
- [x] **ING-02**: Sync writes deterministic queue/status artifacts for discovered source items, skipped items, errors, and pending wikiization work.
- [x] **ING-03**: Sync supports a dry-run mode that reports planned registry and queue changes without writing artifacts.
- [x] **ING-04**: Source item freshness is determined from deterministic fingerprints and local metadata so repeated syncs are stable.

### Wiki Object Model

- [ ] **OBJ-01**: Wikify defines canonical schemas for source, source item, wiki page, topic, project, person, decision, timeline entry, citation, graph edge, and context pack objects.
- [ ] **OBJ-02**: Wiki pages include page id, type, title, summary, body path, source references, outbound links, backlinks, timestamps, confidence, and review status.
- [ ] **OBJ-03**: Wiki object metadata is available as both machine-readable JSON artifacts and Markdown front matter where applicable.
- [ ] **OBJ-04**: Wikify can validate wiki object artifacts and return structured errors for missing required fields, invalid links, or unresolved source references.

### Wikiization Pipeline

- [ ] **WIK-01**: User can run a wikiization command that turns ingested source items into structured Markdown wiki pages.
- [ ] **WIK-02**: Generated pages preserve source traceability for summaries, claims, and extracted relationships.
- [ ] **WIK-03**: Wikiization updates existing generated pages incrementally and avoids overwriting user-edited content without explicit patch/apply flow.
- [ ] **WIK-04**: Low-confidence, conflicting, or ambiguous transformations create review/maintenance tasks instead of silently merging questionable content.
- [ ] **WIK-05**: Semantic enrichment that requires an external agent uses explicit request/proposal/bundle artifacts rather than hidden provider calls.

### Human Wiki Views

- [ ] **VIEW-01**: User can generate a human-facing wiki home page with recent updates, core topics, source groups, and recommended entry points.
- [ ] **VIEW-02**: User can browse generated source pages that show each source's status, contributed pages, citations, and unresolved issues.
- [ ] **VIEW-03**: User can browse generated topic, project, person, and decision pages with summaries, related pages, and source-backed references.
- [ ] **VIEW-04**: User can generate local static HTML output for the wiki using stdlib-compatible rendering.
- [ ] **VIEW-05**: Human views include graph and timeline entry points generated from the same wiki object model.

### Agent Wiki Interfaces

- [ ] **AGT-01**: Agent can read `llms.txt` and `llms-full.txt` exports that summarize the wiki structure and important entry points.
- [ ] **AGT-02**: Agent can read `graph.json`, citation index, and page index artifacts generated from the wiki object model.
- [ ] **AGT-03**: Agent can request a task-specific context pack that selects relevant pages, source references, and graph neighbors within a size budget.
- [ ] **AGT-04**: Agent can query citations for a topic or claim and receive source-backed references with stable ids.
- [ ] **AGT-05**: Agent can query related topics/pages and receive ranked relationships with explanations.

### Maintenance Integration

- [ ] **MAINT-01**: Existing graph maintenance can read the v0.2.0 wiki object model instead of assuming project-only topic layouts.
- [ ] **MAINT-02**: Maintenance findings can target personal wiki pages, source pages, human views, and agent exports.
- [ ] **MAINT-03**: Verifier and repair flows preserve source references and review status when updating generated wiki pages.
- [ ] **MAINT-04**: Existing v0.1.0a2 commands remain compatible while v0.2.0 adds personal wiki concepts.

## Future Requirements

### Provider Runtime

- **PROV-01**: Wikify can call configured model providers directly with explicit keys, retries, budgets, and audit records.
- **PROV-02**: Provider-backed wikiization can enrich pages without requiring a separate external agent command.

### Search And Retrieval

- **RET-01**: Wikify can build optional semantic embeddings for local retrieval.
- **RET-02**: Wikify can rank results with hybrid graph, text, citation, and embedding signals.

### Sharing And UI

- **SHARE-01**: User can publish selected wiki views to a remote or hosted location.
- **UI-01**: User can use a richer desktop or web app for manual browsing and editing.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hidden LLM calls | v0.2.0 must preserve explicit agent/provider boundaries. |
| Obsidian or Notion replacement | Wikify should generate and maintain a wiki, not become a full manual note app. |
| Chat-first RAG UI | The primary interface remains CLI commands and artifacts. |
| Public cloud sync/accounts | v0.2.0 is local-first and should not require hosted infrastructure. |
| Mandatory vector database | Deterministic indexes and graph artifacts should come first. |
| Desktop/Tauri clone of LLM Wiki | Human display can start with generated Markdown/static HTML. |
| GPL code reuse from `nashsu/llm_wiki` | Product ideas are allowed; incompatible implementation code is not. |

## Traceability

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

**Coverage:**
- v0.2.0 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-04-29*
*Last updated: 2026-04-29 after completing Phase 22*
