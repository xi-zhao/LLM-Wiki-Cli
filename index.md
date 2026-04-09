# LLM Wiki Index

这是这套 LLM Wiki 的总入口。

优先阅读顺序：先看这里，再决定进入 topic、timeline、parsed 还是 raw。

## 1. 核心 Schema
- [WIKI_SCHEMA.md](./WIKI_SCHEMA.md) - 结构、工作流和维护规则
- [README.md](./README.md) - 产品速览
- [sources/index.md](./sources/index.md) - 来源索引样例

## 2. 示例对象
- [量子计算产业](./topics/quantum-computing-industry.md) - 一个最小 topic 示例
- [量子计算产业时间线](./timelines/quantum-computing-industry.md) - 一个最小 timeline 示例

## 3. 使用约定
1. 默认入口：`python3 scripts/ingest_any_url.py "<url>"`
2. 原文进 `articles/raw/`
3. 结构化卡进 `articles/parsed/`
4. 快速简报进 `articles/briefs/`
5. 更新一个或多个 `topics/`
6. 需要时更新 `timelines/`
7. 在 `sources/index.md` 追加来源记录

## 4. 发布说明
当前仓库刻意保留为最小可发布产品面，只附带少量样例对象用于测试和演示。
