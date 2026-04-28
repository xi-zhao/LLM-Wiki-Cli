# Wikify Maintain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `wikify maintain`, an autonomous graph-driven maintenance loop that builds graph artifacts, generates findings, creates an action plan, writes audit artifacts, and returns a stable JSON envelope without interrupting the user.

**Architecture:** Add a focused `wikify/maintenance/` package. `findings.py` derives deterministic findings from `graph.json`; `planner.py` converts findings into policy-gated steps; `executor.py` classifies executable versus queued steps; `history.py` persists append-only run records; `runner.py` orchestrates the loop and is the only module called by `wikify.cli`.

**Tech Stack:** Python 3.10+, stdlib only, dataclasses/dicts, argparse, unittest, existing Wikify JSON envelope style.

---

### Task 1: Maintenance Findings

**Files:**
- Create: `wikify/maintenance/__init__.py`
- Create: `wikify/maintenance/findings.py`
- Modify: `pyproject.toml`
- Test: `tests/test_maintenance_findings.py`

- [ ] **Step 1: Write the failing findings tests**

Create `tests/test_maintenance_findings.py` with a graph dictionary containing:

```python
graph = {
    'schema_version': 'wikify.graph.v1',
    'analytics': {
        'node_count': 4,
        'edge_count': 3,
        'broken_links': [
            {'source': 'topics/a.md', 'target': 'Missing', 'line': 7, 'label': 'unresolved_wikilink'}
        ],
        'orphans': [
            {'id': 'sources/index.md', 'title': 'Sources', 'type': 'sources'}
        ],
        'central_nodes': [
            {'id': 'topics/a.md', 'title': 'A', 'type': 'topics', 'degree': 12}
        ],
        'communities': [
            {'id': 'community-1', 'nodes': ['topics/a.md', 'articles/parsed/a.md', 'sorted/a.md'], 'size': 3}
        ],
    },
}
```

Assert `build_findings(graph)` emits finding types `broken_link`, `orphan_node`, `god_node`, and `mature_community`. Assert every finding has `id`, `type`, `severity`, `title`, `subject`, `evidence`, `recommended_action`, `can_auto_apply`, and `policy_minimum`. Assert `summarize_findings(findings)` returns `finding_count`, `by_type`, and `by_severity`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_maintenance_findings -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'wikify.maintenance'`.

- [ ] **Step 3: Implement findings module**

Implement:

- `build_findings(graph: dict) -> list[dict]`
- `summarize_findings(findings: list[dict]) -> dict`

Finding rules:

- Each `analytics.broken_links[]` creates `broken_link`, severity `warning`, action `queue_link_repair`.
- Each `analytics.orphans[]` creates `orphan_node`, severity `info`, action `queue_orphan_attachment`.
- Each central node with `degree >= max(8, node_count)` creates `god_node`, severity `info`, action `queue_digest_refresh`.
- Each community with `size >= 3` creates `mature_community`, severity `info`, action `queue_community_synthesis`.
- If `node_count == 0` or `edge_count == 0`, create `thin_graph`, severity `warning`, action `record_graph_health_snapshot`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_maintenance_findings -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/maintenance tests/test_maintenance_findings.py pyproject.toml
git commit -m "feat: derive graph maintenance findings"
```

### Task 2: Maintenance Planner And Executor

**Files:**
- Create: `wikify/maintenance/planner.py`
- Create: `wikify/maintenance/executor.py`
- Test: `tests/test_maintenance_plan.py`

- [ ] **Step 1: Write the failing planner/executor tests**

Create `tests/test_maintenance_plan.py` with two findings:

```python
findings = [
    {
        'id': 'broken-link:topics/a.md:7:Missing',
        'type': 'broken_link',
        'severity': 'warning',
        'title': 'Broken link',
        'subject': 'topics/a.md',
        'evidence': {'source': 'topics/a.md', 'line': 7},
        'recommended_action': 'queue_link_repair',
        'can_auto_apply': False,
        'policy_minimum': 'conservative',
    },
    {
        'id': 'thin-graph',
        'type': 'thin_graph',
        'severity': 'warning',
        'title': 'Thin graph',
        'subject': 'graph',
        'evidence': {'node_count': 0, 'edge_count': 0},
        'recommended_action': 'record_graph_health_snapshot',
        'can_auto_apply': True,
        'policy_minimum': 'conservative',
    },
]
```

Assert `build_plan(findings, policy='balanced')` returns schema version `wikify.maintenance-plan.v1`, keeps policy, and creates one step per finding. Assert every step references `finding_id`. Assert `apply_plan(plan, dry_run=False)` marks executable steps `executed` and semantic/content steps `queued`. Assert `apply_plan(plan, dry_run=True)` marks all steps `dry_run`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_maintenance_plan -v`

Expected: FAIL because `wikify.maintenance.planner` and `wikify.maintenance.executor` do not exist.

- [ ] **Step 3: Implement planner and executor**

Implement:

- `build_plan(findings: list[dict], policy: str = 'balanced') -> dict`
- `apply_plan(plan: dict, dry_run: bool = False) -> dict`

Policies allowed: `conservative`, `balanced`, `aggressive`.

Action risk mapping:

- `queue_link_repair`: semantic, cannot execute in V1.
- `queue_orphan_attachment`: semantic, cannot execute in V1.
- `queue_digest_refresh`: generated_content, cannot execute in V1.
- `queue_community_synthesis`: generated_content, cannot execute in V1.
- `record_graph_health_snapshot`: deterministic, can execute in V1.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_maintenance_plan -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/maintenance/planner.py wikify/maintenance/executor.py tests/test_maintenance_plan.py
git commit -m "feat: plan graph maintenance actions"
```

### Task 3: Maintenance History And Runner

**Files:**
- Create: `wikify/maintenance/history.py`
- Create: `wikify/maintenance/runner.py`
- Test: `tests/test_maintenance_runner.py`

- [ ] **Step 1: Write the failing runner tests**

Create `tests/test_maintenance_runner.py`. Copy `sample-kb` to a temp directory and call:

```python
from wikify.maintenance.runner import run_maintenance
result = run_maintenance(kb, policy='balanced', dry_run=False)
```

Assert:

- `result['policy'] == 'balanced'`
- `result['summary']` contains `finding_count`, `planned_count`, `executed_count`, and `queued_count`
- `graph/graph.json` exists
- `sorted/graph-findings.json` exists
- `sorted/graph-maintenance-plan.json` exists
- `sorted/graph-maintenance-history.json` exists
- `result['next_commands']` is a list

Add a second test for `dry_run=True` asserting graph artifacts exist but maintenance artifacts under `sorted/` do not.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_maintenance_runner -v`

Expected: FAIL because `wikify.maintenance.runner` does not exist.

- [ ] **Step 3: Implement history and runner**

Implement:

- `write_json(path, data)`
- `append_run(base, run_record, dry_run=False)`
- `run_maintenance(base, policy='balanced', dry_run=False) -> dict`

Runner flow:

1. Call `build_graph_artifacts(base, include_html=False)`.
2. Build findings from `graph_result['graph']`.
3. Build findings document with schema `wikify.graph-findings.v1`.
4. Build plan.
5. Apply plan.
6. If not dry-run, write findings and plan to `sorted/` and append history.
7. Return result with artifacts, summary, next commands, execution, and completion.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_maintenance_runner -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/maintenance/history.py wikify/maintenance/runner.py tests/test_maintenance_runner.py
git commit -m "feat: run autonomous graph maintenance"
```

### Task 4: CLI Wiring

**Files:**
- Modify: `wikify/cli.py`
- Test: `tests/test_wikify_cli.py`

- [ ] **Step 1: Write the failing CLI tests**

Extend `tests/test_wikify_cli.py` with:

- Parser test: `parser.parse_args(['maintain', '--policy', 'balanced', '--dry-run'])`.
- Command test: copy `sample-kb` to temp, set `WIKIFY_BASE`, call `cli.main(['--output', 'json', 'maintain', '--dry-run'])`, assert exit `0`, command `maintain`, graph JSON exists, and maintenance artifacts do not exist.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_wikify_cli -v`

Expected: FAIL because `maintain` is not wired into the parser.

- [ ] **Step 3: Wire maintain command**

In `wikify/cli.py`, import `run_maintenance`, add `cmd_maintain(args)`, and add a top-level `maintain` subparser with:

- `--policy` choices `conservative`, `balanced`, `aggressive`; default `balanced`
- `--dry-run` flag

The handler returns `envelope_ok('maintain', result)` and `graph_maintenance_failed` on exceptions.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_wikify_cli -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add wikify/cli.py tests/test_wikify_cli.py
git commit -m "feat: wire wikify maintain command"
```

### Task 5: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `LLM-Wiki-Cli-README.md`
- Modify: `scripts/fokb_protocol.md`
- Test: full suite

- [ ] **Step 1: Update docs**

Document:

- `wikify maintain`
- `--policy conservative|balanced|aggressive`
- `--dry-run`
- Output artifacts: `sorted/graph-findings.json`, `sorted/graph-maintenance-plan.json`, `sorted/graph-maintenance-history.json`
- V1 safety rule: no content-page edits.

- [ ] **Step 2: Run full tests**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 3: Run manual smoke test**

Run:

```bash
tmpdir=$(mktemp -d)
cp -R sample-kb "$tmpdir/kb"
WIKIFY_BASE="$tmpdir/kb" python3 -m wikify.cli maintain --dry-run
WIKIFY_BASE="$tmpdir/kb" python3 -m wikify.cli maintain
rm -rf "$tmpdir"
```

Expected: Both commands return `ok: true`. Dry-run writes graph artifacts only. Normal run writes graph artifacts plus sorted maintenance artifacts.

- [ ] **Step 4: Commit**

Run:

```bash
git add README.md LLM-Wiki-Cli-README.md scripts/fokb_protocol.md
git commit -m "docs: document autonomous maintenance"
```

