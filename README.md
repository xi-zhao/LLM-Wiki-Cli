# Wikify

Turn links, files, repos, and notes into an agent-maintained local wiki.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![CLI](https://img.shields.io/badge/interface-CLI-black.svg)](docs/agent-operator-guide.md)

Wikify is a local-first knowledge base generator for people who use agents.

You tell an agent:

```text
Save this article to my wiki: https://...
Make this WeChat public account article easy to find later.
Organize this folder into my knowledge base.
```

The agent calls:

```bash
wikify ingest <locator>
```

Wikify turns the source into a readable Markdown/static wiki, source-backed machine artifacts, and agent-ready context files. Humans get the wiki. Agents get stable commands, JSON, citations, graph context, and rollback tools.

Not another notes app. Not another chat RAG demo.

Wikify is the operating layer between your agents and your long-term knowledge base.

## Why Star Wikify?

- **Human wiki:** Markdown pages, source pages, topic indexes, review queues, graph views, and local static HTML.
- **Agent memory:** `llms.txt`, `llms-full.txt`, citation indexes, related-topic queries, context packs, and stable JSON outputs.
- **Recovery layer:** source traceability, validation, patch rollback, and trusted operation snapshots for broad agent edits.
- **Local-first:** no hosted account, no mandatory vector database, no hidden provider calls.
- **Agent-native:** designed for OpenClaw, Codex, Claude Code, and shell agents to call directly.

## 30-Second Demo

```bash
git clone https://github.com/xi-zhao/LLM-Wiki-Cli.git
cd LLM-Wiki-Cli
python3 -m pip install -e .

wikify init ~/my-wiki
export WIKIFY_BASE="$HOME/my-wiki"

wikify ingest "https://example.com/article"
wikify views
```

Open:

```text
~/my-wiki/views/index.md
~/my-wiki/views/site/index.html
```

For WeChat public account articles:

```bash
wikify ingest https://mp.weixin.qq.com/s/example
```

## What Humans Should See

What humans should see is the final wiki entry, related pages, and a short change summary.

They should not need to inspect queues, request artifacts, JSON envelopes, validation reports, or agent context exports unless they are debugging.

Humans should normally ask their agent to save or organize knowledge. Wikify is the tool the agent uses behind that request.

## What Agents Get

For OpenClaw, Codex, Claude Code, and shell agents:

```bash
wikify ingest <locator>
wikify validate --strict --write-report
wikify views
wikify agent export
wikify agent context "what I am working on" --max-chars 12000 --max-pages 8
wikify agent cite "claim or title" --limit 10
wikify agent related "topic" --limit 10
```

Successful ingest writes a trusted agent request under:

```text
.wikify/ingest/requests/
```

The trusted agent request tells the calling agent what was captured, where cleaned content lives, what the current wiki context is, how much control the agent has, how to recover, and how to summarize the result for the human.

Agent operator guide: [docs/agent-operator-guide.md](docs/agent-operator-guide.md).

## Recovery For Agent Edits

For deterministic patch bundles:

```bash
wikify apply --proposal-path <proposal.json> --bundle-path <bundle.json>
wikify rollback --application-path <application.json>
```

For broad wiki rewrites, merges, splits, and cleanup, agents should use trusted operation snapshots:

```bash
wikify trusted-op begin --path wiki/pages/example.md --reason "merge imported article into existing topic"
# agent edits scoped wiki files
wikify trusted-op complete --operation-path .wikify/trusted-operations/op_<id>.json
wikify trusted-op rollback --operation-path .wikify/trusted-operations/op_<id>.json
```

Trusted operation snapshots record before/after file content and hashes. Rollback only runs when the current files still match the completed operation, so stale rollback does not overwrite newer work.

## How It Differs

| Tool type | What it usually does | Wikify's angle |
|-----------|----------------------|----------------|
| Notes app | You manually organize notes | Agents organize source-backed wiki pages for you |
| Docs generator | Converts one repo into docs | Builds a personal/project knowledge base from many sources |
| Chat RAG | Answers questions over opaque chunks | Produces readable wiki artifacts and stable agent context |
| Vector DB stack | Optimizes retrieval backend | Starts with inspectable Markdown, JSON, graph, and citations |

## Core Flow

```text
Source layer
  -> Incremental ingest
  -> Wiki objects
  -> Links and graph
  -> Human views
  -> Agent interfaces
  -> Maintenance and recovery
```

The same source of truth feeds both humans and agents.

## Current Capabilities

- Initialize a local wiki workspace.
- Register files, directories, URLs, repositories, and notes.
- Ingest web and WeChat article URLs through an explicit save command.
- Sync local sources into deterministic queues. `wikify sync still does not fetch URL sources`.
- Generate source-backed wiki pages and object artifacts.
- Render Markdown views and local static HTML.
- Export `llms.txt`, `llms-full.txt`, page indexes, citation indexes, related indexes, graph JSON, and context packs.
- Build graph reports, broken-link findings, maintenance plans, and agent task queues.
- Run bounded maintenance automation with explicit external agent commands.
- Apply, verify, and rollback deterministic patch bundles.
- Snapshot and rollback broad trusted-agent operations.

## Install

From this repository:

```bash
python3 -m pip install -e .
```

Then:

```bash
wikify --help
wikify init ~/my-wiki
export WIKIFY_BASE="$HOME/my-wiki"
```

If an agent runs in a different shell or Python environment, install Wikify in that environment too.

## Minimal Agent Prompt

Give this to an agent such as OpenClaw:

```text
Use Wikify as my local knowledge-base tool.
When I ask you to save a link, file, repo, or note, call `wikify ingest <locator>`.
Read docs/agent-operator-guide.md.
Do not show me queues, JSON envelopes, request artifacts, or validation reports by default.
Return the final wiki page location and a short summary of what changed.
```

## Deep Docs

- Agent operating guide: [docs/agent-operator-guide.md](docs/agent-operator-guide.md)
- Chinese product doc: [LLM-Wiki-Cli-README.md](LLM-Wiki-Cli-README.md)
- Protocol reference: [scripts/fokb_protocol.md](scripts/fokb_protocol.md)
- Quickstart: [QUICKSTART.md](QUICKSTART.md)
- Schema notes: [WIKI_SCHEMA.md](WIKI_SCHEMA.md)
- Sample knowledge base: [sample-kb/](sample-kb/)

## Status

Alpha, but usable as an agent-facing local wiki control plane.

The core loop is working:

```text
save source -> wikiize -> browse -> export agent context -> maintain -> recover
```

The next maturity step is real-world use with larger personal and project knowledge bases.

## License

MIT
