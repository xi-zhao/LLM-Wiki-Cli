# Phase 28: Maintenance Integration And Compatibility - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 28 connects the v0.2.0 personal wiki model to the existing maintenance system from v0.1.0a2.

The phase should make `wikify maintain`, graph findings, agent tasks, patch proposals, verifier handoff, repair feedback, `run-task`, `run-tasks`, `maintain-run`, and `maintain-loop` understand the new personal wiki artifacts:

- canonical object JSON under `artifacts/objects/`
- generated wiki pages under `wiki/pages/`
- source and human views under `views/`
- agent exports under `llms.txt`, `llms-full.txt`, and `artifacts/agent/`
- control artifacts under `.wikify/`

This phase is an integration and compatibility phase, not a rewrite of maintenance.

It must not add hidden provider calls, embeddings/vector databases, chat UI, desktop UI, hosted sync, cloud publishing, raw-source retrieval, or a second knowledge store. Existing v0.1.0a2 commands and JSON envelopes remain compatible unless an explicit deprecation is documented and tested.

</domain>

<decisions>
## Implementation Decisions

### Maintenance Model

- **D-01:** Keep the existing graph maintenance command surface as the compatibility anchor. `wikify maintain`, `tasks`, `propose`, `bundle-request`, `produce-bundle`, `verify-bundle`, `apply`, `rollback`, `run-task`, `run-tasks`, `maintain-run`, and `maintain-loop` must continue to work for v0.1.0a2-style workspaces.
- **D-02:** Do not introduce a new top-level `wikify maintenance` namespace in Phase 28 unless planning finds it unavoidable. The main value is making the existing maintenance loop object-aware.
- **D-03:** Keep `sorted/graph-agent-tasks.json` and `wikify.graph-agent-tasks.v1` compatible. New v0.2 metadata should be optional additive fields so old task readers do not break.
- **D-04:** Keep `sorted/graph-findings.json`, `sorted/graph-maintenance-plan.json`, patch proposal directories, bundle request directories, verification directories, application records, and lifecycle events compatible.
- **D-05:** Treat "graph maintenance" as the legacy subsystem name. Product behavior should now be "wiki maintenance" over graph, object, view, and agent artifacts, but artifact paths can remain legacy-named for compatibility.
- **D-06:** Build an ephemeral maintenance target index from existing artifacts rather than creating a persistent second index. The target index can map object ids, body paths, object JSON paths, view paths, source ids, and agent artifact paths.
- **D-07:** The maintenance target index should load object documents, the object index, source items, view manifests/reports, validation reports, graph artifacts, and agent export artifacts when present.
- **D-08:** Missing optional artifacts should produce warnings or findings, not crashes, when the workspace is otherwise valid. Malformed required artifacts should return structured errors.

### Finding Sources And Targets

- **D-09:** Preserve existing graph-derived findings: broken links, orphan nodes, high-degree central nodes, mature communities, thin graph, relevance signals, and conservative queueing behavior.
- **D-10:** Add object-aware finding enrichment so graph subjects can resolve to `object_id`, `object_type`, `body_path`, `object_path`, source refs, and review status when the subject corresponds to a v0.2 object.
- **D-11:** Maintenance findings may target four surface families: personal wiki pages, source/human views, agent exports, and object/control artifacts.
- **D-12:** Personal wiki page targets include both the generated Markdown body path and the canonical `wikify.wiki-page.v1` JSON object path when available.
- **D-13:** Source page and human view targets should be resolved through the view manifest and view run report. Do not infer view paths by string guessing if manifest data is available.
- **D-14:** Agent export targets should be resolved through Phase 27 artifact locations: root `llms.txt`, root `llms-full.txt`, `artifacts/agent/*.json`, `artifacts/agent/context-packs/`, and `.wikify/agent/` manifests/reports.
- **D-15:** Agent exports are derived artifacts. Maintenance should prefer "regenerate with `wikify agent export`" findings/tasks over manual patching of agent export files.
- **D-16:** Human views are generated artifacts with hash guards. Maintenance should prefer "regenerate with `wikify views`" findings/tasks unless the specific task is about a deliberate view template/content bug.
- **D-17:** Object validation records are valid maintenance inputs. Validation errors can become findings with precise object/path targets.
- **D-18:** Existing wikiization and view task queues are valid maintenance inputs. Maintenance should be able to surface drift or queued work without inventing separate user interruption.
- **D-19:** Do not reread raw source files to produce maintenance findings in Phase 28. Findings should come from existing synced/wikiized/object/view/agent/control artifacts.

### Task Queue Contract

- **D-20:** The old task fields remain stable: `id`, `source_finding_id`, `source_step_id`, `action`, `priority`, `target`, `evidence`, `write_scope`, `agent_instructions`, `acceptance_checks`, `requires_user`, and `status`.
- **D-21:** Additive v0.2 task metadata can include `target_kind`, `target_family`, `object_id`, `object_type`, `body_path`, `object_path`, `view_path`, `agent_artifact_path`, `source_refs`, `review_status`, and `regeneration_command`.
- **D-22:** `target` should remain a human-readable/path-compatible field for legacy consumers. `object_id` and typed metadata should carry the stronger v0.2 identity.
- **D-23:** `write_scope` stays path-based and relative to the workspace root because proposal, bundle request, apply, and rollback already validate relative paths.
- **D-24:** For tasks that should not directly mutate files, `write_scope` may point at the primary generated artifact while instructions and acceptance checks require regeneration or queueing instead of content patching.
- **D-25:** New maintenance actions should be narrow and explainable. Likely actions include `queue_object_validation_repair`, `queue_generated_page_repair`, `queue_view_regeneration`, `queue_agent_export_refresh`, and `queue_source_traceability_repair`.
- **D-26:** Existing actions such as `queue_link_repair`, `queue_orphan_attachment`, `queue_digest_refresh`, and `queue_community_synthesis` should continue to be emitted when the evidence matches legacy graph semantics.

### Repair And Verifier Safety

- **D-27:** Repair and verifier flows must preserve `source_refs` and `review_status` for generated wiki pages unless a future explicit review workflow changes them.
- **D-28:** Bundle requests for generated wiki pages should include preservation constraints in `agent_instructions`, `allowed_operations` constraints, or a dedicated safety block.
- **D-29:** The verifier request should expose preflight information plus v0.2 preservation facts when the proposal targets a generated page: front matter source refs, object JSON source refs, review status, object id, and body path.
- **D-30:** Verifier integration should reject patch bundles that remove, weaken, or silently alter source refs or review status for generated wiki pages.
- **D-31:** Post-apply checks should run focused object validation when object artifacts or generated page metadata are touched.
- **D-32:** Patch apply should remain deterministic `replace_text` with exact-once matching and hash-guarded rollback. Phase 28 should not expand to arbitrary AST edits or multi-file semantic rewrites.
- **D-33:** If a task targets both Markdown front matter and object JSON, the implementation must define whether the object JSON or Markdown front matter is authoritative for the repair. Prefer preserving both and rejecting divergence.
- **D-34:** Repair feedback from verifier rejection should carry structured findings back into the existing blocked task feedback path; do not create a parallel repair queue.

### Compatibility And UX

- **D-35:** Maintain the existing JSON envelope style and structured exit-code-2 error behavior.
- **D-36:** Dry-run behavior remains zero-write for content and control artifacts except where existing commands already documented in-memory previews.
- **D-37:** Commands without explicit agent or verifier command/profile must not execute external agents. Default profiles remain explicit shorthand only when the user passes `--agent-profile`.
- **D-38:** v0.1.0a2 Markdown-only/project-style workspaces should still pass maintenance tests. Object-aware code must degrade when object artifacts are absent.
- **D-39:** User-facing language should not sell audit/rollback as the headline. In docs, describe this phase as making the personal wiki maintainable and agent-safe while preserving source traceability.
- **D-40:** Keep output useful to agents: deterministic task ordering, stable ids where possible, explicit evidence, and clear commands for next action.

### End-To-End Verification

- **D-41:** Add an integration-style fixture for the local flow: `wikify init` -> `wikify source add` -> `wikify sync` -> `wikify wikiize` -> `wikify views` -> `wikify agent export`/`wikify agent context` -> `wikify maintain` -> task/proposal/verifier/repair path.
- **D-42:** The E2E fixture should avoid real provider calls. Use deterministic local sample scripts when agent/verifier behavior is required.
- **D-43:** Tests must assert both forward compatibility and backward compatibility: v0.2 metadata exists where expected, and legacy task/query fields still exist.
- **D-44:** Tests must cover preservation of `source_refs` and `review_status` when a generated wiki page repair is proposed, verified, rejected, repaired, or applied.
- **D-45:** Tests must cover maintenance findings that target at least one generated wiki page, one human/source view or view task, and one agent export artifact or refresh action.

### the agent's Discretion

- Exact helper module names, with a preference for a small maintenance-focused module such as `wikify/maintenance/targets.py`.
- Exact optional task metadata field ordering.
- Exact wording of agent instructions and acceptance checks, provided preservation and regeneration boundaries are explicit.
- Whether object-aware findings are added inside `findings.py` or composed by a new higher-level builder, provided legacy graph finding behavior remains intact.
- Whether Phase 28 is implemented in one plan or split into multiple plans. Prefer multiple plans if the verifier/repair preservation work would make a single plan too large.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Direction

- `AGENTS.md` - Product positioning, human/agent view split, CLI-first boundary, Graphify/LLM Wiki lessons, and generated wiki as the product artifact.
- `.planning/PROJECT.md` - Current v0.2.0 state, constraints, key decisions, and active maintenance integration requirement.
- `.planning/ROADMAP.md` - Phase 28 goal, requirements, success criteria, dependencies, and verification expectations.
- `.planning/REQUIREMENTS.md` - Maintenance requirements `MAINT-01` through `MAINT-04`.
- `.planning/STATE.md` - Current GSD state, unavailable SDK note, recent decisions, and continuity.

### Upstream Phase Context

- `.planning/phases/24-wiki-object-model-and-validation/24-CONTEXT.md` - Object schemas, object ids, source refs, review statuses, graph-edge compatibility, and validation behavior.
- `.planning/phases/24-wiki-object-model-and-validation/24-01-SUMMARY.md` - Implemented object model, front matter bridge, and validation command.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-CONTEXT.md` - Generated page/object layout, source refs, review status, edit protection, wikiization tasks, and Phase 28 handoff.
- `.planning/phases/25-source-backed-wikiization-pipeline/25-01-SUMMARY.md` - Implemented wikiize behavior and source-backed generated page evidence.
- `.planning/phases/26-human-wiki-views-and-local-static-output/26-CONTEXT.md` - Human view source of truth, view manifest, view drift tasks, and Phase 28 handoff.
- `.planning/phases/26-human-wiki-views-and-local-static-output/26-01-SUMMARY.md` - Implemented view generation, static HTML, hash guards, and view task queue.
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-CONTEXT.md` - Agent artifacts, context packs, citation/related indexes, and Phase 28 handoff.
- `.planning/phases/27-agent-wiki-interfaces-and-context-packs/27-03-SUMMARY.md` - Implemented agent export/context/cite/related behavior and smoke workflow.

### Existing Implementation Patterns

- `wikify/maintenance/runner.py` - Current maintenance orchestration, artifact paths, graph build, finding/plan/execution/task queue pipeline, and dry-run behavior.
- `wikify/maintenance/findings.py` - Current graph-only findings and recommended actions to preserve.
- `wikify/maintenance/planner.py` - Current plan building from findings.
- `wikify/maintenance/task_queue.py` - Existing `wikify.graph-agent-tasks.v1` schema and agent instruction/acceptance check conventions.
- `wikify/maintenance/task_reader.py` - Existing task selection/status filtering behavior.
- `wikify/maintenance/proposal.py` - Current path-based write-scope validation and proposal shape.
- `wikify/maintenance/bundle_request.py` - Target snapshots, repair context, allowed operations, and agent handoff instructions.
- `wikify/maintenance/bundle_verifier.py` - Verifier request/verdict shape, preflight integration, and rejection feedback path.
- `wikify/maintenance/patch_apply.py` - Deterministic `replace_text` apply, hash-guarded rollback, and application records.
- `wikify/maintenance/task_runner.py` - Single task workflow composition and verifier rejection handling.
- `wikify/maintenance/batch_runner.py`, `wikify/maintenance/maintain_run.py`, and `wikify/maintenance/maintain_loop.py` - Batch and loop composition to preserve.
- `wikify/objects.py` - Object schema versions, required fields, source refs, review statuses, object paths, and constructors.
- `wikify/object_validation.py` - Strict validation records, validation report, source/item reference checks, and focused validation.
- `wikify/wikiize.py` - Generated wiki page paths, source refs, review status, object JSON writes, object index updates, hash guards, and wikiization task queue.
- `wikify/views.py` - View manifest, source/human view paths, view drift tasks, graph/timeline entry views, and hash guards.
- `wikify/agent.py` - Agent export paths, `llms.txt`, `llms-full.txt`, page/citation/related indexes, context packs, and validation-before-write behavior.
- `wikify/graph/builder.py` and `wikify/graph/extractors.py` - Legacy graph artifact creation and object/front matter metadata extraction.
- `wikify/cli.py` - CLI parser pattern, JSON envelope use, and existing command compatibility.
- `wikify/envelope.py` - Success/error envelope helpers.
- `tests/test_maintenance_*.py` - Maintenance proposal/apply/task-runner/batch/loop/verifier patterns.
- `tests/test_wikiize.py`, `tests/test_views.py`, `tests/test_agent.py`, and `tests/test_wikify_cli.py` - v0.2 generated artifact fixtures and CLI envelope tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Current Maintenance Shape

- `run_maintenance()` builds legacy graph artifacts with `build_graph_artifacts(root, include_html=False)`, derives graph findings, builds a plan, applies the plan, and writes findings/plan/history/task queue under `sorted/`.
- `build_findings()` currently only sees graph analytics. It has no direct access to object documents, generated page paths, view manifests, or agent artifacts.
- `build_task_queue()` currently turns queued plan results into path-like tasks where `target` becomes `write_scope`.
- `build_patch_proposal()` validates path-based write scope and produces a planned content patch.
- `build_bundle_request()` snapshots files from `proposal.write_scope` and instructs external agents to produce a `wikify.patch-bundle.v1`.
- `verify_patch_bundle()` runs deterministic preflight, then delegates semantic acceptance to an explicit verifier command.
- `apply_patch_bundle()` supports only exact-once `replace_text` operations and hash-guarded rollback.

### v0.2 Artifact Shape

- Generated wiki pages live under `wiki/pages/` and are represented as `wikify.wiki-page.v1` JSON objects under `artifacts/objects/wiki_pages/`.
- Wiki page objects include `body_path`, `source_refs`, and `review_status`.
- `wikify validate` can validate object artifacts and Markdown front matter, including source/item reference integrity.
- Human views live under `views/` and are tracked through `.wikify/views/view-manifest.json`; drift creates `.wikify/queues/view-tasks.json`.
- Agent exports live at `llms.txt`, `llms-full.txt`, `artifacts/agent/`, and `.wikify/agent/`; context packs can also be object artifacts.
- Agent exports and context packs validate object artifacts before non-dry-run writes.

### Integration Risks

- Current graph subjects may be raw paths, graph node ids, or legacy identifiers. Planning must define a robust target resolution layer rather than assuming every subject is an object id.
- Current task `write_scope` is a list of relative paths. Object-aware metadata must not replace it unless proposal/apply semantics are deliberately redesigned.
- Directly patching generated agent exports or generated views can create stale derived artifacts. Prefer regeneration tasks for derived surfaces.
- Generated wiki pages have two metadata carriers: Markdown front matter and object JSON. Repairs must avoid divergence.
- Verifier acceptance currently depends on external verifier behavior. Phase 28 needs deterministic local pre/post preservation checks in addition to optional external verifier judgment.

### Recommended Implementation Shape

- Add a small target resolver that loads v0.2 artifacts and returns normalized maintenance targets.
- Enrich findings and tasks with optional typed target metadata while keeping legacy fields stable.
- Add preservation constraints to proposals/bundle requests when generated wiki pages are in scope.
- Add local verifier/preflight checks for generated-page preservation before external verifier acceptance or before apply.
- Add focused tests for legacy compatibility, v0.2 target enrichment, regeneration findings, and preservation rejection.

</code_context>

<specifics>
## Specific Ideas

- Treat Phase 28 as "make the maintenance loop see the same wiki object that humans and agents see."
- Let existing graph analytics remain useful, but attach object/view/agent context so tasks are meaningful for a personal knowledge base.
- When agent exports are stale or missing, create an explicit refresh task with a command such as `wikify agent export`, not a patch task over `llms.txt`.
- When views are stale or drifted, create an explicit view regeneration or review task, not silent regeneration inside `maintain`.
- For generated wiki pages, include both `source_refs` and `review_status` in task evidence so agents and verifiers have no excuse to drop them.
- Add test fixtures that model real personal wiki flow rather than isolated graph-only files.

</specifics>

<deferred>
## Deferred Ideas

- Renaming legacy `graph-*` maintenance artifact paths to `wiki-*`.
- Full maintenance namespace redesign.
- Provider-backed built-in repair generation.
- Vector or embedding-backed maintenance prioritization.
- Raw source reread during maintenance.
- Rich human review UI for maintenance queues.
- Hosted/remote maintenance automation.

</deferred>

---

*Phase: 28-maintenance-integration-and-compatibility*
*Context gathered: 2026-04-30*
