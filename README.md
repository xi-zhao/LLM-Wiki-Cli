# Wikify

把链接、文件、仓库和笔记变成一个由 Agent 维护的本地 Wiki。

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![CLI](https://img.shields.io/badge/interface-CLI-black.svg)](docs/agent-operator-guide.md)

Wikify 是一个本地优先的个人知识库生成器，专门给正在使用 OpenClaw、Codex、Claude Code 等 Agent 的人用。

你对 Agent 说：

```text
帮我保存这篇文章：https://...
把这篇公众号文章整理进我的知识库。
把这个文件夹变成可浏览的项目 Wiki。
```

Agent 调用：

```bash
wikify ingest <locator>
```

Wikify 会把原始材料变成可读的 Markdown/静态 Wiki、可追溯的机器产物，以及 Agent 能长期调用的上下文文件。人类看到最终 Wiki。Agent 拿到稳定命令、JSON、引用、图谱上下文和恢复工具。

不是又一个笔记软件，也不是又一个聊天 RAG demo。

Wikify 是你的 Agent 和长期知识库之间的操作层。

## 为什么值得 Star

- **人类 Wiki：** Markdown 页面、来源页、主题索引、复查队列、图谱视图和本地静态 HTML。
- **Agent 记忆：** `llms.txt`、`llms-full.txt`、引用索引、相关主题查询、context packs 和稳定 JSON 输出。
- **恢复层：** 来源追踪、验证报告、patch rollback，以及用于大范围 Agent 编辑的 trusted operation snapshots。
- **本地优先：** 不需要托管账号，不强制向量数据库，不隐藏模型或 provider 调用。
- **Agent 原生：** 给 OpenClaw、Codex、Claude Code 和 shell agent 用，直接从 CLI 调用。

## 30 秒体验

```bash
git clone https://github.com/xi-zhao/LLM-Wiki-Cli.git
cd LLM-Wiki-Cli
python3 -m pip install -e .

wikify init ~/my-wiki
export WIKIFY_BASE="$HOME/my-wiki"

wikify ingest "https://example.com/article"
wikify views
```

打开：

```text
~/my-wiki/views/index.md
~/my-wiki/views/site/index.html
```

保存微信公众号文章：

```bash
wikify ingest https://mp.weixin.qq.com/s/example
```

## 人类应该看到什么

人类应该看到最终 Wiki 页面、相关页面，以及一段简短的变更总结。

正常情况下，人类不需要看队列、请求产物、JSON envelopes、验证报告或 Agent 上下文导出，除非是在排查问题。

更自然的入口是：人类说“帮我保存这篇文章”“整理这个文件夹”“把这个链接放进知识库”，Agent 负责调用 Wikify，最后把 Wiki 结果交回来。

## Agent 得到什么

给 OpenClaw、Codex、Claude Code 和 shell agent 用：

```bash
wikify ingest <locator>
wikify validate --strict --write-report
wikify views
wikify agent export
wikify agent context "what I am working on" --max-chars 12000 --max-pages 8
wikify agent cite "claim or title" --limit 10
wikify agent related "topic" --limit 10
```

一次成功的 ingest 会在这里写入 trusted agent request：

```text
.wikify/ingest/requests/
```

这个 trusted agent request 会告诉调用方 Agent：捕获了什么、清洗后的内容在哪里、当前 Wiki 上下文是什么、Agent 有多大操作权限、如何恢复，以及应该怎样把结果汇报给人类。

Agent 操作指南：[docs/agent-operator-guide.md](docs/agent-operator-guide.md)。

## Agent 改坏了怎么恢复

确定性的 patch bundle：

```bash
wikify apply --proposal-path <proposal.json> --bundle-path <bundle.json>
wikify rollback --application-path <application.json>
```

大范围 Wiki 重写、合并、拆分和清理，Agent 应该先使用 trusted operation snapshots：

```bash
wikify trusted-op begin --path wiki/pages/example.md --reason "merge imported article into existing topic"
# agent edits scoped wiki files
wikify trusted-op complete --operation-path .wikify/trusted-operations/op_<id>.json
wikify trusted-op rollback --operation-path .wikify/trusted-operations/op_<id>.json
```

Trusted operation snapshots 会记录编辑前后的文件内容和 hash。Rollback 只会在当前文件仍然匹配那次 completed operation 时执行，避免旧 rollback 覆盖新的人工或 Agent 修改。

## 它和别的工具有什么不同

| 工具类型 | 通常做什么 | Wikify 的角度 |
|----------|------------|---------------|
| 笔记软件 | 让你手动整理笔记 | 让 Agent 帮你整理有来源的 Wiki 页面 |
| 文档生成器 | 把一个 repo 转成文档 | 从链接、文件、仓库、笔记构建个人/项目知识库 |
| Chat RAG | 在不透明 chunks 上回答问题 | 先产出人能读的 Wiki，再提供 Agent context |
| Vector DB stack | 优化检索后端 | 从可检查的 Markdown、JSON、图谱和引用开始 |

## 核心流程

```text
Source layer
  -> Incremental ingest
  -> Wiki objects
  -> Links and graph
  -> Human views
  -> Agent interfaces
  -> Maintenance and recovery
```

人类视图和 Agent 接口来自同一个 source of truth。

## 现在能做什么

- 初始化本地 Wiki workspace。
- 注册文件、目录、URL、仓库和笔记。
- 通过显式保存命令 ingest 网页和微信公众号文章 URL。
- 把本地 sources 同步到确定性的队列；`wikify sync` 现在仍然不会抓取 URL sources。
- 生成有来源追踪的 Wiki 页面和 object artifacts。
- 渲染 Markdown views 和本地静态 HTML。
- 导出 `llms.txt`、`llms-full.txt`、页面索引、引用索引、相关主题索引、graph JSON 和 context packs。
- 生成图谱报告、坏链 findings、维护计划和 Agent task queues。
- 用显式外部 Agent 命令运行有边界的维护自动化。
- Apply、verify、rollback 确定性的 patch bundles。
- Snapshot 和 rollback 大范围 trusted-agent operations。

## 安装

从这个仓库安装：

```bash
python3 -m pip install -e .
```

然后：

```bash
wikify --help
wikify init ~/my-wiki
export WIKIFY_BASE="$HOME/my-wiki"
```

如果 Agent 运行在另一个 shell 或 Python 环境里，也要在那个环境里安装 Wikify。

## 给 Agent 的最小提示词

可以直接给 OpenClaw 这类 Agent：

```text
你可以使用 Wikify 作为我的本地知识库工具。
当我让你保存链接、文件、仓库或笔记时，调用 `wikify ingest <locator>`。
先阅读 docs/agent-operator-guide.md。
默认不要把队列、JSON envelopes、request artifacts 或验证报告展示给我。
最后只返回 Wiki 页面位置和简短变更总结。
```

## 深入文档

- Agent 操作指南：[docs/agent-operator-guide.md](docs/agent-operator-guide.md)
- 中文产品文档：[LLM-Wiki-Cli-README.md](LLM-Wiki-Cli-README.md)
- 协议参考：[scripts/fokb_protocol.md](scripts/fokb_protocol.md)
- 快速开始：[QUICKSTART.md](QUICKSTART.md)
- Schema 说明：[WIKI_SCHEMA.md](WIKI_SCHEMA.md)
- 示例知识库：[sample-kb/](sample-kb/)

## 状态

Alpha，但已经可以作为面向 Agent 的本地 Wiki 控制层使用。

核心闭环已经跑通：

```text
保存来源 -> Wiki 化 -> 浏览 -> 导出 Agent 上下文 -> 维护 -> 恢复
```

下一步成熟度来自更大规模的个人知识库和项目知识库实战。

## 许可证

MIT
