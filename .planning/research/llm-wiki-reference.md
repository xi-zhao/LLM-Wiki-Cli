# Reference Research: nashsu/llm_wiki

**Date:** 2026-04-28
**Reason:** User asked to reference `https://github.com/nashsu/llm_wiki` before continuing Wikify GSD planning.

## Sources Reviewed

- Repository overview: https://github.com/nashsu/llm_wiki
- Ingest queue lifecycle: https://github.com/nashsu/llm_wiki/blob/main/src/lib/ingest-queue.ts
- Ingest/write safety context: https://github.com/nashsu/llm_wiki/blob/main/src/lib/ingest.ts
- Graph relevance model: https://github.com/nashsu/llm_wiki/blob/main/src/lib/graph-relevance.ts
- Graph insights model: https://github.com/nashsu/llm_wiki/blob/main/src/lib/graph-insights.ts
- License: https://github.com/nashsu/llm_wiki/blob/main/LICENSE

## Useful Product Ideas To Borrow

### 1. Durable task lifecycle

`llm_wiki` has a persistent ingest queue with states, cancellation, retry, and cleanup behavior. Wikify already has `graph-agent-tasks.json`, but it is still a static queue. The next durable step is to let agents move tasks through a small state machine without rewriting content pages.

Wikify mapping:
- Keep the artifact-first queue.
- Add lifecycle commands after patch proposal exists.
- Record state transitions as append-only events.
- Preserve read-only task listing as the default behavior.

### 2. Two-stage work: analyze before generating

`llm_wiki` describes a two-step ingest flow: analysis first, generation second. That maps well to Wikify's safety goals. Agents should first produce a scoped proposal artifact, then a later phase can decide whether to apply or reject it.

Wikify mapping:
- Phase 3 should add `wikify propose --task-id <id>`.
- Proposal must be deterministic JSON.
- Proposal must not apply content edits.
- Proposal must validate every path against the task `write_scope`.

### 3. Stronger path and write boundaries

The ingest path handles derived wiki outputs from source inputs. Wikify should keep this as a principle, not as copied implementation: every proposed write must be scoped, normalized, and explainable.

Wikify mapping:
- Proposal artifacts include `write_scope`, `proposed_files`, `blocked_files`, and `preflight`.
- Any path outside `write_scope` returns a structured error.
- Content mutation remains out of scope until a later apply phase exists.

### 4. Graph relevance signals

`llm_wiki` uses direct links, source overlap, Adamic-Adar/common-neighbor structure, and type affinity as graph relevance signals. Wikify can use the same conceptual signals with a stdlib-only implementation.

Wikify mapping:
- Phase 5 should compute relevance scores for candidate links and maintenance tasks.
- Scores should prioritize and explain suggestions, not silently rewrite content.
- Scores should be attached to findings/tasks with evidence.

### 5. Graph insights

`llm_wiki` detects knowledge gaps from graph structure, including isolated nodes, sparse communities, and bridge nodes. Wikify already emits graph findings, so these can become stronger maintenance signals.

Wikify mapping:
- Add "gap" and "bridge" finding types after scoring exists.
- Generate tasks only when evidence is clear enough.
- Keep low-confidence insights informational.

### 6. Purpose-aware context

`llm_wiki` introduces `purpose.md` as a project direction artifact read during ingest/query. Wikify needs a CLI-friendly version so automation can judge whether a proposed repair is meaningful, not merely syntactically valid.

Wikify mapping:
- Phase 6 should introduce optional `purpose.md` or `wikify-purpose.md`.
- Missing purpose must be non-blocking.
- Proposal artifacts can include purpose evidence when present.

## What Not To Copy

- Do not copy source code from `llm_wiki`; the repo uses GPLv3 while Wikify is MIT.
- Do not import the desktop/Tauri/UI architecture into this CLI.
- Do not add hidden LLM provider calls inside deterministic maintenance commands.
- Do not add automatic content rewriting before proposal, lifecycle, and apply contracts are explicitly designed.

## Resulting GSD Sequence

1. Phase 3: Scoped Patch Proposal.
2. Phase 4: Agent Task Lifecycle.
3. Phase 5: Graph Relevance Scoring.
4. Phase 6: Purpose-Aware Proposals.
