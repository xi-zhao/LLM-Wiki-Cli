# Phase 30: Trusted Agent Operation Snapshots - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning
**Source:** Phase 29 trusted-agent handoff and product decision to give agents full wiki permissions with recovery.

<domain>
## Phase Boundary

This phase adds explicit trusted-agent operation primitives so agents can snapshot broad edits before changing files, complete the operation after edits, and roll back safely if needed.

Wikify cannot intercept arbitrary agent file edits, so the first recoverability primitive must be an explicit CLI/API the agent calls before and after broad changes.

</domain>

<decisions>
## Implementation Decisions

### Trusted Operation Flow
- Agent calls `wikify trusted-op begin --path <relpath> --reason <why>` before broad edit.
- Agent edits, merges, splits, deletes, or creates files directly.
- Agent calls `wikify trusted-op complete --operation-path <path>` after edits.
- Agent or user can call `wikify trusted-op rollback --operation-path <path>`.

### Snapshot Semantics
- Snapshots are path based and stored in a durable operation record.
- Existing files store pre-change content and hash.
- Missing paths are valid snapshots so rollback can delete newly created files.
- Rollback is hash-guarded against drift after completion.

### Safety Boundary
- Paths must be relative and stay inside the workspace.
- This is trusted-agent recovery infrastructure, not a human approval gate.
- It should not call providers, run agents, or infer semantic changes.

### the agent's Discretion
- Exact module name and internal helper names.
- Whether operation records live under `.wikify/trusted-operations/` or another `.wikify/` control path.

</decisions>

<canonical_refs>
## Canonical References

### Existing Recovery Pattern
- `wikify/maintenance/patch_apply.py` - Existing patch application and hash-guarded rollback pattern.
- `tests/test_maintenance_patch_apply.py` - Existing rollback behavior tests.

### CLI
- `wikify/cli.py` - Add `trusted-op` command namespace.
- `tests/test_wikify_cli.py` - CLI parser and command envelope tests.

### Product Design
- `docs/superpowers/specs/2026-04-30-trusted-agent-ingest-experience-design.md` - Trusted-agent full-control and recovery principles.
- `.planning/phases/29-trusted-agent-ingest-handoff/29-01-SUMMARY.md` - Ingest handoff now instructs agents to snapshot broad rewrites.

</canonical_refs>

<specifics>
## Specific Ideas

- Add schema `wikify.trusted-operation.v1`.
- Add rollback schema `wikify.trusted-operation-rollback.v1`.
- Store operation records under `.wikify/trusted-operations/<operation-id>.json`.
- Provide `begin_trusted_operation`, `complete_trusted_operation`, and `rollback_trusted_operation`.
- Support `--dry-run` for begin and rollback.
- Use `--path` multiple times.
- Require `--reason` on begin.

</specifics>

<deferred>
## Deferred Ideas

- Rich semantic diff rendering.
- Automatic interception of agent writes.
- Policy presets for which operations require snapshots.
- Human approval workflows.

</deferred>

---

*Phase: 30-trusted-agent-operation-snapshots*
*Context gathered: 2026-04-30 via GSD inline planning*
