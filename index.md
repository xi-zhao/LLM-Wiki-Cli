# File Organizer Wiki Index

这是 `file-organizer/` 的公开总入口。

目标不是暴露某个私有 working knowledge base，
而是说明这套 LLM Wiki / `fokb` 产品的结构与使用方式。

## 1. 先看什么

- [README.md](./README.md) - GitHub 首页和产品定位
- [LLM-Wiki-Cli-README.md](./LLM-Wiki-Cli-README.md) - 完整产品说明
- [WIKI_SCHEMA.md](./WIKI_SCHEMA.md) - wiki 结构、对象层级、工作流
- [scripts/fokb_protocol.md](./scripts/fokb_protocol.md) - agent-facing JSON 协议
- [QUICKSTART.md](./QUICKSTART.md) - 最短上手路径

## 2. 公开仓库里保留什么

公开仓库优先保留：

- 产品文档
- CLI 与脚本
- 协议文档
- 测试
- 模板文件
- `sample-kb/` 这种 curated example

公开仓库默认**不**包含：

- 私有 working KB 的原文沉淀
- 大量真实 parsed / brief / topic / timeline 文件
- 本地运行态和临时状态

## 3. 推荐从哪里理解产品

### 如果你想看产品面
- 先看 [README.md](./README.md)
- 再看 [LLM-Wiki-Cli-README.md](./LLM-Wiki-Cli-README.md)

### 如果你想看知识库长什么样
- 直接看 [sample-kb/](./sample-kb/README.md)

### 如果你想接 agent / UI
- 直接看 [scripts/fokb_protocol.md](./scripts/fokb_protocol.md)

## 4. 目录角色

- `scripts/` - CLI 与工作流脚本
- `tests/` - 可公开运行的测试
- `sample-kb/` - 最小公共演示知识库
- `topics/_template.md` - topic 模板
- `timelines/_template.md` - timeline 模板
- `sources/index-template.md` - source index 模板

## 5. 一句话原则

这个 repo 发布的是：

**一个 agent-facing Markdown knowledge base system。**

不是某个人私有知识库的完整导出。
