# Wikify Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `wikify` as the public CLI name and implement `wikify graph` as a stable local graph intelligence layer for the Markdown knowledge base.

**Architecture:** Keep existing behavior compatible through `fokb`, but put new code in a focused `wikify/` package. The graph pipeline scans Markdown wiki objects, extracts nodes and provenance-rich edges, computes simple graph analytics, and writes `graph.json`, `GRAPH_REPORT.md`, and optional `graph.html`.

**Tech Stack:** Python 3.10+, stdlib only, argparse, dataclasses, unittest, existing JSON envelope style.

---

### Task 1: Public CLI Name And Config Compatibility

**Files:**
- Create: `wikify/__init__.py`
- Create: `wikify/config.py`
- Create: `wikify/envelope.py`
- Create: `wikify/cli.py`
- Modify: `scripts/fokb.py`
- Modify: `pyproject.toml`
- Test: `tests/test_wikify_cli.py`

- [ ] **Step 1: Write failing parser and config tests**

Add `tests/test_wikify_cli.py` with tests that import `wikify.cli` and `wikify.config`, assert the parser program is `wikify`, assert `graph` parses, and assert `WIKIFY_BASE` takes precedence over `FOKB_BASE`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_wikify_cli.py -v`

Expected: FAIL because `wikify` package does not exist.

- [ ] **Step 3: Add package shell and compatibility config**

Implement:

- `wikify.config.discover_app_root()`
- `wikify.config.discover_base()`
- `wikify.config.build_paths()`
- `wikify.envelope.envelope_ok()`
- `wikify.envelope.envelope_error()`
- `wikify.envelope.print_output()`
- `wikify.cli.build_parser()` wrapping existing `scripts.fokb.build_parser()` for current commands, then changing `prog` to `wikify`.

Do not add graph behavior yet except parser shape.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_wikify_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Add console script alias**

Update `pyproject.toml`:

```toml
[project.scripts]
wikify = "wikify.cli:main"
fokb = "scripts.fokb:main"
```

Keep `fokb` intact.

- [ ] **Step 6: Commit**

Run:

```bash
git add wikify tests/test_wikify_cli.py pyproject.toml scripts/fokb.py
git commit -m "feat: add wikify cli alias"
```

### Task 2: Markdown Object Index

**Files:**
- Create: `wikify/markdown_index.py`
- Test: `tests/test_markdown_index.py`

- [ ] **Step 1: Write failing scan tests**

Add tests that call `scan_objects(sample-kb, scope='all')` and assert it returns topics, parsed, briefs, sorted, and source objects with `relative_path`, `type`, `title`, `text`, and `lines`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_markdown_index.py -v`

Expected: FAIL because `wikify.markdown_index` does not exist.

- [ ] **Step 3: Implement markdown index**

Implement `WikiObject` dataclass and `scan_objects(base, scope='all')`. Supported scopes are `all`, `topics`, `timelines`, `briefs`, `parsed`, `sorted`, and `sources`. Ignore template files beginning with `_`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_markdown_index.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/markdown_index.py tests/test_markdown_index.py
git commit -m "feat: index markdown wiki objects"
```

### Task 3: Graph Model And Extractors

**Files:**
- Create: `wikify/graph/__init__.py`
- Create: `wikify/graph/model.py`
- Create: `wikify/graph/extractors.py`
- Test: `tests/test_graph_extractors.py`

- [ ] **Step 1: Write failing extractor tests**

Add tests using a temporary KB with:

- a topic file linking to `../articles/parsed/a.md`
- a parsed file linking back via Markdown link
- a `[[Concept Note]]` wikilink without a target

Assert:

- nodes are created for Markdown files
- Markdown links become `EXTRACTED` edges
- broken wikilinks become `AMBIGUOUS` `broken_link` edges
- every edge has `source`, `target`, `type`, `provenance`, `confidence`, `source_path`, `line`, and `label`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_graph_extractors.py -v`

Expected: FAIL because graph modules do not exist.

- [ ] **Step 3: Implement graph model and extractors**

Implement `GraphNode` and `GraphEdge` dataclasses with `to_dict()`. Implement `extract_nodes(objects)` and `extract_edges(objects, nodes)` with deterministic Markdown link and wikilink parsing.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_graph_extractors.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/graph tests/test_graph_extractors.py
git commit -m "feat: extract wiki graph nodes and edges"
```

### Task 4: Analytics, Report, HTML, And Artifact Builder

**Files:**
- Create: `wikify/graph/analytics.py`
- Create: `wikify/graph/report.py`
- Create: `wikify/graph/html.py`
- Create: `wikify/graph/builder.py`
- Test: `tests/test_graph_builder.py`

- [ ] **Step 1: Write failing build tests**

Add tests that call `build_graph_artifacts(sample-kb, include_html=True)` and assert:

- `graph/graph.json` exists
- `graph/GRAPH_REPORT.md` exists
- `graph/graph.html` exists
- JSON has `schema_version = wikify.graph.v1`
- analytics includes `node_count`, `edge_count`, `community_count`, `orphan_count`, and `central_nodes`
- report contains `# Wikify Graph Report`, `God Nodes`, `Communities`, `Orphans`, and `Suggested Questions`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_graph_builder.py -v`

Expected: FAIL because builder modules do not exist.

- [ ] **Step 3: Implement analytics and artifact writing**

Implement connected components with stdlib sets, degree counts, central node sorting, orphan detection, relation counts, and suggested questions. Write JSON with deterministic ordering. Render a simple self-contained HTML file using embedded JSON.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_graph_builder.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/graph tests/test_graph_builder.py
git commit -m "feat: build wikify graph artifacts"
```

### Task 5: Wire `wikify graph` Into CLI

**Files:**
- Modify: `wikify/cli.py`
- Modify: `scripts/fokb.py`
- Test: `tests/test_wikify_cli.py`

- [ ] **Step 1: Write failing command tests**

Extend `tests/test_wikify_cli.py` to call `wikify.cli.main(['--output', 'json', 'graph', '--no-html'])` with `WIKIFY_BASE` pointed at a temporary copy of `sample-kb`. Assert the command exits `0`, prints JSON, writes JSON and report, and skips HTML.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_wikify_cli.py -v`

Expected: FAIL because `graph` command is not wired.

- [ ] **Step 3: Implement command handler**

Add `cmd_graph(args)` to `wikify.cli`, call `build_graph_artifacts()`, return an envelope, and include completion artifacts. Keep existing commands delegated to `scripts.fokb` so old behavior remains stable.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_wikify_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/cli.py scripts/fokb.py tests/test_wikify_cli.py
git commit -m "feat: wire wikify graph command"
```

### Task 6: Documentation And Regression Verification

**Files:**
- Modify: `README.md`
- Modify: `LLM-Wiki-Cli-README.md`
- Modify: `scripts/fokb_protocol.md`
- Modify: `scripts/README.md`
- Test: existing test suite

- [ ] **Step 1: Update documentation**

Show `wikify` first in examples. Mention `fokb` as a compatibility alias. Document `wikify graph`, graph artifacts, and the `WIKIFY_BASE` environment variable.

- [ ] **Step 2: Run full tests**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run sample graph command manually**

Run:

```bash
WIKIFY_BASE="$(pwd)/sample-kb" python3 -m wikify.cli graph --no-html
```

Expected: JSON envelope with `ok: true`, `graph.json` and `GRAPH_REPORT.md` artifact paths.

- [ ] **Step 4: Commit**

Run:

```bash
git add README.md LLM-Wiki-Cli-README.md scripts/fokb_protocol.md scripts/README.md
git commit -m "docs: document wikify graph workflow"
```

