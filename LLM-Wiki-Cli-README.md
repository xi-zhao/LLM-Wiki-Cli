# Wikify

Wikify 是一个 **面向 agent 的 Markdown 知识库控制 CLI**。

它明确参考了 Andrej Karpathy 提出的 LLM Wiki / markdown-first knowledge workflow 思路，但不是照搬个人 wiki 展示层，而是把这条路线继续产品化成 agent 可调用的控制面。

它不是一个给人类手工点来点去的终端玩具，也不是一组松散脚本的集合。
它的目标很明确：

- 给 agent 一个稳定的知识库控制入口
- 让 agent 能以结构化方式读状态、做判断、触发动作、追踪执行结果
- 把 markdown wiki 维护、增量知识推理和动作执行串成一条可审计的 control loop

当前主入口是：

```bash
wikify ...
```

兼容入口仍然保留：

```bash
fokb ...
```

`fokb` 是旧名兼容别名，新文档和新自动化应优先使用 `wikify`。

---

# 1. 产品定位

Wikify 解决的不是“如何写 markdown 文件”这个问题，
而是“如何在 Karpathy 那种 markdown-first、可持续维护的 LLM Wiki 思路之上，让 agent 稳定地维护一个可增长、可检查、可决策、可执行的知识库”。

它的核心不是展示，而是控制；Graphify 融合后的新增重点是结构理解。

## 适用场景

适合以下场景：

- agent 把网页、微信文章、本地材料持续归档进 markdown wiki
- agent 需要从现有知识对象中检索上下文、生成整理输出、沉淀 topic/timeline
- agent 需要根据增量变更做维护判断，而不是每次全库重扫
- agent 需要根据维护结论自动给出下一步动作建议，必要时执行动作
- agent / UI / 自动化脚本需要消费稳定 JSON，而不是依赖自然语言 stdout
- agent 需要读取 `graph.json` / `GRAPH_REPORT.md` 来理解 wiki 的中心节点、社区、孤立对象和断链

## 不是什么

Wikify 不是：

- 面向普通终端用户的交互式 UI
- 只会 ingest 的单用途脚本
- 依赖 pretty 输出文案才能用的 CLI
- 单纯的全文搜索工具

---

# 2. 产品目标

Wikify 的产品目标可以概括成五句话：

1. **统一入口**
   - 所有 agent-facing 能力优先挂到 `wikify` 子命令
2. **结构化输出**
   - 所有结果都走稳定 envelope
3. **增量维护**
   - 维护逻辑围绕 changed object，而不是只靠全量 lint
4. **控制闭环**
   - 写入 -> maintenance -> decision -> execution -> history/state
5. **结构理解**
   - Markdown wiki -> graph index -> analytics -> report/html/json

---

# 3. 核心能力

## 3.1 环境与状态

- `init`
- `check`
- `status`
- `stats`
- `state`

作用：
- 初始化目录结构和状态文件
- 检查运行环境
- 返回机器可读的系统状态与聚合视图

## 3.2 入库与工作流

- `ingest`
- `reingest`
- `resolve`
- `digest`
- `promote`

作用：
- 统一入库链接
- 重跑 review item
- 出队 review item
- 生成 digest
- 把候选对象提升为稳定 topic

### digest 自动化规则
`digest` 是二阶段整理动作，不默认与 `ingest` 绑死。

默认策略：
- `ingest` / `reingest` 先完成入库、路由、topic 更新和 completion 回执
- `digest_optional` 只表示“允许继续做摘要收束”，不是“必须立刻做”

建议自动触发条件：
- `review_required = false`
- `lifecycle_status = integrated`
- 存在 `primary_topic`
- 本次确实更新了 topic
- `next_actions` 包含 `digest_optional`

CLI 输出里可直接读取：
- `result.digest_policy.eligible`
- `result.digest_policy.mode`
- `result.digest_policy.recommended_action`
- `result.digest_policy.blocking_reasons`

建议抑制条件：
- 需要 review
- 没有命中稳定 topic
- 只是完成抓取/解析，没有稳定 topic 更新

强制触发方式：
- `digest <topic>`
- `ingest --with-digests`
- `reingest --with-digests`

## 3.3 对象层查询

- `list`
- `search`
- `show`
- `query`

作用：
- 列出对象
- 搜索 markdown wiki
- 展示对象内容
- 抽取 query context 给下游 agent 使用

## 3.4 产出层

- `writeback`
- `synthesize`

作用：
- 基于 query context 写回整理结果
- 生成结构化 synthesis markdown

## 3.5 Obsidian 收口方向
当前产品记录格式正在往 Obsidian-native 收：
- digest 输出优先使用 frontmatter + `[[wikilink]]`
- topic 主笔记补 `笔记关系` 和 `关联笔记（Obsidian）`
- parsed/article note 与 brief note 也补 frontmatter、`笔记关系` 与 Obsidian 链接
- 自动生成 `topics-moc.md` 与 `sources/sources-index.md` 作为导航页
- digest 生成后会自动刷新这些导航页
- 同时暂时保留现有 markdown 路径链接和 `关联主题` 字段，避免破坏 maintenance / ingest 兼容链路

## 3.5 巡检与维护

- `lint`
- `lint --deep`
- `maintenance`
- `maintain`
- `decide`

作用：
- 基础巡检和全库深巡检
- 查询 maintenance history
- 基于 graph 自动生成 findings、plan 和 history，不打断用户
- 根据 maintenance verdict 产出下一步 decision plan

## 3.6 图谱结构层

- `graph`

作用：
- 从已编译的 Markdown wiki 中重建本地图谱
- 提取 `[[wikilink]]`、Markdown 链接和 topic/article/source 结构关系
- 输出 `graph/graph.json`、`graph/GRAPH_REPORT.md` 和可选 `graph/graph.html`
- 帮 agent 发现中心节点、社区、孤立对象、断链和下一步维护问题

默认命令：

```bash
wikify graph
wikify graph --no-html
wikify graph --scope topics
```

`graph` 在 V1 中是 read-mostly 命令：只写 `graph/` 目录，不修改 topic、parsed、review queue 或 maintenance history。

## 3.7 自动图谱维护层

- `maintain`

作用：
- 自动执行 `graph --no-html`
- 基于 `graph.analytics` 生成断链、孤立对象、中心节点、成熟社区和薄图谱 findings
- 根据 `--policy conservative|balanced|aggressive` 生成维护计划
- 把可安全执行的确定性动作标记为 executed，把语义修复和生成内容动作交给 agent 队列
- 把 queued plan step 转成 `graph-agent-tasks.json`，让后续 agent 可直接消费
- 写入可审计产物，供后续 agent 自动审核

默认命令：

```bash
wikify maintain
wikify maintain --dry-run
wikify maintain --policy conservative
wikify maintain --policy balanced
wikify maintain --policy aggressive
```

输出产物：
- `graph/graph.json`
- `graph/GRAPH_REPORT.md`
- `sorted/graph-findings.json`
- `sorted/graph-maintenance-plan.json`
- `sorted/graph-agent-tasks.json`
- `sorted/graph-maintenance-history.json`

`--dry-run` 只写 graph 产物，不写 `sorted/` 下的维护审核产物。

`graph-agent-tasks.json` 是后续 agent 的任务包，而不是人类 checklist。每条任务包含 source finding、action、priority、target、evidence、write scope、agent instructions、acceptance checks、`requires_user: false` 和 `status: queued`。

V1 安全规则：`maintain` 不修改 topic、parsed、sorted 等正文页面，也不在 CLI 内隐藏调用 LLM；断链修复、孤立对象挂接、digest 刷新和 community synthesis 都只进入 plan 和 agent task queue，由后续 agent 审核或执行。

---

# 4. 知识库对象模型

Wikify 默认面向如下目录结构工作：

- `articles/raw` 原文留底
- `articles/parsed` 结构化文章卡
- `articles/briefs` 一页式摘要
- `topics` 长期主题知识卡
- `timelines` 行业/赛道时间线
- `sources` 来源索引
- `materials/wechat` 公众号素材包
- `materials/web` 普通网页素材包
- `materials/local` 本地整理材料
- `archive` 归档
- `sorted` 已整理输出

其中最关键的 agent-facing 对象类型是：

- `parsed`
- `topics`
- `timelines`
- `sorted`

maintenance / decision / execution 的很多推理都围绕这些对象类型展开。

---

# 5. 输出协议

## 5.1 统一 envelope

所有子命令默认输出 JSON envelope。

成功：

```json
{
  "ok": true,
  "command": "status",
  "exit_code": 0,
  "result": {}
}
```

失败：

```json
{
  "ok": false,
  "command": "reingest",
  "exit_code": 2,
  "error": {
    "code": "review_item_not_found",
    "message": "review item not found",
    "retryable": false,
    "details": {}
  }
}
```

## 5.2 输出模式

- `--output json` 默认，给 agent / UI / 脚本使用
- `--output pretty` 调试友好
- `--output quiet` 只保留 exit code

### 推荐原则

对 agent / UI：
- 优先消费 JSON 字段
- 不要依赖 pretty 输出文案
- 不要依赖 `error.message` 的具体措辞

---

# 6. Maintenance 协议

`maintenance` 是 Wikify 的核心协议层之一。

它不是附属字段，而是：

- 写操作后的即时结果
- history 中的持久化记录
- `maintenance` 命令的查询主体
- `stats` / `state` 的重要状态来源

## 6.1 顶层结构

```json
{
  "checked": true,
  "scope": "incremental",
  "verdict": "needs_promotion",
  "signals": [],
  "suggestions": [],
  "warnings": [],
  "changed_paths": [],
  "touched_types": [],
  "changed_objects": []
}
```

## 6.2 维护特点

当前 maintenance 已经不只是 lint 压缩视图，而是增量知识维护引擎，主要包含：

- changed-object inference
- neighborhood inference
- claim extraction
- contradiction detection
- source-aware weighting
- recency-aware weighting
- verdict synthesis

## 6.3 verdict registry

- `stable`
- `watch`
- `conflicted`
- `emerging`
- `needs_promotion`

---

# 7. Decision 协议

`decide` 是 agent workflow 的最小决策接线入口。

它的作用不是输出一段解释，而是产出一份可机械消费的下一步 plan。

## 7.1 推荐输入方式

优先使用：

```bash
wikify decide --maintenance-path <path>
```

兼容模式：

```bash
wikify decide --last
```

原因是：
- `--maintenance-path` 明确指定决策输入来源
- `--last` 只是读取 history 最后一条，适合兼容，不适合要求严格 workflow 语义的场景

## 7.2 decision schema

当前 decision 既保留兼容字段，也提供 agent 应优先消费的新字段。

```json
{
  "decision": {
    "verdict": "needs_promotion",
    "actions": [],
    "rationale": [],
    "promotion_targets": [],
    "steps": []
  },
  "decision_source": {}
}
```

### 兼容字段

- `decision.actions`
- `decision.rationale`
- `decision.promotion_targets`

### 推荐字段

- `decision.steps`
- `decision_source`

## 7.3 step schema

```json
{
  "action": "promote_to_topic_or_timeline",
  "target": "/path/to/object.md",
  "args": {
    "path": "/path/to/object.md"
  },
  "can_execute": true,
  "idempotent": true,
  "retryable": true,
  "reason": "maintenance verdict indicates stable promotion opportunity",
  "expected_result": "topic_created_or_already_exists"
}
```

### 当前 step 设计目标

让 agent 不再自己拼：
- action
- target
- args

而是直接消费 step plan。

---

# 8. Execution 协议

当使用：

```bash
wikify decide --maintenance-path <path> --execute
```

系统会直接消费 decision steps，并返回统一 execution result。

## 8.1 execution result schema

```json
{
  "action": "promote_to_topic_or_timeline",
  "target": "/path/to/object.md",
  "status": "promoted",
  "reason": "topic_created_from_sorted",
  "result": {},
  "artifacts": {
    "created": [],
    "updated": [],
    "skipped": []
  },
  "state_change": {},
  "side_effects": []
}
```

## 8.2 设计原则

- `result` 保留 action 原始结果，方便兼容和调试
- `artifacts` 提供统一对象变化视图
- `state_change` 提供控制语义摘要
- `side_effects` 提供轻量副作用标签

这样 agent 不必理解每个 action 的私有返回形状。

---

# 9. Provenance / History / State

为了让 workflow 可审计、可回放，Wikify 把执行来源正式写入 history/state。

## 9.1 maintenance history entry schema

```json
{
  "command": "decide",
  "maintenance": {},
  "provenance": {}
}
```

## 9.2 provenance schema

```json
{
  "trigger": "decide --execute",
  "parent_command": "decide",
  "execution_mode": "decision_execute",
  "decision": {},
  "execution": {},
  "decision_source": {}
}
```

## 9.3 作用

provenance 用来回答：

- 这条 maintenance 是由哪个 command 触发的
- 是人工 action 还是 decision-driven execution
- 它基于什么输入做出 decision
- 实际执行了哪些 step
- 最终 side effect 是什么

## 9.4 查询入口

- `maintenance --last`
- `maintenance --limit N`
- `state`
- `stats`

---

# 10. 典型工作流

## 10.1 查询上下文并生成整理结果

```bash
wikify query "quantum financing"
wikify synthesize "quantum financing" --mode outline --title "Quantum Financing Outline"
```

## 10.2 生成 decision plan

```bash
wikify decide --maintenance-path /absolute/path/to/sorted/object.md
```

## 10.3 直接执行 decision

```bash
wikify decide --maintenance-path /absolute/path/to/sorted/object.md --execute
```

## 10.4 查询执行后的维护记录

```bash
wikify maintenance --last
wikify state
```

## 10.5 手动 promote

```bash
wikify promote /absolute/path/to/sorted/object.md
```

---

# 11. 推荐调用方式

## 11.1 对 agent

优先读取：

- `ok`
- `exit_code`
- `command`
- `error.code`
- `error.retryable`
- `result.maintenance.verdict`
- `result.maintenance.changed_objects`
- `result.decision.steps`
- `result.decision_source`
- `result.execution.executed`

## 11.2 对后台控制面板 / UI

优先读取：

- `stats`
- `maintenance --last`
- `maintenance --limit N`
- `state`

## 11.3 不建议依赖

- pretty 输出文案
- 原始 stdout 的排列顺序
- `error.message` 的措辞细节
- 兼容字段之外的私有 action 结果细节

---

# 12. Exit Code

- `0` 成功
- `1` 执行失败 / 子命令失败 / 内部异常
- `2` not found
- `3` quality gated
- `4` review required
- `5` environment check failed
- `6` deep lint warning

---

# 13. 目前已经具备的产品特征

当前版本已经具备以下产品级特征：

- 单一主入口 `wikify`
- 稳定 envelope
- 增量 maintenance 协议
- step-based decision contract
- 统一 execution result contract
- provenance schema
- history/state 可查询
- 兼容旧历史的 lazy normalization
- 端到端 control loop 已跑通

因此，它已经可以视为：

## **第一版完整可用的 agent-facing 产品**

不是最终版，但已经不是 demo 或脚本堆。

---

# 14. 当前已知边界

当前仍然存在这些明确边界：

- `claim extraction` 仍然是 heuristic v1，不是完整语义解析
- `canonical_subject` 仍然是弱归一化，不是完整 entity resolution
- 零上下文 synthesis 可能没有 neighbors / claims / contradictions，这属于正常行为
- 某些模板噪声、slug fragment、占位词仍可能进入概念提取，需要继续降噪
- `decide --last` 仍属于兼容模式，严格 workflow 场景推荐使用 `--maintenance-path`

---

# 15. 安装与运行

## 15.1 直接运行

```bash
wikify init
wikify check
```

## 15.2 本地安装

在 `file-organizer/` 目录下：

```bash
pip install -e .
```

安装后：

```bash
wikify init
wikify check
wikify stats
```

## 15.3 路径约定

默认情况下，`wikify` 会把项目包所在目录识别为知识库根目录。

如果要在其他路径运行，可显式设置：

```bash
export WIKIFY_BASE=/path/to/file-organizer
```

---

# 16. 与现有文档的关系

更底层的结构化协议定义见：

- `file-organizer/scripts/fokb_protocol.md`

脚本入口索引见：

- `file-organizer/scripts/README.md`

本文档的角色不是替代协议文档，而是：

## **把 Wikify 作为产品讲清楚**

也就是说明：
- 它是什么
- 它解决什么问题
- 它怎么被 agent 使用
- 它当前的稳定面在哪里
- 它的边界在哪里

---

# 17. 一句话总结

Wikify 是一个把 **markdown wiki、增量知识维护、decision plan、动作执行和状态审计** 串成统一控制回路的 agent-facing CLI。

如果你要的是“让 agent 真正能稳定维护知识库”的产品，而不是“又一个脚本”，它就是这条线上的正确收口。
