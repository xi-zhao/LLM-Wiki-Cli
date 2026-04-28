---
phase: 05-graph-relevance-scoring
plan: 01
subsystem: graph
tags: [wikify, graph, relevance, maintenance]
provides:
  - Deterministic graph relevance scoring
  - Signal-level relevance evidence
  - Relevance metadata on graph analytics, findings, and tasks
affects: [wikify-graph, wikify-maintain, graph-agent-tasks]
tech-stack:
  added: []
  patterns: [stdlib-graph-scoring, advisory-metadata, unittest]
key-files:
  created:
    - wikify/graph/relevance.py
    - tests/test_graph_relevance.py
  modified:
    - wikify/graph/analytics.py
    - wikify/maintenance/findings.py
    - wikify/maintenance/task_queue.py
    - tests/test_graph_builder.py
    - tests/test_maintenance_findings.py
    - tests/test_maintenance_task_queue.py
    - README.md
    - LLM-Wiki-Cli-README.md
    - scripts/fokb_protocol.md
key-decisions:
  - "Graph relevance is advisory and never triggers automatic content writes."
  - "Signals are direct links, source overlap, common neighbors, and type affinity."
  - "Low-confidence relevance remains informational and does not escalate task priority."
duration: 1-session
completed: 2026-04-28
---

# Phase 5: Graph Relevance Scoring Summary

Wikify now computes explainable graph relevance and carries that evidence into maintenance findings and agent tasks.

## Performance
- **Duration:** 1 session
- **Tasks:** 5 completed
- **Files modified:** 15

## Accomplishments
- Added `wikify.graph.relevance`.
- Added `analytics.relevance` to graph artifacts.
- Added relevance metadata to findings when the finding subject has node relevance.
- Copied finding relevance into graph agent tasks.
- Documented relevance scoring and advisory behavior.

## Task Commits
1. **Phase plan** - `3ff46d7`
2. **Implementation and docs** - `dafe080`

## Files Created/Modified
- `wikify/graph/relevance.py` - Scores pairs with direct links, source overlap, common neighbors, and type affinity.
- `wikify/graph/analytics.py` - Adds relevance to graph analytics.
- `wikify/maintenance/findings.py` - Attaches subject relevance to findings.
- `wikify/maintenance/task_queue.py` - Carries finding relevance into tasks.
- `tests/test_graph_relevance.py` - Covers signal scoring and per-node summaries.
- `README.md`, `LLM-Wiki-Cli-README.md`, `scripts/fokb_protocol.md` - Document relevance contract.

## Verification
- `python3 -m unittest tests.test_graph_relevance tests.test_graph_builder tests.test_maintenance_findings tests.test_maintenance_task_queue -v` passed with 6 tests.
- `python3 -m unittest discover -s tests -v` passed with 143 tests.
- Manual smoke passed:
  - `wikify graph --no-html`
  - `wikify maintain`
  - Verified `graph.analytics.relevance.schema_version == wikify.graph-relevance.v1`.
  - Verified findings/tasks relevance metadata, when present, uses the relevance schema.

## Decisions & Deviations
- GSD SDK remains unavailable in PATH, so GSD files were maintained manually.
- Source overlap uses shared source paths from originating graph edges, avoiding double-counting direct links.
- Relevance does not alter automatic execution policy.

## Next Phase Readiness
Phase 6 should add optional purpose context so proposal rationale can include why a repair matters to the wiki's goals.
