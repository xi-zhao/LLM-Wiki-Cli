# Trusted Agent Ingest Experience Design

**Date:** 2026-04-30
**Status:** Draft for review
**Scope:** Product experience direction for agent-driven knowledge ingest

## Problem

Wikify already has the beginnings of a unified ingest pipeline: sources can be saved, normalized, queued, wikiized, validated, and rendered into human-facing views. The remaining product problem is not only whether the pipeline works. The bigger problem is that the current language still makes humans think they should operate the pipeline themselves.

That is the wrong product center.

The human user should not need to understand `sync`, `wikiize`, queues, source items, graph exports, or agent context packs. A human should be able to say:

```text
帮我保存这篇文章
把这个链接整理进我的 wiki
这个文件帮我归档一下
以后让我能查到这篇内容
```

The agent should recognize the knowledge-ingest intent and call Wikify as a tool. Wikify should provide source traceability, workspace context, write support, snapshots, validation, and final wiki rendering. The final artifact people care about is the organized wiki, not the pipeline.

## Product Positioning

Wikify is the knowledge base operating system for trusted agents.

It is not:

- a human-first terminal app
- a generic webpage summarizer
- a Markdown conversion script
- a chat-first RAG app
- an Obsidian or Notion replacement

It is:

- a source traceability layer
- a wiki object layer
- an agent writeback layer
- a snapshot and rollback layer
- a human wiki rendering layer
- a stable CLI contract that agents can call

The strongest product promise is:

> Humans ask agents to save and organize knowledge. Agents use Wikify to turn source material into a traceable, recoverable, human-readable wiki.

## Target User

The first target user is a technical user who works through agents such as Codex, Claude Code, OpenClaw, or similar tools. This user is comfortable with CLI tools, but does not want to manually operate a multi-step knowledge pipeline.

This user wants:

- one natural-language request to the agent
- a high-quality wiki page as the visible outcome
- source-backed trust
- durable context for future agents
- recoverability when automation makes a bad edit

This user does not want:

- to manually choose low-level ingest stages
- to configure per-page templates
- to approve every agent decision
- to inspect artifact directories during normal use

## Primary Experience

The primary interaction is:

```text
Human:
  帮我保存这篇文章：https://...

Agent:
  recognizes save-and-organize intent
  calls wikify ingest <locator>
  reads Wikify's generated source/context artifacts
  autonomously writes or updates the wiki
  runs validation and refreshes views

Human:
  receives a concise knowledge-base change summary
  reads the final wiki page when desired
```

The human does not need to know that `wikify ingest` exists. The CLI is the agent-facing tool contract. Human-facing documentation may show examples for advanced technical users, but the product language should start with the natural-language flow.

## Default Meaning Of "Save This"

When a human says "save this article" or gives the agent a link or file, the default meaning is not "store the raw source only." The default meaning is:

```text
save source
-> organize into a high-quality wiki page
-> extract personal knowledge insights
-> place it into relevant topics
-> preserve source references
-> refresh the final wiki
```

For simple sources such as single articles, WeChat public account articles, Markdown files, text files, and focused webpages, the expected outcome is a finished knowledge page.

For complex sources such as large directories, repositories, long PDFs, or multi-document bundles, the trusted agent may decide to:

- save the source first
- produce an ingest plan
- split work into batches
- create multiple pages
- defer deep synthesis until more context is available

This is an agent judgment. The human should not be forced to choose between pipeline modes up front.

## Trusted Agent Model

Wikify should assume that the calling agent is trusted to maintain the wiki.

The agent has full autonomy to:

- create wiki pages
- edit existing generated pages
- restructure topics
- merge pages
- split pages
- rewrite low-quality pages
- delete or deprecate outdated pages
- update indexes, views, graph artifacts, and agent exports
- decide how a source should become one or more knowledge objects

Wikify should not put a human approval gate in front of normal agent work. Human review can exist as a later inspection surface, but it should not be the default control loop.

Wikify's responsibility is to make agent autonomy recoverable:

- preserve source refs
- record operations
- snapshot before destructive or broad writes
- validate object schemas
- refresh derived views
- expose rollback commands
- keep enough history for a later agent or human to understand what happened

Product principle:

> Give trusted agents full control over the wiki, while making every source, write, merge, and deletion traceable and recoverable.

## Permission And Recovery Semantics

Default permissions:

```text
read:
  all wiki pages, source records, artifacts, context packs, graph data

write:
  wiki pages, topics, views, graph artifacts, object artifacts, agent exports

reorganize:
  allowed

delete/merge:
  allowed with automatic snapshot

repair:
  allowed
```

Hard requirements:

- Source-backed pages must keep `source_refs`.
- Synthesis pages must identify themselves as synthesis rather than direct source extraction.
- Broad rewrites, deletes, merges, and splits should create automatic snapshots.
- Operation records should state what changed and why.
- Validation failures should be surfaced to the agent so the agent can repair them.
- Rollback should restore prior content without requiring the user to manually reconstruct files.

This is not a permission-denial model. It is a trusted-autonomy plus recovery model.

## Agent Work Context

When `wikify ingest <locator>` is called by an agent, Wikify should prepare a work context that gives the agent enough information to make good knowledge decisions.

The work context should include:

```text
source:
  original locator
  canonical locator
  source_id
  item_id
  capture time
  fingerprint evidence
  raw artifact paths

content:
  extracted title candidates
  author/source account candidates
  published time candidates
  cleaned body text
  cleaned Markdown when available
  extraction quality signals

workspace_context:
  existing topic index
  recent pages
  likely related pages
  graph summary
  duplicate or overlap candidates

task:
  user intent: save and organize into personal wiki
  expected outcome: source-backed knowledge page or ingest plan
  page quality standard

recovery:
  snapshot policy
  validation command
  rollback path
  operation log path
```

The agent should use this context to decide:

- final page title
- page structure
- related topics
- whether to update an existing page or create a new one
- whether to create or adjust topic pages
- which insights are worth preserving
- whether parts of the source are uncertain or low-quality

## High-Quality Page Standard

The default knowledge page should feel like a personal wiki entry, not a generic article summary.

Recommended structure:

```markdown
# Page Title

## 一句话结论
The one durable judgment or idea worth remembering.

## 为什么值得保存
Why this material matters to the user's knowledge system, projects, decisions, or future tasks.

## 核心观点
- The main claims, concepts, or mechanisms.

## 可复用洞察
- When the user may want to recall this.
- What mental model, checklist, or decision rule it provides.
- How it should influence future work.

## 相关主题
- [[Topic A]]
- [[Topic B]]

## 和已有知识的关系
- 补充: [[Existing Page]]
- 冲突: [[Existing Page]]
- 可合并: [[Existing Page]]

## 来源依据
- Original URL or file path.
- Capture time.
- Author/account/published time when available.
- Key source evidence or excerpt references.
```

The first visual layer should emphasize conclusion, value, and insight. Metadata and evidence should be present, but should not dominate the page.

For WeChat public account articles, the agent should preserve:

- original title
- account name when available
- author when available
- publish time when available
- canonical URL
- capture time
- extraction quality warnings

## Human Completion Summary

When the agent finishes, the human should receive a knowledge-base change summary, not pipeline logs.

Recommended successful response:

```text
已保存并整理进你的 wiki。

新增知识页：
- 《xxx》 -> wiki/pages/xxx.md

这篇内容被归入：
- [[个人知识库]]
- [[Agent 工作流]]

我提炼出的长期价值：
- ...
- ...

同时更新了：
- 主题页：2 个
- 最近更新页：1 个
- graph/index：已刷新

来源已保留，可回溯到原文。
```

Recommended failure response:

```text
这篇文章还没有成功入库。

原因：
- 页面正文抓取质量不足，可能需要登录或手动提供 HTML。

我已经保留了：
- 原始链接
- 本次抓取记录
- 待处理任务

你可以直接发我网页 HTML 或正文，我会继续整理。
```

Human-facing feedback should answer:

- What was added?
- What was changed?
- Where can I read it?
- Which topics now include it?
- What long-term value did the agent extract?
- Is the source preserved?
- What should happen next if it failed?

It should not require the human to understand `source_id`, `queue_id`, raw artifacts, or validation reports.

## Command And Documentation Language

README and command help should move away from:

```text
Humans should normally run wikify ingest <locator>.
```

Preferred product language:

```text
Humans ask their agent to save or organize knowledge.
Agents call Wikify to ingest, structure, validate, and update the wiki.
Humans read the final wiki.
```

Technical docs can still document `wikify ingest` directly, but they should describe it as an agent tool contract first and a direct advanced CLI command second.

## End-To-End Flow

```text
1. Human gives the agent a natural-language request.
   "帮我保存这篇文章：https://..."

2. Agent identifies a knowledge-ingest intent.

3. Agent calls Wikify.
   wikify ingest <locator>

4. Wikify saves the source and creates traceable artifacts.

5. Wikify prepares trusted agent work context.

6. Agent autonomously organizes the source into the wiki.
   It may create, update, merge, split, or delete pages as needed.

7. Wikify snapshots risky changes, validates objects, and refreshes views.

8. Agent gives the human a concise knowledge-base change summary.
```

## Implementation Phases

### Phase 1: Product Language Correction

Update README, help text, and docs so the default product story is:

```text
human intent -> agent tool call -> final wiki
```

Make `sync`, `wikiize`, queues, validation reports, and agent exports clearly lower-level machine surfaces.

### Phase 2: Trusted Agent Ingest Context

Extend `wikify ingest` artifacts so the calling agent receives a complete work context:

- source metadata
- cleaned content
- related topic candidates
- existing related pages
- graph summary
- page quality standard
- snapshot and validation instructions

### Phase 3: Page Quality Contract

Define and test the expected structure for high-quality personal wiki pages:

- conclusion
- why worth saving
- core ideas
- reusable insights
- related topics
- relationship to existing knowledge
- source evidence

This should be a contract for agent output, not a rigid human-facing template that users must configure.

### Phase 4: Snapshot And Operation Records

Make trusted full-control safe by default:

- snapshot before broad rewrites, merges, splits, or deletes
- record operation summaries
- expose rollback paths
- keep validation results tied to operations

### Phase 5: Human Completion Summary

Provide a standard machine-readable completion summary that agents can translate into human-facing replies:

- added pages
- updated pages
- related topics
- extracted long-term value
- source preservation status
- warnings and next steps

## Acceptance Criteria

The experience is successful when:

- A human can ask an agent to save an article without mentioning Wikify commands.
- The agent can call Wikify and receive enough context to decide how to organize the source.
- A single article becomes a high-quality personal wiki page by default.
- The page includes source evidence without making metadata the main reading experience.
- The agent can restructure the wiki without human approval.
- Risky writes produce snapshots and operation records.
- The final response to the human describes wiki changes, not pipeline internals.
- The human can read the final wiki and trust that the source is recoverable.

## Non-Goals

- No GUI-first workflow.
- No human approval gate for every agent decision.
- No per-source manual template selection.
- No hidden claim that Wikify itself is the reasoning model.
- No requirement that normal users understand internal artifacts.
- No removal of lower-level CLI commands; they remain useful for agents, debugging, and recovery.
