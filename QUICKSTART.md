# fokb Quickstart

`fokb` 是一个面向 agent 的本地知识库 CLI，目前处于 alpha。

## 1. 安装

```bash
pip install -e .
```

## 1.5 先试公开 sample-kb（推荐）

```bash
export FOKB_BASE="$(pwd)/sample-kb"
fokb stats
fokb show agent-knowledge-loops --scope topics
fokb digest agent-knowledge-loops.md
```

如果你只是先想看 repo 长什么样，这一步最省事。

## 2. 初始化

```bash
fokb init
```

## 3. 自检

```bash
fokb check
```

如果返回 `ok: true`，说明基础环境可用。

## 4. 查看状态

```bash
fokb status
fokb --output pretty status
```

## 5. 搜索和取上下文

```bash
fokb search "quantum"
fokb query "quantum financing"
fokb writeback "quantum financing" --title "Quantum Financing Notes"
fokb synthesize "quantum financing" --mode outline --title "Quantum Financing Outline"
```

## 6. 入库一个链接

```bash
fokb ingest "https://example.com"
```

## 7. 查看 review 队列

```bash
fokb review --summary
fokb review --urls-only
```

## 8. 重跑或出队

```bash
fokb reingest --last
fokb resolve --last
```

## 可选：自定义知识库目录

```bash
export FOKB_BASE=/path/to/your-kb
fokb init
fokb check
```

公开仓库建议保留 `sample-kb/` 这种 curated example，把真实 working KB 放到另一个目录或私有仓库里。
