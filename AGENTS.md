# AGENTS.md

## Product Positioning

Wikify is a CLI-first personal knowledge base generator and maintenance tool. It turns scattered files, directories, URLs, repositories, notes, and other source material into an incremental local wiki that is useful to both humans and agents.

The knowledge base is the product artifact. It should be readable, navigable, and trustworthy for people, while also exposing stable machine interfaces that agents can query, cite, and use as long-term context.

## Core Promise

Wikify helps users build a living wiki from their personal and project knowledge, then makes that wiki easy for agents such as Codex, OpenClaw, and Claude Code to call.

The intended product feeling is:

- People can see and browse the knowledge they have accumulated.
- Agents can retrieve the right context without rereading raw files every time.
- New material can be added incrementally without forcing users to manually reorganize everything.

## Product Boundaries

Wikify is not just a project documentation generator. Project wikis are one important use case, but the broader object is a personal knowledge base.

Wikify is also not trying to become an Obsidian replacement, Notion replacement, or chat-first RAG app. The CLI remains the control surface, but the generated wiki must be a first-class human-facing outcome, not only an agent backend.

## Human And Agent Views

Design features around two consumers of the same wiki:

- Human Wiki: Markdown pages, static site output, readable index pages, source pages, topic pages, graph views, timelines, recent updates, and review queues.
- Agent Wiki: `llms.txt`, `llms-full.txt`, `graph.json`, context packs, citation indexes, related-topic queries, and stable JSON command outputs.

The same source of truth should feed both views. Avoid creating separate human-only and agent-only knowledge stores unless a future design explicitly justifies it.

## Architecture Direction

Prefer product and technical designs that follow this flow:

```text
Source Layer
  -> Incremental Ingest
  -> Wiki Core
  -> Link And Graph
  -> Human Views
  -> Agent Interfaces
  -> Maintenance Loop
```

The source layer registers raw material. The wiki core turns it into structured pages with type, purpose, links, and source traceability. The graph layer helps both people and agents navigate relationships. The maintenance loop should improve, deduplicate, and repair the wiki with low user interruption.

## Graphify And LLM Wiki Lessons

Absorb Graphify as a graph intelligence layer, not as a broad feature checklist. Valuable ideas include graph reports, god nodes, unexpected connections, relation provenance such as `EXTRACTED`, `INFERRED`, and `AMBIGUOUS`, cache-aware updates, query/path/explain commands, and agent installation guidance.

Absorb LLM Wiki as a wikiization and ingest model, not as a desktop app clone. Valuable ideas include incremental ingest, persistent queues, page types, source traceability, overview updates, and source-backed wiki pages.

Do not copy GPL code from `nashsu/llm_wiki`. Only product ideas, architecture lessons, and compatible behavior patterns may be reused.

## Product Language

Do not sell audit logs or rollback as the headline value. Treat them as trust infrastructure.

The user-facing promise should be closer to:

- Build a personal wiki from scattered knowledge.
- Let agents use that wiki as durable context.
- Keep the wiki readable for people.
- Keep every generated claim tied back to sources.
- Let automation run with confidence and recover when it is wrong.

## Agent Guidance

When changing this project, protect the product direction above. Prefer scoped, CLI-first, artifact-first features that make the wiki more useful to both humans and agents.

Before adding a feature, check whether it strengthens at least one of these loops:

- Add source -> wikiize -> browse.
- Add source -> wikiize -> agent context.
- Graph insight -> maintenance task -> verified improvement.
- Human review -> clearer wiki -> better agent retrieval.

Avoid GUI-first expansion, hidden provider behavior, opaque chat workflows, or broad platform integrations before the wiki object model, ingest flow, human views, and agent interfaces are stable.
