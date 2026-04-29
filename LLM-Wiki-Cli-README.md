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
- `source add`
- `source list`
- `source show`
- `sync`
- `wikiize`
- `check`
- `status`
- `stats`
- `state`

作用：
- 初始化个人 wiki workspace、目录结构和状态文件
- 登记个人知识库的增量 source registry
- 检查运行环境
- 返回机器可读的系统状态与聚合视图

### 个人 wiki workspace 与 source registry

`wikify init [BASE]` 会创建一个以个人知识库为中心的 workspace：

- `wikify.json`
- `.wikify/registry/sources.json`
- `sources/`
- `wiki/`
- `artifacts/`
- `views/`

`wikify source add <locator> --type <type>` 只做 source 登记，不做抓取、clone、同步、wiki 化、graph 构建或 provider 调用。

支持的 source type：

- `file`
- `directory`
- `url`
- `repository`
- `note`

source registry 的价值是给 agent 一个稳定、增量、可查询的知识入口。每个 source 会得到 `src_<uuid>`，登记时记录 canonical locator、本地文件 fingerprint 或远程未校验状态，并把 `last_sync_status` 设为 `never_synced`。后续 sync、parse、wikiize、view、agent export 都应该是显式命令，不隐藏在 `source add` 里。

基础流程：

```bash
wikify init ~/personal-wiki
export WIKIFY_BASE="$HOME/personal-wiki"
wikify source add ~/notes/research.md --type file
wikify source add "https://example.com/report" --type url
wikify source list
wikify source show src_<id>
wikify sync --dry-run
wikify sync
wikify sync --source src_<id>
wikify wikiize --dry-run
wikify wikiize
```

base 解析优先级：

1. `WIKIFY_BASE`
2. `FOKB_BASE`
3. 当前目录或父目录中的 `wikify.json`
4. 应用根目录兼容 fallback

### 增量 sync 与 ingest queue

`wikify sync` 会离线扫描 source registry 中的 source，生成 source item 状态和后续 wiki 化队列。它把每个 item 分类为 `new`、`changed`、`unchanged`、`missing`、`skipped`、`errored`。

写入的控制面 artifact：

- `.wikify/sync/source-items.json`，schema 为 `wikify.source-items.v1`
- `.wikify/sync/last-sync.json`，schema 为 `wikify.sync-run.v1`
- `.wikify/queues/ingest-items.json`，schema 为 `wikify.ingest-queue.v1`

常用命令：

```bash
wikify sync
wikify sync --source src_<id>
wikify sync --dry-run
```

`--dry-run` 只返回计划中的 registry 与 queue 变化，不写 `.wikify/sync/`、`.wikify/queues/`，也不更新 registry sync metadata。重复 sync 且内容没有变化时，item 会变成 `unchanged`，不会重复创建 queue entry。

队列规则：只有 `new` 和 `changed` item 会进入 active pending wikiization work；`missing`、`skipped`、`errored` 只进入状态 artifact，不进入 active queue。

边界规则：`wikify sync` 不会抓取 URL、不会 clone repository、不会调用 provider、不会运行 `wikify ingest`、不会生成 wiki 页面、不会生成 views，也不会生成 agent export。URL 和远程 repository source 只生成 `network_checked: false` 的离线 remote item。

### Source-backed wikiization

`wikify wikiize` 是 `source add -> sync -> wikiize` 这条产品闭环里的 wiki 化步骤。它读取 `.wikify/queues/ingest-items.json` 和 `.wikify/sync/source-items.json`，把 eligible 的本地文本/Markdown source item 转成可读 wiki 页面和机器可读对象。

常用命令：

```bash
wikify wikiize --dry-run
wikify wikiize
wikify wikiize --queue-id queue_<id>
wikify wikiize --item item_<id>
wikify wikiize --source src_<id>
wikify wikiize --limit 5
wikify wikiize --agent-command "python3 agent.py"
wikify wikiize --agent-profile default
wikify wikiize --agent-profile
```

主要产物：

- `wiki/pages/`：给人看的 source-backed Markdown 页面
- `artifacts/objects/wiki_pages/`：给 agent 和工具读的 `wikify.wiki-page.v1` 对象
- `artifacts/objects/object-index.json`：对象索引
- `artifacts/objects/validation.json`：严格验证报告
- `.wikify/wikiization/last-wikiize.json`：本次 wikiize run report
- `.wikify/queues/wikiization-tasks.json`：低置信、冲突、远程未抓取、用户编辑漂移等后续任务
- `.wikify/wikiization/requests/` 和 `.wikify/wikiization/results/`：显式 external agent handoff 产物

`--dry-run` 只报告会处理哪些 queue entry、计划写哪些 page/object/request/result path，不写页面、不写对象、不更新 queue，也不写 run report。

默认 deterministic baseline 不依赖 provider：本地 Markdown 取第一个 H1 作为标题，否则用文件名；summary 来自源文本的前几行有效内容；页面包含 source references 和 bounded excerpt。每个生成页面和对象都必须带 `source_refs`，至少包含 `source_id`、`item_id`、locator/path evidence、fingerprint evidence 和 confidence。

增量更新有 hash guard：Wikify 会在对象里记录 generation metadata，只有当现有生成页仍匹配上一次 generated hash 时才覆盖。只要用户改过页面，下一次 wikiize 会保留用户内容，把 queue entry 标成 `needs_review`，并写入 `.wikify/queues/wikiization-tasks.json`。

远程 URL 和远程 repository 默认不抓取、不 clone，不会伪造页面；没有显式 agent enrichment 时会生成 wikiization task。语义增强必须显式传 `--agent-command` 或 `--agent-profile`。Wikify 写出 `wikify.wikiization-request.v1`，通过 stdin 交给外部 agent，接收 `wikify.wikiization-result.v1`，然后由 Wikify 自己完成路径校验、front matter 渲染、对象写入和 strict validation。不存在隐藏 provider 调用。

Phase 25 只负责 source-backed page pipeline；首页、source 页、topic/project/person/decision 浏览页和静态站点属于 Phase 26；`llms.txt`、context pack 和 agent query export 属于 Phase 27。

## 3.2 Wiki object model 与验证

Phase 24 定义 v0.2 对象模型和验证面；Phase 25 通过 `wikify wikiize` 消费 `.wikify/queues/ingest-items.json` 并生成 source-backed wiki 页面。human views、agent exports、provider runtime 和更广泛 maintenance repair flow 仍属于后续阶段。

对象产物是知识库成果的一部分，放在可见目录 `artifacts/objects/`，而不是只藏在 `.wikify/` 控制面里：

- `artifacts/objects/object-index.json`，schema 为 `wikify.object-index.v1`
- `artifacts/objects/validation.json`，schema 为 `wikify.object-validation.v1`
- 具体对象 JSON 可放在 `artifacts/objects/wiki_pages/` 等类型目录下

当前对象 schema：

- `wikify.wiki-page.v1`
- `wikify.topic.v1`
- `wikify.project.v1`
- `wikify.person.v1`
- `wikify.decision.v1`
- `wikify.timeline-entry.v1`
- `wikify.citation.v1`
- `wikify.graph-edge.v1`
- `wikify.context-pack.v1`

对象类型：

- `source`
- `source_item`
- `wiki_page`
- `topic`
- `project`
- `person`
- `decision`
- `timeline_entry`
- `citation`
- `graph_edge`
- `context_pack`

`wiki_page` 必填字段包括 `schema_version`、`id`、`type`、`title`、`summary`、`body_path`、`source_refs`、`outbound_links`、`backlinks`、`created_at`、`updated_at`、`confidence`、`review_status`。

`review_status` 取值为 `generated`、`needs_review`、`approved`、`rejected`、`stale`。Graph provenance 取值为 `EXTRACTED`、`INFERRED`、`AMBIGUOUS`。

Markdown front matter 是人可读的对象 metadata 镜像。当前解析范围是标量值加 JSON-flow 数组/对象，不引入完整 YAML 依赖。

验证命令：

```bash
wikify validate
wikify validate --path <path>
wikify validate --strict
wikify validate --write-report
```

默认验证兼容旧 Markdown：没有 object front matter 会返回 warning，exit code 仍为 `0`。严格错误返回 exit code `2`，并通过 `wikify.object-validation.v1` 返回结构化记录。每条记录固定包含 `code`、`message`、`path`、`object_id`、`field`、`severity`、`details`。

稳定错误码包括 `object_required_field_missing`、`object_duplicate_id`、`object_link_unresolved`、`object_source_ref_unresolved`、`object_frontmatter_invalid`、`object_schema_invalid`。

兼容性边界：`wikify graph` 继续保留 path-based node id，只额外暴露 object id；`wikify maintain`、旧 `fokb` 入口和现有 sample KB layout 都保持可用。

## 3.3 入库与工作流

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

## 3.4 对象层查询

- `list`
- `search`
- `show`
- `query`

作用：
- 列出对象
- 搜索 markdown wiki
- 展示对象内容
- 抽取 query context 给下游 agent 使用

## 3.5 产出层

- `writeback`
- `synthesize`

作用：
- 基于 query context 写回整理结果
- 生成结构化 synthesis markdown

## 3.6 Obsidian 收口方向
当前产品记录格式正在往 Obsidian-native 收：
- digest 输出优先使用 frontmatter + `[[wikilink]]`
- topic 主笔记补 `笔记关系` 和 `关联笔记（Obsidian）`
- parsed/article note 与 brief note 也补 frontmatter、`笔记关系` 与 Obsidian 链接
- 自动生成 `topics-moc.md` 与 `sources/sources-index.md` 作为导航页
- digest 生成后会自动刷新这些导航页
- 同时暂时保留现有 markdown 路径链接和 `关联主题` 字段，避免破坏 maintenance / ingest 兼容链路

## 3.7 巡检与维护

- `lint`
- `lint --deep`
- `maintenance`
- `maintain`
- `maintain-run`
- `maintain-loop`
- `agent-profile`
- `decide`

作用：
- 基础巡检和全库深巡检
- 查询 maintenance history
- 基于 graph 自动生成 findings、plan 和 history，不打断用户
- 一条命令刷新维护产物并推进有界 agent task batch
- 多轮重复维护刷新和任务推进，直到没有可选任务或触发明确 stop condition
- 管理显式外部 agent command profile，减少重复输入
- 根据 maintenance verdict 产出下一步 decision plan

## 3.8 图谱结构层

- `graph`

作用：
- 从已编译的 Markdown wiki 中重建本地图谱
- 提取 `[[wikilink]]`、Markdown 链接和 topic/article/source 结构关系
- 输出 `graph/graph.json`、`graph/GRAPH_REPORT.md` 和可选 `graph/graph.html`
- 帮 agent 发现中心节点、社区、孤立对象、断链和下一步维护问题
- 计算 advisory graph relevance：direct links、source overlap、common neighbors、type affinity

默认命令：

```bash
wikify graph
wikify graph --no-html
wikify graph --scope topics
```

`graph` 在 V1 中是 read-mostly 命令：只写 `graph/` 目录，不修改 topic、parsed、review queue 或 maintenance history。

`graph.analytics.relevance` 会输出结构相关性分数和 signal-level evidence。该分数只用于解释和排序，不会直接触发正文写入。

## 3.9 自动图谱维护层

- `maintain`

作用：
- 自动执行 `graph --no-html`
- 基于 `graph.analytics` 生成断链、孤立对象、中心节点、成熟社区和薄图谱 findings
- 把 graph relevance metadata 附加到相关 findings 和 agent tasks
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

## 3.10 Agent Task Reader

- `tasks`

作用：
- 读取 `sorted/graph-agent-tasks.json`
- 按 status、action、id、limit 筛选任务
- 为后续 agent 提供稳定 JSON selection，而不是让 agent 自己解析文件路径和筛选逻辑
- 在显式 `--refresh` 时先执行一次 `maintain`，再读取最新任务

默认命令：

```bash
wikify tasks
wikify tasks --status queued --limit 5
wikify tasks --action queue_link_repair
wikify tasks --id agent-task-1
wikify tasks --refresh --id agent-task-1
```

缺少 `sorted/graph-agent-tasks.json` 时，返回 `agent_task_queue_missing`。V1 中 `tasks` 默认只读，不修改正文页面，也不改变 task status；状态流转和 patch 应用属于后续 phase。

## 3.11 Scoped Patch Proposal

- `propose`

作用：
- 读取一个已有 graph agent task
- 校验 task 的 `write_scope`
- 生成受限的 patch proposal artifact
- 读取 wiki 根目录下可选的 `purpose.md` / `wikify-purpose.md`，把目标上下文写进 proposal
- 让后续 agent 审核 proposal，而不是直接让 `maintain` 或 `tasks` 改正文

默认命令：

```bash
wikify propose --task-id agent-task-1
wikify propose --task-id agent-task-1 --dry-run
```

输出产物：
- `sorted/graph-patch-proposals/<task-id>.json`

`propose` 默认写 proposal artifact；`--dry-run` 只返回 proposal JSON，不写文件。

proposal 会包含 task id、source finding、action、target、write scope、planned edits、acceptance checks、`purpose_context`、`rationale`、risk 和 preflight。所有 planned edit 的 path 必须落在 task `write_scope` 内，否则返回 `proposal_out_of_scope`。

如果根目录存在 `purpose.md`，`propose` 会优先读取它；否则读取 `wikify-purpose.md`。目的文件存在时，`purpose_context.present = true`，proposal 的 `rationale.purpose_alignment` 会说明当前 task 如何贴合该目的。目的文件缺失时，`purpose_context.present = false`，这是明确的非阻塞状态，proposal 仍按 graph task evidence 生成。

V1 安全规则：`propose` 不应用 patch，不修改 topic、parsed、sorted 等正文页面，也不改变 task status。目的上下文只丰富解释，不扩大 `write_scope`，不绕过 path validation。它只把“这个 agent task 可以怎样被处理、为什么值得处理”转成可审计 JSON，给后续生命周期和 apply phase 使用。

## 3.12 Agent Task Lifecycle

`tasks` 的默认读取行为仍然只读；只有显式 lifecycle action flag 出现时才会写入 task queue 和 event log。

作用：
- 把 `queued`、`proposed`、`in_progress`、`done`、`failed`、`blocked`、`rejected` 变成可审计状态
- 把状态变化持久化回 `sorted/graph-agent-tasks.json`
- 追加状态事件到 `sorted/graph-agent-task-events.json`
- 支持 agent 自动 retry、cancel、restore 和 mark-done，不打断用户

默认命令：

```bash
wikify tasks --id agent-task-1 --mark-proposed --proposal-path sorted/graph-patch-proposals/agent-task-1.json
wikify tasks --id agent-task-1 --start
wikify tasks --id agent-task-1 --mark-done
wikify tasks --id agent-task-1 --mark-failed --note "patch conflict"
wikify tasks --id agent-task-1 --retry
wikify tasks --id agent-task-1 --block --note "ambiguous target"
wikify tasks --id agent-task-1 --restore
wikify tasks --id agent-task-1 --cancel
```

输出产物：
- `sorted/graph-agent-tasks.json`
- `sorted/graph-agent-task-events.json`

非法状态流转返回 `invalid_agent_task_transition`。例如 `done -> in_progress` 会被拒绝。缺少 `--id` 时返回 `agent_task_id_required`。

安全规则：lifecycle action 只修改 agent task artifact 和 event artifact，不修改正文页面、不改 proposal artifact、不应用 patch。

## 3.13 Patch Bundle Request

- `bundle-request`

作用：
- 读取一个 graph agent task 和 scoped proposal context
- 校验 proposal `write_scope`
- 读取目标文件当前内容，生成 snapshot 和 SHA-256 hash
- 把外部 agent 生成 patch bundle 所需的上下文打包成稳定 JSON
- 默认写入 `sorted/graph-patch-bundle-requests/<task-id>.json`
- 不修改正文页面，不改变 task status，不在 CLI 内隐藏调用 LLM

默认命令：

```bash
wikify bundle-request --task-id agent-task-1 --dry-run
wikify bundle-request --task-id agent-task-1
```

输出产物：
- `sorted/graph-patch-bundle-requests/<task-id>.json`
- 如果 proposal 不存在，非 dry-run 会同时写入 `sorted/graph-patch-proposals/<task-id>.json`

request 会包含 `wikify.patch-bundle-request.v1` schema、proposal evidence、write scope、target snapshots、content hash、默认 bundle 输出路径 `sorted/graph-patch-bundles/<task-id>.json`，以及当前允许的 `replace_text` operation contract。

外部 agent 的职责是读取 request，只写 patch bundle artifact：

```json
{
  "schema_version": "wikify.patch-bundle.v1",
  "proposal_task_id": "agent-task-1",
  "proposal_path": "sorted/graph-patch-proposals/agent-task-1.json",
  "operations": [
    {
      "operation": "replace_text",
      "path": "topics/a.md",
      "find": "[[Missing]]",
      "replace": "[[Existing]]",
      "rationale": "resolve broken wikilink"
    }
  ]
}
```

`bundle-request --dry-run` 只返回 request JSON，不写 request artifact，也不写 proposal artifact。

正常自动化流程优先调用 `run-task`。当 bundle 缺失时，`run-task` 会自动写入 request artifact；`bundle-request` 主要用于显式刷新 request、人工检查 handoff，或者外部编排系统只想生成 request 而不推进 task lifecycle。

安全规则：`bundle-request` 是 agent handoff 层，不是内容生成层。它只打包上下文和契约，不调用 provider、不生成 semantic patch、不修改 task lifecycle。正文修改仍然只允许通过 `apply`。

## 3.14 External Patch Bundle Producer

- `produce-bundle`

作用：
- 读取一个 `wikify.patch-bundle-request.v1` request artifact
- 显式调用调用方传入的外部 agent command
- 把 request JSON 通过 stdin 传给外部 command
- 通过环境变量告诉外部 command 当前 KB、request 路径和建议 bundle 输出路径
- 接收 stdout JSON bundle，或接受 command 直接写好的 suggested bundle 文件
- 对产出的 bundle 做 deterministic preflight
- 不修改正文页面，不推进 task lifecycle，不隐藏选择 provider

默认命令：

```bash
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py" --dry-run
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py"
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py" --timeout 120
```

外部 command 收到：
- stdin：完整 `wikify.patch-bundle-request.v1` JSON
- `WIKIFY_BASE`：当前 wiki root
- `WIKIFY_PATCH_BUNDLE_REQUEST`：request artifact 绝对路径
- `WIKIFY_PATCH_BUNDLE`：建议写入的 patch bundle 绝对路径

外部 command 可以二选一：
- 向 stdout 打印完整 `wikify.patch-bundle.v1` JSON，Wikify 会写入 `WIKIFY_PATCH_BUNDLE`
- 自己写入 `WIKIFY_PATCH_BUNDLE` 指向的文件，stdout 保持为空

返回 schema：

```json
{
  "schema_version": "wikify.patch-bundle-production.v1",
  "status": "bundle_ready",
  "executed": true,
  "request_path": "/abs/kb/sorted/graph-patch-bundle-requests/agent-task-1.json",
  "suggested_bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json",
  "output_mode": "stdout",
  "artifacts": {
    "patch_bundle": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json"
  },
  "preflight": {
    "schema_version": "wikify.patch-application-preflight.v1",
    "status": "ready"
  }
}
```

`produce-bundle --dry-run` 只校验 request、解析 command、返回 invocation contract；它不执行 command，不写 bundle，不 preflight。

安全规则：`produce-bundle` 是外部 agent command adapter，不是内置 LLM provider。Wikify 不保存 API key、不选择模型、不重试 provider，也不把失败吞掉改成人工确认。provider、模型、密钥和 retry 策略都应由 `--agent-command` 指向的外部程序负责。

## 3.15 Patch Apply And Rollback

- `apply`
- `rollback`

作用：
- 读取一个 patch proposal artifact
- 读取一个下游 agent 生成的 patch bundle
- 对 bundle 做 deterministic preflight
- 在非 dry-run 模式下应用受限文本替换
- 写入 `sorted/graph-patch-applications/<application-id>.json`
- 在需要撤销时用 application record 做 hash-guarded rollback

默认命令：

```bash
wikify apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json --dry-run
wikify apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json
wikify rollback --application-path sorted/graph-patch-applications/<application-id>.json --dry-run
wikify rollback --application-path sorted/graph-patch-applications/<application-id>.json
```

patch bundle 是 agent 生成的结构化补丁，不是 Wikify 在 CLI 内隐藏生成的内容。V1.2 只支持 `replace_text`：

```json
{
  "schema_version": "wikify.patch-bundle.v1",
  "proposal_task_id": "agent-task-1",
  "proposal_path": "sorted/graph-patch-proposals/agent-task-1.json",
  "operations": [
    {
      "operation": "replace_text",
      "path": "topics/a.md",
      "find": "[[Missing]]",
      "replace": "[[Existing]]"
    }
  ]
}
```

apply preflight 会检查：
- proposal 和 bundle 的 task id 一致
- 每个 operation path 都在 proposal `write_scope` 内
- path 是 wiki-root 内的相对路径
- `find` 文本在目标文件中恰好出现一次
- 每个文件在当前 phase 只允许一个 operation，避免半应用和顺序 hash 混乱

`apply --dry-run` 不写正文、不写 application record。非 dry-run apply 会写正文，并把 before/after hash、affected paths、proposal path、bundle path 和 rollback guard 写进 `graph-patch-applications`。

rollback 不重新读取 proposal 或 bundle，而是读取 application record。只有当前文件 hash 仍等于记录里的 `after_hash` 时，rollback 才会把 `replace` 还原为 `find`；如果文件已经漂移，则返回 `patch_rollback_hash_mismatch`。

安全规则：Wikify 只应用显式 patch bundle，不在 apply 过程中调用 LLM、不自行生成语义内容、不扩大 proposal `write_scope`。task status 仍由 `tasks --mark-done` 等 lifecycle 命令显式推进。

## 3.16 Agent Task Workflow Runner

- `run-task`

作用：
- 读取一个 graph agent task
- 创建或复用 scoped proposal
- 查找默认 patch bundle：`sorted/graph-patch-bundles/<task-id>.json`
- bundle 存在时调用 deterministic apply
- apply 成功后通过 lifecycle 把 task 标记为 `done`
- bundle 缺失时自动写入 `sorted/graph-patch-bundle-requests/<task-id>.json`
- bundle 缺失时返回 `waiting_for_patch_bundle`，交给 agent 读取 request 或调用 `produce-bundle` 生成补丁，不打扰用户
- 显式提供 `--agent-command` 时，bundle 缺失也可以在同一次 run 中自动产包、preflight、apply、mark-done

默认命令：

```bash
wikify run-task --id agent-task-1 --dry-run
wikify run-task --id agent-task-1
wikify run-task --id agent-task-1 --bundle-path sorted/graph-patch-bundles/custom.json
wikify run-task --id agent-task-1 --agent-command "python3 agent.py" --producer-timeout 120
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py"
wikify run-task --id agent-task-1
```

返回 schema：

```json
{
  "schema_version": "wikify.agent-task-run.v1",
  "task_id": "agent-task-1",
  "dry_run": false,
  "status": "waiting_for_patch_bundle",
  "steps": [
    {"name": "proposal", "status": "written"},
    {"name": "lifecycle", "status": "marked_proposed"}
  ],
  "artifacts": {
    "proposal": "/abs/kb/sorted/graph-patch-proposals/agent-task-1.json",
    "bundle": null,
    "patch_bundle_request": "/abs/kb/sorted/graph-patch-bundle-requests/agent-task-1.json",
    "application": null,
    "agent_tasks": "/abs/kb/sorted/graph-agent-tasks.json",
    "task_events": "/abs/kb/sorted/graph-agent-task-events.json"
  },
  "next_actions": ["generate_patch_bundle"],
  "summary": {
    "task_id": "agent-task-1",
    "bundle_request_path": "/abs/kb/sorted/graph-patch-bundle-requests/agent-task-1.json",
    "suggested_bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json"
  }
}
```

状态语义：
- `waiting_for_patch_bundle`：proposal 和 bundle request 已准备好，但还没有可应用 bundle；agent 应读取 `artifacts.patch_bundle_request`，再按 request 写 patch bundle，或调用 `produce-bundle` 让外部 agent command 产出 bundle
- `ready_to_apply`：dry-run 发现 proposal 和 bundle 都可用，下一次非 dry-run 可执行 apply
- `completed`：bundle 已 apply，task 已 mark-done

`run-task --dry-run` 不写 proposal、不写 bundle request、不写 lifecycle event、不改正文、不写 application record。即使同时传入 `--agent-command`，dry-run 也只报告 would-execute，不执行外部 command，不写 patch bundle。

`run-task --agent-command` 只在 bundle 缺失时调用 producer。若 `sorted/graph-patch-bundles/<task-id>.json` 或 `--bundle-path` 指向的 bundle 已存在，runner 会直接走 deterministic apply，不执行外部 command。

producer 失败时，`run-task` 返回对应 `bundle_producer_*` code，`details.phase` 为 `bundle_producer`。此时已写入的 proposal、request 和 lifecycle event 会保留为可审计中间状态，正文不会被修改。

安全规则：`run-task` 是编排层，不是隐藏 provider 层。它只有在调用方显式传入 `--agent-command` 时才会执行外部 command；provider、模型、密钥和 retry 都属于该 command 的责任。runner 不会绕过 proposal `write_scope`，正文修改仍然只发生在 deterministic apply 之后。

## 3.17 Batch Task Workflow Runner

- `run-tasks`

作用：
- 从 `sorted/graph-agent-tasks.json` 选择一组任务
- 默认只选择 `queued`
- 默认 `limit=5`
- 顺序调用现有 `run-task` 工作流
- 返回每个 task 的结构化结果或结构化错误
- 默认遇到第一个失败 task 就停止
- 显式 `--continue-on-error` 时继续处理后续 task

默认命令：

```bash
wikify run-tasks --dry-run
wikify run-tasks --limit 5 --agent-command "python3 agent.py"
wikify run-tasks --status queued --action queue_link_repair --limit 5 --agent-command "python3 agent.py"
wikify run-tasks --status queued --limit 5 --continue-on-error --agent-command "python3 agent.py"
```

返回 schema：

```json
{
  "schema_version": "wikify.agent-task-batch-run.v1",
  "dry_run": false,
  "status": "completed",
  "selection": {
    "status": "queued",
    "action": null,
    "id": null,
    "limit": 5
  },
  "execution": {
    "mode": "sequential",
    "continue_on_error": false,
    "stop_on_error": true
  },
  "items": [
    {
      "task_id": "agent-task-1",
      "ok": true,
      "status": "completed",
      "result": {
        "schema_version": "wikify.agent-task-run.v1"
      }
    }
  ],
  "summary": {
    "selected_count": 1,
    "completed_count": 1,
    "waiting_count": 0,
    "failed_count": 0,
    "stopped": false
  }
}
```

状态语义：
- `no_tasks`：筛选后没有任务
- `dry_run`：完成预演，未写任何 artifact
- `completed`：选中的任务都完成
- `waiting_for_patch_bundle`：至少一个任务停在等待 bundle，且没有失败
- `stopped_on_error`：默认 stop-on-error 触发，后续任务未执行
- `completed_with_errors`：启用 `--continue-on-error` 后有失败，但后续任务仍继续处理

安全规则：`run-tasks` 不新增任何 apply 语义，也不并发执行。它只是顺序组合现有 `run-task`。默认 limit 5 和 stop-on-error 是批量执行的刹车。`--agent-command` 仍然是显式外部 command，Wikify 不隐藏 provider、模型、密钥或 retry 策略。`run-tasks --dry-run` 在整个 batch 内都不写 proposal、request、bundle、event、正文或 application record。

## 3.18 Maintenance Run Automation

- `maintain-run`

作用：
- 先执行 `maintain` 刷新 graph findings、plan、history 和 agent task queue
- 再从刷新后的队列中选择 bounded batch
- 复用现有 `run-tasks` 执行路径，不新增 apply 语义
- 默认 `policy=balanced`、`status=queued`、`limit=5`
- 默认顺序执行，遇到第一个 per-task failure 停止
- 显式 `--continue-on-error` 时继续后续 task

默认命令：

```bash
wikify maintain-run --dry-run
wikify maintain-run --limit 5 --agent-command "python3 agent.py"
wikify maintain-run --status queued --action queue_link_repair --limit 5 --agent-command "python3 agent.py"
wikify maintain-run --status queued --limit 5 --continue-on-error --agent-command "python3 agent.py"
```

`maintain-run --dry-run` 会运行 maintenance dry-run 并用返回的 in-memory task queue 预览 selection；它不会读取旧的 `sorted/graph-agent-tasks.json` 来决定 would-run tasks，也不会执行 producer、写 proposal/request/bundle、写 lifecycle event、apply bundle 或修改正文。和 `maintain --dry-run` 一样，它可能刷新 `graph/` 产物。

返回结果使用 `wikify.maintenance-run.v1`，包含：
- `maintenance.summary`
- `batch.summary`
- `artifacts.maintenance`
- `artifacts.batch`
- `summary.selected_count`
- `summary.completed_count`
- `next_actions`

安全规则：`maintain-run` 是组合层。它只组合 `maintain` 和 `run-tasks`，不会隐藏调用 provider、不会选择模型、不会读取 API key、不会绕过 proposal/write_scope/preflight/apply/rollback/lifecycle 规则。只有调用方显式传入 `--agent-command` 或 `--agent-profile` 时，后续 batch task 才可能执行外部 command。

## 3.19 Maintenance Loop Automation

- `maintain-loop`

作用：
- 重复执行 `maintain-run`，让维护刷新和 agent task 执行可以自动推进多轮
- 每轮继续复用现有 proposal/request/producer/preflight/apply/lifecycle 路径
- 默认 `policy=balanced`、`status=queued`、`limit=5`
- 默认 `max_rounds=3`、`task_budget=15`
- 遇到无任务、等待 bundle、失败、任务预算耗尽、轮数耗尽或 dry-run preview 时停止

默认命令：

```bash
wikify maintain-loop --dry-run
wikify maintain-loop --max-rounds 3 --task-budget 15 --limit 5 --agent-command "python3 agent.py"
wikify maintain-loop --max-rounds 3 --task-budget 15 --limit 5 --agent-profile default
wikify maintain-loop --max-rounds 3 --task-budget 15 --limit 5 --agent-profile
wikify maintain-loop --status queued --action queue_link_repair --limit 1 --max-rounds 3 --task-budget 3 --agent-profile
```

`maintain-loop --dry-run` 只预览一轮，因为 dry-run 不写 task queue、proposal、request、bundle、event、application record 或正文；重复 dry-run 会不断看到同一个 in-memory selection。

返回结果使用 `wikify.maintenance-loop.v1`，包含：
- `stop_reason`
- `summary.round_count`
- `summary.selected_count`
- `summary.completed_count`
- `summary.waiting_count`
- `summary.failed_count`
- `rounds[]`
- `artifacts.paths`
- `next_actions`

stop reasons：
- `no_tasks`
- `waiting_for_patch_bundle`
- `failed_tasks`
- `task_budget_exhausted`
- `max_rounds_reached`
- `dry_run_preview`

安全规则：`maintain-loop` 只是多轮组合层。它不新增 apply 语义，不并发执行，不隐藏 provider、模型、密钥或 retry。只有调用方显式传入 `--agent-command` 或 `--agent-profile` 时，每轮 task 才可能执行外部 producer command；只有显式传入 `--verifier-command` 或 `--verifier-profile` 时，每轮 task 才可能执行外部 verifier command。仅配置 default profile 不会触发外部 command。

## 3.20 Agent Profile Configuration

- `agent-profile`

作用：
- 把外部 agent command 保存为命名 profile
- 避免每次 `run-task`、`run-tasks`、`maintain-run` 或 `produce-bundle` 都重复输入长命令
- 同样可用于 `maintain-loop`
- 同一个 profile store 也可通过 `--verifier-profile` 用于 verifier agent
- profile 解析后仍然走现有 producer/preflight/apply/lifecycle 流程
- 不保存 API key，不选择模型，不内置 retry，不隐藏 provider 行为

默认命令：

```bash
wikify agent-profile --set default --agent-command "python3 agent.py" --producer-timeout 120
wikify agent-profile --set-default default
wikify agent-profile --list
wikify agent-profile --show default
wikify agent-profile --show-default
wikify agent-profile --clear-default
wikify agent-profile --unset default
wikify maintain-run --limit 5 --agent-profile default
wikify maintain-run --limit 5 --agent-profile
wikify maintain-loop --max-rounds 3 --task-budget 15 --limit 5 --agent-profile
wikify run-task --id agent-task-1 --agent-profile default
wikify run-task --id agent-task-1 --agent-profile default --verifier-profile reviewer
wikify produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-profile default
```

profile artifact 写在 wiki root：

```json
{
  "schema_version": "wikify.agent-profiles.v1",
  "default_profile": "default",
  "profiles": {
    "default": {
      "name": "default",
      "agent_command": "python3 agent.py",
      "producer_timeout_seconds": 120.0,
      "description": null,
      "created_at": "2026-04-28T00:00:00Z",
      "updated_at": "2026-04-28T00:00:00Z"
    }
  }
}
```

错误：
- 同时传入 `--agent-command` 和 `--agent-profile` 返回 `agent_profile_ambiguous`
- profile config 缺失返回 `agent_profile_config_missing`
- 指定 profile 不存在返回 `agent_profile_missing`
- 裸 `--agent-profile` 但没有配置 default profile 时返回 `agent_profile_default_missing`

默认 profile 只是省略 profile 名称的显式 shorthand：`maintain-loop --agent-profile` 或 `maintain-run --agent-profile` 等价于读取 `default_profile` 后再执行对应 profile。`--verifier-profile` 也支持同一个裸 flag shorthand。仅仅配置了 `default_profile` 不会让 `maintain-loop`、`maintain-run`、`run-task`、`run-tasks`、`verify-bundle` 或 `produce-bundle` 自动执行外部 command。

安全规则：profile 是显式命令的项目级别别名，不是 provider adapter。不要把 API key 或 token 直接写进 `wikify-agent-profiles.json`；如果外部 agent 需要密钥，应由外部 command 自己从环境变量或它自己的安全配置读取。

## 3.21 Agent Verifier Gate

- `verify-bundle`
- `run-task --verifier-command`
- `run-task --verifier-profile`
- `run-tasks --verifier-command`
- `maintain-run --verifier-profile`
- `maintain-loop --verifier-profile`

作用：
- 在 deterministic preflight 通过之后、真正 apply 之前，让另一个显式 agent 审核 patch bundle
- 审核通过才继续 apply 和 mark-done
- 审核拒绝时写 audit artifact，然后返回结构化错误，不修改正文
- 在 `run-task` / batch / loop 自动化中，审核拒绝会把 task 标记为 `blocked` 并写入可机读反馈
- 减少人工审批打扰，但不把审核藏成默认 provider 行为

默认命令：

```bash
wikify verify-bundle --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json --verifier-command "python3 verifier.py"
wikify verify-bundle --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json --verifier-profile reviewer
wikify run-task --id agent-task-1 --agent-profile default --verifier-profile reviewer
wikify maintain-loop --agent-profile default --verifier-profile reviewer
```

verifier command 从 stdin 读取 `wikify.patch-bundle-verification-request.v1`：

```json
{
  "schema_version": "wikify.patch-bundle-verification-request.v1",
  "task_id": "agent-task-1",
  "proposal_path": "/abs/kb/sorted/graph-patch-proposals/agent-task-1.json",
  "bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json",
  "proposal": {},
  "bundle": {},
  "preflight": {
    "ready": true
  },
  "response_schema": {
    "schema_version": "wikify.patch-bundle-verdict.v1",
    "accepted": true,
    "summary": "short rationale",
    "findings": []
  }
}
```

verifier command 必须向 stdout 输出：

```json
{
  "schema_version": "wikify.patch-bundle-verdict.v1",
  "accepted": true,
  "summary": "looks safe",
  "findings": []
}
```

Wikify 会暴露环境变量：
- `WIKIFY_BASE`
- `WIKIFY_PATCH_PROPOSAL`
- `WIKIFY_PATCH_BUNDLE`
- `WIKIFY_PATCH_BUNDLE_VERIFICATION`

返回 / artifact 使用 `wikify.patch-bundle-verification.v1`，写入：
- `sorted/graph-patch-verifications/<task-id>.json`

错误：
- verifier 拒绝返回 `patch_bundle_verification_rejected`
- stdout 非 JSON 返回 `bundle_verifier_invalid_output`
- schema 错误返回 `bundle_verifier_verdict_schema_invalid`
- command 失败返回 `bundle_verifier_command_failed`
- timeout 返回 `bundle_verifier_timeout`

当 verifier 拒绝发生在 `run-task` 自动化路径中，Wikify 还会：
- 把选中的 task lifecycle 标记为 `blocked`
- 在 task 上写 `blocked_feedback`，包含 `summary`、`findings`、`verification_path` 和完整 `verdict`
- 在 `sorted/graph-agent-task-events.json` 的 block event 上写同样的 `details`
- 在错误 `details` 中暴露 `verification_path`、`agent_tasks` 和 `task_events`

后续 agent 可以读取这些 artifact 修复 bundle，再用 `wikify tasks --id <id> --retry` 或 `--restore` 回到 `queued`；retry / restore 会清理旧的 `blocked_feedback`，避免新一轮执行背着过期审核结论。

自动 repair 路径：
- 对 verifier-blocked task 再次调用 `run-task --id <id> --agent-command ... --verifier-command ...`
- runner 会先把 blocked task retry 回可执行状态
- 新的 bundle request 会带 `repair_context`
- 即使默认 bundle 路径已有旧 rejected bundle，也会重新执行 producer 并覆盖该 bundle
- 新 bundle 仍必须通过 verifier，之后才会 apply 和 mark-done

批量 repair 用同一条单任务路径：

```bash
wikify run-tasks --status blocked --limit 5 --agent-profile default --verifier-profile reviewer
```

安全规则：verifier gate 不替代 deterministic preflight，也不直接修改内容。它只是在 apply 前增加一个显式外部 review command。dry-run 会构造 request 和 preflight，但不执行 verifier、不写 verification artifact。

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
- `maintain-run` 已能把维护刷新和有界 agent task 执行串成一条低打扰自动化路径

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
