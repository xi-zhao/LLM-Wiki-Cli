---
type: topic
tags:
  - topic
  - obsidian
  - agent-knowledge-loops
---

# Topic: Agent Knowledge Loops

## 笔记关系
- Topics MOC: [[topics-moc]]
- Source Index: [[sources-index]]
- Related Digest: [[agent-knowledge-loops-digest]]

## 主题定义
- Agent knowledge loops describe how an agent ingests, restructures, maintains, and reuses knowledge over time.

## 当前核心问题
- How should raw materials and compiled notes be separated?
- Which outputs should be optimized for agents versus humans?

## 稳定结论
- JSON contracts are better for agents than natural-language-only command output.
- Markdown remains a strong human-facing source of truth for review and editing.
- Obsidian-facing navigation can coexist with agent-facing CLI contracts.

## 新增观察
- A public repo should ship a sample KB instead of a private working KB.
- Completion and maintenance feedback make write operations much easier to automate safely.

## 代表性案例 / 证据
- [Agent knowledge loops as a markdown-first workflow](../articles/parsed/2026-04-10_agent-knowledge-loops.md)

## 可输出方向
- A public README for agent-facing knowledge tooling
- A design note on JSON-for-agents and Markdown-for-humans

## 关联文章
- [Agent knowledge loops as a markdown-first workflow](../articles/parsed/2026-04-10_agent-knowledge-loops.md)

## 待跟进
- How to package a reusable sample KB for public repos
- Whether to ship CI and release templates in the first public version
