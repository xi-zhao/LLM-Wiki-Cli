# Phase 28: Pattern Map

**Phase:** 28 - Maintenance Integration And Compatibility
**Created:** 2026-04-30

## Closest Existing Patterns

### Maintenance Orchestration

- **Analog:** `wikify/maintenance/runner.py`
- **Pattern:** Build graph artifacts, derive findings, build a plan, apply the plan, build task queue, and write deterministic artifacts under `sorted/`.
- **Use for Phase 28:** Keep this pipeline and insert v0.2 target resolution/finding enrichment before planning and task queue generation.

### Graph Finding Shape

- **Analog:** `wikify/maintenance/findings.py`
- **Pattern:** Findings are dictionaries with stable `id`, `type`, `severity`, `title`, `subject`, `evidence`, `recommended_action`, `can_auto_apply`, and `policy_minimum`.
- **Use for Phase 28:** Add optional typed target metadata to findings without removing legacy fields.

### Agent Task Queue Contract

- **Analog:** `wikify/maintenance/task_queue.py`
- **Pattern:** Queued findings become `wikify.graph-agent-tasks.v1` tasks with path-based `write_scope`, instructions, acceptance checks, status, and optional relevance.
- **Use for Phase 28:** Preserve all existing task fields; add optional v0.2 fields such as `target_kind`, `object_id`, `body_path`, `view_path`, `source_refs`, and `regeneration_command`.

### Object/View/Agent Snapshot Loading

- **Analog:** `wikify/views.py` and `wikify/agent.py`
- **Pattern:** Load existing object/source/control artifacts; optional artifacts generate warnings; non-dry-run writes validate object artifacts before writing.
- **Use for Phase 28:** Build `wikify/maintenance/targets.py` with the same local-first, artifact-only loading style.

### Generated Artifact Hash Guards

- **Analog:** `wikify/wikiize.py` and `wikify/views.py`
- **Pattern:** Generated visible Markdown is not silently overwritten when drifted; queue tasks are created instead.
- **Use for Phase 28:** View and agent export findings should queue explicit regeneration/review tasks rather than patching derived files directly.

### Patch Proposal And Bundle Flow

- **Analog:** `wikify/maintenance/proposal.py`, `bundle_request.py`, `bundle_verifier.py`, `patch_apply.py`, and `task_runner.py`
- **Pattern:** Tasks become scoped proposals; bundle requests snapshot write scopes; external agents write bundles; verifier accepts/rejects; apply is deterministic and rollback is hash-guarded.
- **Use for Phase 28:** Add generated-page preservation context and checks without changing the underlying `replace_text` operation model.

### Test Style

- **Analog:** `tests/test_maintenance_*.py`, `tests/test_wikiize.py`, `tests/test_views.py`, `tests/test_agent.py`, and `tests/test_wikify_cli.py`
- **Pattern:** Use `unittest`, temporary directories, direct module calls, deterministic JSON/Markdown fixtures, and CLI JSON envelope assertions.
- **Use for Phase 28:** Add focused tests per subsystem and one local E2E fixture; avoid real provider calls.

## New Files Expected

- `wikify/maintenance/targets.py` - v0.2 maintenance target resolver and optional artifact index.
- `wikify/maintenance/preservation.py` - generated page preservation context and local validation helpers.
- `tests/test_maintenance_targets.py` - target resolver loading, indexing, and legacy degradation tests.
- `tests/test_maintenance_artifact_findings.py` - validation/view/wikiization/agent export finding tests.
- `tests/test_maintenance_generated_page_preservation.py` - preservation tests across bundle, verifier, and apply paths.
- `tests/test_maintenance_e2e.py` - source-to-maintenance local workflow fixture.

## Modified Files Expected

- `wikify/maintenance/findings.py` - object-aware enrichment and artifact-health findings.
- `wikify/maintenance/planner.py` - risk map for new queued actions.
- `wikify/maintenance/task_queue.py` - optional typed metadata propagation and new action instructions/checks.
- `wikify/maintenance/runner.py` - load target index and use enriched finding builder.
- `wikify/maintenance/proposal.py` - preservation metadata in proposals.
- `wikify/maintenance/bundle_request.py` - preservation instructions and safety context.
- `wikify/maintenance/bundle_verifier.py` - preservation facts in verifier request and deterministic rejection.
- `wikify/maintenance/patch_apply.py` - preservation preflight before content apply.
- `wikify/maintenance/task_runner.py` - keep rejection feedback path compatible.
- `README.md`, `LLM-Wiki-Cli-README.md`, and `scripts/fokb_protocol.md` - document maintenance integration and compatibility.

## Non-Patterns

- Do not rename `sorted/graph-*` artifact paths in Phase 28.
- Do not create a second persistent maintenance database.
- Do not silently run `sync`, `wikiize`, `views`, `agent export`, provider calls, external agents, embeddings, or raw-source retrieval from `wikify maintain`.
- Do not patch generated views or agent exports when regeneration is the correct source-of-truth action.
- Do not rely only on verifier prompts to preserve `source_refs` and `review_status`.
