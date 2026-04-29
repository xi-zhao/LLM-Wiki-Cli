# Phase 26: Human Wiki Views And Local Static Output - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 26-human-wiki-views-and-local-static-output
**Areas discussed:** command boundary, view source of truth, output layout, static HTML rendering, missing data and edit protection

---

## Command Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| `wikify views` | Dedicated human-view generation command with Markdown and static HTML output. | yes |
| Extend `wikify wikiize` | Generate views as a final wikiization side effect. | |
| Extend `wikify graph` | Treat human views mainly as graph output. | |

**User's choice:** Agent-selected under the user's prior low-interruption automation preference.
**Notes:** Dedicated command keeps the source-to-wiki-to-view pipeline explicit and prevents hidden sync/wikiize/graph side effects.

---

## View Source Of Truth

| Option | Description | Selected |
|--------|-------------|----------|
| Object artifacts first | Render from `artifacts/objects/object-index.json`, object JSON files, source registry, source item index, and queue artifacts. | yes |
| Markdown scan first | Scan generated Markdown and infer view structure from files. | |
| Raw source reread | Re-open original source files to build richer views. | |

**User's choice:** Agent-selected under the user's prior low-interruption automation preference.
**Notes:** Object artifacts first preserves the single source of truth for future human and agent views. Raw rereads or inferred semantics would create drift and hidden behavior.

---

## Output Layout

| Option | Description | Selected |
|--------|-------------|----------|
| `views/` plus `views/site/` | Human Markdown views under `views/`, static HTML mirror under `views/site/`, control reports under `.wikify/views/`. | yes |
| Everything under `.wikify/` | Treat views as internal generated state. | |
| Everything under `wiki/` | Mix generated pages and navigation views in one tree. | |

**User's choice:** Agent-selected under the user's prior low-interruption automation preference.
**Notes:** `views/` is already created by workspace init as a visible product artifact root. `.wikify/views/` is kept for manifests and reports only.

---

## Static HTML Rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Stdlib renderer | Escape HTML safely and render a bounded Markdown subset with no extra dependencies or server. | yes |
| Add Markdown/template dependency | Use a richer renderer with external packages. | |
| Browser app | Build a richer UI shell now. | |

**User's choice:** Agent-selected under the user's prior low-interruption automation preference.
**Notes:** Phase 26 requires stdlib-compatible local static output. Browser app and desktop UI remain out of scope.

---

## Missing Data And Edit Protection

| Option | Description | Selected |
|--------|-------------|----------|
| Honest empty states and hash guard | Missing optional data becomes empty-state views/next actions; existing generated Markdown views are protected by manifest hashes. | yes |
| Best-effort inference | Infer missing topics/timelines from filenames or snippets. | |
| Always overwrite | Treat generated views as disposable and overwrite without drift checks. | |

**User's choice:** Agent-selected under the user's prior low-interruption automation preference.
**Notes:** Honest empty states keep trust; hash guards protect visible artifacts users may edit.

## the agent's Discretion

- Exact module names and helper decomposition.
- Exact CSS and local static page styling.
- Exact schema field ordering for view run reports and manifests.
- Exact empty-state wording.

## Deferred Ideas

- Agent context exports and query commands are Phase 27.
- Maintenance targeting human views and personal wiki exports is Phase 28.
- Desktop/Tauri UI parity, hosted publishing, vector search, and chat-first RAG remain future/out-of-scope work.
