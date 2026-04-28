# Wikify Graph Architecture Design

Date: 2026-04-28

## Purpose

`wikify` should become an agent-facing Markdown wiki control plane with a graph intelligence layer. The product should preserve the current LLM-Wiki-Cli strengths: stable JSON envelopes, incremental maintenance, Obsidian-friendly Markdown, and automation-friendly commands. The Graphify fusion should add structural understanding, not a decorative graph export.

The design goal is:

> `wikify` maintains the wiki; `wikify graph` explains the wiki structure.

This avoids turning the project into either a loose script pile or a clone of Graphify. Graphify-style ideas are adopted where they create durable product value: stable graph artifacts, explicit provenance, relationship reports, navigation hints, and future extractor boundaries.

## Non-Goals For V1

- No LLM calls inside `wikify graph`.
- No image/PDF vision extraction in the first graph release.
- No AST parser for code repositories in the first graph release.
- No database or server requirement.
- No fragile natural-language parsing of report text by agents.
- No new behavior hidden inside the existing large `scripts/fokb.py` file.

These can be added later through extractors once the local graph contract is stable.

## Product Surface

The public command becomes:

```bash
wikify ...
```

The old command remains available:

```bash
fokb ...
```

`fokb` is a compatibility alias, not the product name. Documentation should show `wikify` first and mention `fokb` only for migration.

Environment variables:

- `WIKIFY_BASE`: primary knowledge base root.
- `FOKB_BASE`: compatibility fallback.

V1 graph command:

```bash
wikify graph
wikify graph --no-html
wikify graph --scope topics
wikify graph --scope all
```

Default output remains a JSON envelope:

```json
{
  "ok": true,
  "command": "graph",
  "exit_code": 0,
  "result": {
    "artifacts": {
      "json": "/abs/kb/graph/graph.json",
      "html": "/abs/kb/graph/graph.html",
      "report": "/abs/kb/graph/GRAPH_REPORT.md"
    },
    "summary": {
      "node_count": 12,
      "edge_count": 18,
      "community_count": 3,
      "orphan_count": 2
    },
    "completion": {}
  }
}
```

## Architecture

The implementation should move toward a real Python package while keeping current scripts working.

```text
wikify/
  __init__.py
  cli.py                 # argparse only; no business logic
  config.py              # app root, KB base, paths, env compatibility
  envelope.py            # success/error envelope and output rendering
  markdown_index.py      # scans KB markdown objects
  graph/
    __init__.py
    model.py             # dataclasses and JSON schema helpers
    extractors.py        # relationship extraction interfaces
    builder.py           # graph build orchestration
    analytics.py         # degrees, communities, orphan detection
    report.py            # GRAPH_REPORT.md rendering
    html.py              # self-contained graph.html rendering
scripts/
  fokb.py                # compatibility shim, imports wikify.cli
```

V1 may migrate only the parts needed for `wikify graph` plus shared config/envelope if a full migration would create too much churn. The key rule: new graph behavior must live in `wikify/graph/*`, not in the old monolithic script.

### Module Boundaries

- `cli.py` parses arguments and calls command handlers.
- `config.py` owns path discovery and `WIKIFY_BASE` / `FOKB_BASE` compatibility.
- `markdown_index.py` returns normalized wiki objects. It does not compute graph analytics.
- `graph.extractors` turns wiki objects into nodes and edges. It does not write files.
- `graph.builder` assembles graph data and writes artifacts.
- `graph.analytics` computes metrics from graph data only.
- `graph.report` and `graph.html` render existing graph data only.

This keeps future vibe-coded feature additions from becoming a single everything-file. A new capability should usually mean a new extractor or analytics function, not a new pile of conditions in the CLI.

## Data Model

Graph JSON should be stable enough for agents to consume directly.

```json
{
  "schema_version": "wikify.graph.v1",
  "base": "/abs/kb",
  "generated_at": "2026-04-28T00:00:00Z",
  "nodes": [],
  "edges": [],
  "communities": [],
  "analytics": {}
}
```

Node:

```json
{
  "id": "topics/agent-knowledge-loops.md",
  "path": "/abs/kb/topics/agent-knowledge-loops.md",
  "relative_path": "topics/agent-knowledge-loops.md",
  "type": "topics",
  "title": "agent-knowledge-loops",
  "label": "agent-knowledge-loops",
  "tags": [],
  "degree": 3
}
```

Edge:

```json
{
  "source": "topics/agent-knowledge-loops.md",
  "target": "articles/parsed/2026-04-10_agent-knowledge-loops.md",
  "type": "markdown_link",
  "provenance": "EXTRACTED",
  "confidence": 1.0,
  "source_path": "/abs/kb/topics/agent-knowledge-loops.md",
  "line": 22,
  "label": "links_to"
}
```

Allowed provenance values:

- `EXTRACTED`: directly found in Markdown or filesystem structure.
- `INFERRED`: deterministic inference from local structure, never LLM guesswork in V1.
- `AMBIGUOUS`: detected but unresolved relationship, such as a broken wikilink.

V1 relation types:

- `wikilink`
- `markdown_link`
- `topic_timeline_pair`
- `topic_article_backlink`
- `source_index_link`
- `broken_link`

## Meaningful Graph Features

The graph layer should answer questions that are hard to answer from plain files:

- Which topics are central enough to deserve better summaries?
- Which objects are isolated and likely under-maintained?
- Which topic/article links are broken or one-way only?
- Which communities exist in the KB?
- Which cross-type connections create useful navigation paths?
- Which questions should an agent ask next based on actual structure?

V1 `GRAPH_REPORT.md` should include:

- Summary counts.
- God nodes by degree.
- Communities by connected component.
- Orphan nodes.
- Broken or ambiguous links.
- Cross-type relationship highlights.
- Suggested next questions.

This report is for humans and agents, but agents should prefer `graph.json` for automation.

## Anti-Mess Constraints

1. No graph business logic in `scripts/fokb.py`.
2. No renderer should scan files. Renderers receive graph data.
3. No analytics function should write files.
4. No command should return prose-only results.
5. No optional dependency for V1 graph generation.
6. No hidden network calls in graph generation.
7. Every edge must explain where it came from.
8. Every new command must have parser tests and behavior tests.
9. New files should use small public functions with typed-ish dict/dataclass boundaries.
10. Compatibility aliases may call new code, but new code must not depend on old command names.

## Error Handling

Graph command errors use the existing envelope shape.

New error codes:

- `graph_build_failed`
- `graph_no_markdown_objects`
- `graph_write_failed`

An empty KB should not crash. It should return an OK envelope with zero counts and empty artifacts if output generation is possible.

Broken links are graph findings, not command failures.

## Testing Strategy

Tests should verify behavior through the public command and stable module interfaces.

Required tests:

- `wikify` parser accepts current commands.
- `fokb` compatibility entrypoint still works.
- `WIKIFY_BASE` takes precedence over `FOKB_BASE`.
- `wikify graph` builds graph artifacts for `sample-kb`.
- `graph.json` has stable schema fields.
- Markdown links and wikilinks create edges with provenance.
- Broken links are represented as `AMBIGUOUS` edges/findings, not crashes.
- `GRAPH_REPORT.md` contains summary, central nodes, communities, orphans, and suggested questions.
- `--no-html` skips HTML but still writes JSON and report.

## Migration Plan

1. Add `wikify` console script while keeping `fokb`.
2. Introduce `wikify/` package with config and envelope helpers.
3. Add graph model, extractor, builder, analytics, report, and HTML renderer.
4. Add `graph` command to the existing CLI path with minimal glue.
5. Update docs to show `wikify` first.
6. Keep old command examples available for compatibility notes.

The first implementation can leave most existing commands in place. The important architectural move is that new graph code starts in the modular package, creating a path to gradually extract older functionality later.

## Future Extensions

Once V1 is stable:

- Add optional LLM extractor for inferred semantic edges.
- Add code AST extractor as a separate plugin.
- Add `wikify graph query`, `wikify graph path`, and `wikify graph explain`.
- Add MCP server exposing graph queries.
- Add incremental graph rebuild using file hashes.
- Add graph-informed maintenance signals, such as isolated topic warnings.

Each extension must enter through an extractor, analytics, or query module, not by modifying renderer or CLI internals.

