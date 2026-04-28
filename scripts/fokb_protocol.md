# Wikify Protocol v1

`wikify` 是面向 agent 的知识库控制 CLI。
本文件定义它的稳定调用协议，重点不是“人类命令手册”，而是让 agent、UI 和脚本稳定消费 `wikify` 的结构化输出。

`fokb` 是旧入口兼容别名，协议语义与 `wikify` 相同。新自动化应优先调用 `wikify`。

## 1. 输出 envelope

所有子命令默认输出 JSON envelope。

支持输出模式：
- `--output json` 默认，稳定机器消费
- `--output pretty` 人类调试友好
- `--output quiet` 静默，仅保留 exit code

### 成功 envelope
```json
{
  "ok": true,
  "command": "status",
  "exit_code": 0,
  "result": {}
}
```

### 失败 envelope
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

## 2. Exit code registry

- `0` `EXIT_OK`
  - 成功
- `1` `EXIT_EXEC_ERROR`
  - 子命令执行失败、内部异常、外部脚本失败
- `2` `EXIT_NOT_FOUND`
  - 目标不存在、review item 不存在、topic 不存在等
- `3` `EXIT_QUALITY_GATED`
  - 质量门禁未通过，但结果已降级生成
- `4` `EXIT_REVIEW_REQUIRED`
  - 命令完成，但结果进入 `needs_review`
- `5` `EXIT_CHECK_FAILED`
  - 环境检查失败
- `6` `EXIT_DEEP_LINT_WARNING`
  - `lint --deep` 发现 warning / issue

## 3. Error code registry v1

### 通用
- `subcommand_failed`
- `invalid_json_output`
- `internal_error`
- `environment_check_failed`
- `object_not_found`
- `graph_maintenance_failed`
- `agent_task_queue_missing`
- `agent_task_not_found`
- `agent_task_id_required`
- `invalid_agent_task_transition`
- `proposal_write_scope_missing`
- `proposal_out_of_scope`
- `proposal_path_invalid`
- `patch_proposal_failed`
- `bundle_request_failed`
- `bundle_request_path_invalid`
- `bundle_request_target_not_found`
- `bundle_producer_request_not_found`
- `bundle_producer_request_invalid_json`
- `bundle_producer_request_schema_invalid`
- `bundle_producer_command_invalid`
- `bundle_producer_command_failed`
- `bundle_producer_timeout`
- `bundle_producer_invalid_output`
- `bundle_producer_no_bundle_output`
- `bundle_producer_failed`
- `patch_bundle_not_found`
- `patch_bundle_schema_invalid`
- `patch_bundle_task_mismatch`
- `patch_operation_out_of_scope`
- `patch_operation_unsupported`
- `patch_operation_conflict`
- `patch_preflight_failed`
- `patch_apply_failed`
- `patch_application_not_found`
- `patch_rollback_hash_mismatch`
- `patch_rollback_failed`
- `agent_task_run_failed`

### review / reingest / resolve
- `review_item_not_found`

### digest
- `digest_failed`
- `invalid_topic`

### ingest（预留）
- `quality_gate_blocked`
- `needs_review`
- `topic_update_failed`
- `parse_failed`
- `fetch_failed`

## 4. 命令层分层

### 环境层
- `init`
- `check`

### 运行 / 状态层
- `status`
- `stats`
- `state`
- `maintenance`
- `maintain`
- `decide`

### 对象层
- `list`
- `search`
- `show`
- `query`

### 工作流层
- `ingest`
- `reingest`
- `resolve`
- `digest`
- `promote`

### 产出层
- `writeback`
- `synthesize`

### 结构图谱层
- `graph`
- `graph --no-html`
- `graph --scope <scope>`
- `maintain`
- `maintain --dry-run`
- `maintain --policy <policy>`
- `maintain-run`
- `maintain-run --dry-run`
- `maintain-run --agent-command <command>`
- `tasks`
- `tasks --refresh`
- `tasks --id <id> --mark-proposed`
- `tasks --id <id> --start`
- `tasks --id <id> --mark-done`
- `propose --task-id <id>`
- `propose --task-id <id> --dry-run`
- `bundle-request --task-id <id>`
- `bundle-request --task-id <id> --dry-run`
- `produce-bundle --request-path <path> --agent-command <command>`
- `produce-bundle --request-path <path> --agent-command <command> --dry-run`
- `apply --proposal-path <path> --bundle-path <path>`
- `apply --proposal-path <path> --bundle-path <path> --dry-run`
- `rollback --application-path <path>`
- `rollback --application-path <path> --dry-run`
- `run-task --id <id>`
- `run-task --id <id> --dry-run`
- `run-task --id <id> --bundle-path <path>`
- `run-task --id <id> --agent-command <command>`
- `run-task --id <id> --agent-command <command> --producer-timeout <seconds>`
- `run-tasks`
- `run-tasks --status <status> --action <action> --limit <n>`
- `run-tasks --agent-command <command>`
- `run-tasks --continue-on-error --agent-command <command>`

### 巡检层
- `lint`
- `lint --deep`

## 5. Maintenance schema v1

`maintenance` 是 `wikify` 当前最重要的增量知识维护协议层之一。`graph` 是结构理解协议层，负责把已编译 Markdown wiki 转成可审计图谱产物。`maintain` 是自动图谱维护入口，负责把 graph analytics 转成 findings、plan、execution classification 和 append-only history。

它既会作为：
- 写操作结果中的 `result.maintenance`
- 持久化历史中的 `maintenance_history[*].maintenance`
- `maintenance` 子命令查询结果中的主体

### 顶层结构
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

### 顶层字段
- `checked`
  - 是否已执行维护推理
- `scope`
  - 当前固定为 `incremental`
- `verdict`
  - 维护结论，见 verdict registry
- `signals`
  - 已命中的维护信号
- `suggestions`
  - 非阻断建议
- `warnings`
  - 值得关注的风险或冲突提示
- `changed_paths`
  - 本次写操作涉及的对象路径
- `touched_types`
  - 本次触及的对象类型，如 `sorted` / `parsed`
- `changed_objects`
  - 对象级维护分析数组

## 6. Changed object schema v1

```json
{
  "path": ".../sorted/wechat-agent-summary.md",
  "type": "sorted",
  "signals": [],
  "warnings": [],
  "suggestions": [],
  "emerging_concepts": [],
  "neighbors": [],
  "claims": [],
  "contradictions": [],
  "promotion_candidate": true,
  "verdict": "needs_promotion"
}
```

### 对象级字段
- `path`
- `type`
- `signals`
- `warnings`
- `suggestions`
- `emerging_concepts`
  - 新出现、尚未稳定沉淀的概念候选
- `neighbors`
  - 一跳邻域对象摘要
- `claims`
  - 从对象文本中抽出的最小 claim 列表
- `contradictions`
  - 与邻域 claim 的冲突列表
- `promotion_candidate`
  - 是否应被提升成稳定知识对象
- `verdict`
  - 对象级 verdict

## 7. Claim schema v1

```json
{
  "subject": "OpenClaw Router",
  "canonical_subject": "openclaw-route",
  "polarity": "positive",
  "marker": "可行",
  "sentence": "OpenClaw Router 可行",
  "source_type": "sorted",
  "source_weight": 2,
  "source_path": ".../sorted/example.md"
}
```

### claim 字段
- `subject`
  - 原始 subject
- `canonical_subject`
  - 归一化后的 subject，用于弱聚类与冲突比对
- `polarity`
  - `positive` / `negative`
- `marker`
  - 触发 polarity 的词
- `sentence`
  - claim 来源句子
- `source_type`
  - 对象类型
- `source_weight`
  - source-aware + recency-aware 后的有效权重
- `source_path`
  - 来源路径

## 8. Contradiction schema v1

```json
{
  "subject": "OpenClaw Router",
  "canonical_subject": "openclaw-route",
  "changed_claim": {},
  "neighbor_claim": {},
  "changed_weight": 2,
  "neighbor_weight": 4,
  "baseline_side": "neighbor"
}
```

### contradiction 字段
- `changed_claim`
- `neighbor_claim`
- `changed_weight`
- `neighbor_weight`
- `baseline_side`
  - `changed` / `neighbor`
  - 表示当前更像基线的一侧，不等于真值裁决，只表示当前维护判断倾向

## 9. Verdict registry v1

### 顶层 / 对象级 verdict
- `stable`
  - 当前对象较稳定，暂无明显维护动作
- `watch`
  - 有建议或弱风险，值得观察
- `conflicted`
  - 已检测到 claim-level contradiction 或更强冲突
- `emerging`
  - 出现新概念、新信号，但还未到 promotion 条件
- `needs_promotion`
  - 当前对象应进一步沉淀为 topic / timeline / 稳定结论

## 10. History / state / decision 协议

### `stats`
重点聚合字段：
- `maintenance_history_count`
- `last_maintenance`

### `state`
重点聚合字段：
- `maintenance_history`
- `review_queue`
- `resolved_review`
- `last_ingest_payload`
- `lint_report`

### maintenance history entry schema v2
- `command`
- `maintenance`
- `provenance`

### provenance schema v2
- `trigger`
- `parent_command`
- `execution_mode`
- `decision`
- `execution`

### `maintenance`
推荐用作 maintenance history 正式查询接口。

常用：
- `maintenance --last`
- `maintenance --limit 5`
- `maintenance --warnings-only`

读取时会自动做 history normalization，尽量把旧记录补齐到当前 schema。
旧记录中的 `meta` 会被 lazy normalize 到 `provenance`，新记录应稳定写入 `provenance`。

### `maintain`
推荐用作自动化图谱维护入口。

常用：
- `maintain`
- `maintain --dry-run`
- `maintain --policy conservative`
- `maintain --policy balanced`
- `maintain --policy aggressive`

执行流程：
- 重建 `graph/graph.json` 和 `graph/GRAPH_REPORT.md`
- 计算 graph relevance signals：direct links、source overlap、common neighbors、type affinity
- 生成 `sorted/graph-findings.json`
- 生成 `sorted/graph-maintenance-plan.json`
- 生成 `sorted/graph-agent-tasks.json`
- 追加 `sorted/graph-maintenance-history.json`

`--dry-run` 只写 graph 产物，不写 `sorted/` 下的 findings、plan、agent tasks 或 history。返回结果中仍可包含 task queue preview，供调用方预览后续 agent 工作。

策略：
- `conservative`
  - 只允许最低风险维护计划进入执行分类
- `balanced`
  - 默认策略，适合常规 agent 自动巡检
- `aggressive`
  - 为后续更主动 agent 提供策略位，V1 仍不直接改正文页

`graph-agent-tasks.json` schema:

```json
{
  "schema_version": "wikify.graph-agent-tasks.v1",
  "summary": {
    "task_count": 1,
    "by_action": {
      "queue_link_repair": 1
    }
  },
  "tasks": [
    {
      "id": "agent-task-1",
      "source_finding_id": "broken-link:topics/a.md:7:Missing",
      "action": "queue_link_repair",
      "priority": "high",
      "target": "topics/a.md",
      "evidence": {},
      "write_scope": ["topics/a.md"],
      "agent_instructions": [],
      "acceptance_checks": [],
      "requires_user": false,
      "status": "queued"
    }
  ]
}
```

V1 安全规则：`maintain` 不修改 topic、parsed、sorted 等正文页面，也不在 CLI 内隐藏调用 LLM。断链修复、孤立对象挂接、digest refresh 和 community synthesis 都进入 queued plan step 和 agent task queue；只有确定性维护记录可标记为 executed。

返回 `result.summary` 至少包含：
- `finding_count`
- `planned_count`
- `executed_count`
- `queued_count`
- `task_count`

### `maintain-run`
推荐用作 one-command maintenance automation。

常用：
- `maintain-run --dry-run`
- `maintain-run --limit 5 --agent-command "python3 agent.py"`
- `maintain-run --status queued --action queue_link_repair --limit 5 --agent-command "python3 agent.py"`
- `maintain-run --status queued --limit 5 --continue-on-error --agent-command "python3 agent.py"`

执行流程：
- 先运行 `maintain`，刷新 graph findings、plan、agent task queue 和 history
- 非 dry-run 再调用 bounded `run-tasks`
- dry-run 使用 `maintain` 返回的 in-memory task queue 预览 selection，不读取旧的 on-disk queue
- 默认 `policy=balanced`、`status=queued`、`limit=5`
- 默认 sequential stop-on-error，显式 `--continue-on-error` 才继续后续 task

`wikify.maintenance-run.v1` schema:

```json
{
  "schema_version": "wikify.maintenance-run.v1",
  "base": "/abs/kb",
  "policy": "balanced",
  "dry_run": false,
  "status": "completed",
  "selection": {
    "status": "queued",
    "action": null,
    "id": null,
    "limit": 5
  },
  "execution": {
    "mode": "maintenance_then_batch",
    "continue_on_error": false,
    "stop_on_error": true,
    "agent_command_explicit": true
  },
  "maintenance": {
    "summary": {
      "task_count": 6
    }
  },
  "batch": {
    "schema_version": "wikify.agent-task-batch-run.v1"
  },
  "summary": {
    "selected_count": 1,
    "completed_count": 1,
    "waiting_count": 0,
    "failed_count": 0,
    "stopped": false
  },
  "next_actions": []
}
```

状态：
- `dry_run`
  - 完成 maintenance preview 和 batch selection preview
- `maintenance_completed_no_tasks`
  - 维护刷新成功，但筛选后没有任务
- `completed`
  - 选中的 batch tasks 完成
- `waiting_for_patch_bundle`
  - 至少一个 task 等待 bundle，且没有失败
- `stopped_on_error`
  - 默认 stop-on-error 触发
- `completed_with_errors`
  - `--continue-on-error` 模式下至少一个 task 失败，但 batch 跑完 selected tasks

错误：
- maintenance refresh 失败返回 `maintenance_refresh_failed`，`details.phase` 为 `maintenance`
- batch selection/execution 失败保留原 code，并设置 `details.phase` 为 `batch_execution`

安全规则：`maintain-run` 只组合 `maintain` 和 `run-tasks`，不新增 apply 语义，不并发执行，不隐藏 provider、模型、密钥或 retry。只有显式 `--agent-command` 才会触发外部 command。

Graph relevance contract:

```json
{
  "schema_version": "wikify.graph-relevance.v1",
  "summary": {
    "pair_count": 1,
    "by_confidence": {
      "high": 1
    }
  },
  "pairs": [
    {
      "source": "topics/a.md",
      "target": "articles/parsed/a.md",
      "score": 8.5,
      "confidence": "high",
      "signals": {
        "direct_link": {"count": 1, "score": 4.0},
        "source_overlap": {"shared_count": 1, "shared_sources": ["source.md"], "score": 3.0},
        "common_neighbors": {"count": 1, "neighbors": ["topics/c.md"], "score": 1.5},
        "type_affinity": {"source_type": "topics", "target_type": "parsed", "score": 1.0}
      }
    }
  ],
  "by_node": {}
}
```

Relevance is advisory. It may appear on `graph.analytics.relevance`, `sorted/graph-findings.json` findings, and `sorted/graph-agent-tasks.json` tasks. Low-confidence relevance is informational and must not escalate a task to high priority by itself.

### `tasks`
推荐用作 graph agent task queue 的正式读取接口。

常用：
- `tasks`
- `tasks --status queued`
- `tasks --action queue_link_repair`
- `tasks --id agent-task-1`
- `tasks --limit 5`
- `tasks --refresh`

默认行为：
- 只读取 `sorted/graph-agent-tasks.json`
- 返回 `wikify.agent-task-selection.v1`
- 不修改 task status
- 不修改 topic、parsed、sorted 等正文页面

`--refresh` 是显式写入路径：它会先运行 `maintain`，刷新 graph findings、plan、agent tasks 和 history，然后再读取任务。

缺少任务队列时返回：

```json
{
  "ok": false,
  "command": "tasks",
  "exit_code": 2,
  "error": {
    "code": "agent_task_queue_missing",
    "message": "agent task queue not found; run wikify maintain first or use --refresh",
    "retryable": false,
    "details": {
      "path": "/abs/kb/sorted/graph-agent-tasks.json"
    }
  }
}
```

找不到指定 task id 时返回 `agent_task_not_found`，exit code 为 `2`。

显式 lifecycle action：
- `tasks --id agent-task-1 --mark-proposed --proposal-path sorted/graph-patch-proposals/agent-task-1.json`
- `tasks --id agent-task-1 --start`
- `tasks --id agent-task-1 --mark-done`
- `tasks --id agent-task-1 --mark-failed --note "..."`
- `tasks --id agent-task-1 --block --note "..."`
- `tasks --id agent-task-1 --cancel`
- `tasks --id agent-task-1 --retry`
- `tasks --id agent-task-1 --restore`

生命周期行为：
- 写回 `sorted/graph-agent-tasks.json`
- 追加 `sorted/graph-agent-task-events.json`
- 返回 `wikify.agent-task-lifecycle.v1`
- 不修改 topic、parsed、sorted 等正文页面
- 不修改 proposal artifact

`graph-agent-task-events.json` schema:

```json
{
  "schema_version": "wikify.graph-agent-task-events.v1",
  "events": [
    {
      "id": "event-1",
      "task_id": "agent-task-1",
      "action": "mark_proposed",
      "from_status": "queued",
      "to_status": "proposed",
      "created_at": "2026-04-28T00:00:00Z",
      "proposal_path": "sorted/graph-patch-proposals/agent-task-1.json"
    }
  ]
}
```

非法状态流转返回 `invalid_agent_task_transition`，exit code 为 `2`。生命周期 action 缺少 `--id` 时返回 `agent_task_id_required`，exit code 为 `2`。

### `propose`
推荐用作 graph agent task 的 scoped patch proposal 入口。

常用：
- `propose --task-id agent-task-1`
- `propose --task-id agent-task-1 --dry-run`

默认行为：
- 读取 `sorted/graph-agent-tasks.json`
- 选择一个 task id
- 校验 task `write_scope`
- 读取 wiki 根目录下可选的 `purpose.md` / `wikify-purpose.md`
- 返回 `wikify.patch-proposal.v1`
- 默认写入 `sorted/graph-patch-proposals/<task-id>.json`
- 不修改 task status
- 不修改 topic、parsed、sorted 等正文页面

`--dry-run` 只返回 proposal JSON，不写 proposal artifact。

Purpose-aware 行为：
- `purpose.md` 优先于 `wikify-purpose.md`
- 找到目的文件时，proposal 包含 `purpose_context.present = true` 和目的摘要
- 找不到目的文件时，proposal 包含 `purpose_context.present = false`，这是非阻塞状态
- `rationale` 只解释 task 与目的/证据的关系，不扩大 `write_scope`，不绕过 path validation

`graph-patch-proposals/<task-id>.json` schema:

```json
{
  "schema_version": "wikify.patch-proposal.v1",
  "task_id": "agent-task-1",
  "source_finding_id": "broken-link:topics/a.md:7:Missing",
  "action": "queue_link_repair",
  "target": "topics/a.md",
  "write_scope": ["topics/a.md"],
  "planned_edits": [
    {
      "operation": "propose_content_patch",
      "path": "topics/a.md",
      "action": "queue_link_repair",
      "instructions": [],
      "evidence": {},
      "status": "planned"
    }
  ],
  "acceptance_checks": [],
  "purpose_context": {
    "schema_version": "wikify.purpose-context.v1",
    "present": true,
    "path": "/abs/kb/purpose.md",
    "relative_path": "purpose.md",
    "title": "Agent Knowledge Memory",
    "excerpt": "Goal: keep graph maintenance auditable.",
    "goal_lines": ["Goal: keep graph maintenance auditable."],
    "question_lines": []
  },
  "rationale": {
    "purpose_aware": true,
    "task_reason": "queue_link_repair for topics/a.md is derived from topics/a.md.",
    "purpose_alignment": "Aligns with Agent Knowledge Memory: Goal: keep graph maintenance auditable.",
    "safety": "Purpose context does not expand write scope or bypass path validation."
  },
  "risk": "medium",
  "preflight": {
    "write_scope_valid": true,
    "content_mutation": false,
    "task_status_mutation": false
  }
}
```

错误：
- 缺少任务队列时返回 `agent_task_queue_missing`，exit code 为 `2`
- 找不到指定 task id 时返回 `agent_task_not_found`，exit code 为 `2`
- task 缺少 write scope 时返回 `proposal_write_scope_missing`，exit code 为 `2`
- planned edit path 超出 write scope 时返回 `proposal_out_of_scope`，exit code 为 `2`

目的文件缺失不是错误，不影响 exit code。调用方应读取 `purpose_context.present` 和 `rationale.purpose_aware`，而不是把目的缺失当作失败。

### `bundle-request`
推荐用作外部 agent 生成 patch bundle 前的 deterministic request 入口。

常用：
- `bundle-request --task-id agent-task-1 --dry-run`
- `bundle-request --task-id agent-task-1`

默认行为：
- 读取 `sorted/graph-agent-tasks.json`
- 构建 task 对应的 scoped patch proposal context
- 校验 proposal `write_scope`
- 读取 write scope 内目标文件当前内容
- 返回 `wikify.patch-bundle-request.v1`
- 非 dry-run 写入 `sorted/graph-patch-bundle-requests/<task-id>.json`
- 非 dry-run 且 proposal artifact 缺失时，写入 `sorted/graph-patch-proposals/<task-id>.json`
- 不修改 task status
- 不修改 topic、parsed、sorted 等正文页面

`bundle-request --dry-run` 只返回 request JSON，不写 request artifact，不写 proposal artifact。

`graph-patch-bundle-requests/<task-id>.json` schema:

```json
{
  "schema_version": "wikify.patch-bundle-request.v1",
  "task_id": "agent-task-1",
  "proposal_path": "/abs/kb/sorted/graph-patch-proposals/agent-task-1.json",
  "request_path": "/abs/kb/sorted/graph-patch-bundle-requests/agent-task-1.json",
  "suggested_bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json",
  "proposal": {
    "schema_version": "wikify.patch-proposal.v1",
    "task_id": "agent-task-1",
    "write_scope": ["topics/a.md"]
  },
  "targets": [
    {
      "path": "topics/a.md",
      "absolute_path": "/abs/kb/topics/a.md",
      "sha256": "<sha256>",
      "content": "See [[Missing]].\n",
      "truncated": false,
      "content_length": 17
    }
  ],
  "allowed_operations": [
    {
      "operation": "replace_text",
      "constraints": [
        "path must be inside proposal.write_scope",
        "find must be non-empty and match exactly once in the current target file",
        "replace must be a string and must differ from find",
        "only one operation per path is supported"
      ]
    }
  ],
  "expected_bundle_schema": {
    "schema_version": "wikify.patch-bundle.v1",
    "proposal_task_id": "agent-task-1",
    "proposal_path": "sorted/graph-patch-proposals/agent-task-1.json",
    "operations": [
      {
        "operation": "replace_text",
        "path": "topics/a.md",
        "find": "<exact current text>",
        "replace": "<replacement text>",
        "rationale": "<why this change satisfies the proposal>"
      }
    ]
  },
  "safety": {
    "content_mutation": false,
    "task_status_mutation": false,
    "hidden_llm_call": false
  }
}
```

外部 agent 应读取 request，写入 `suggested_bundle_path` 指向的 `wikify.patch-bundle.v1` artifact，然后重新调用 `run-task --id <id>` 或显式调用 `apply`。

正常自动化建议先调用 `run-task --id <id>`。当 bundle 缺失时，`run-task` 会自动生成同样的 request artifact；`bundle-request` 主要作为显式刷新或单独 handoff 命令。

错误：
- 缺少任务队列时返回 `agent_task_queue_missing`，exit code 为 `2`
- 找不到指定 task id 时返回 `agent_task_not_found`，exit code 为 `2`
- request path 不安全时返回 `bundle_request_path_invalid`，exit code 为 `2`
- target file 缺失时返回 `bundle_request_target_not_found`，exit code 为 `2`

安全规则：`bundle-request` 只生成 agent handoff artifact，不生成语义内容，不调用隐藏 LLM，不修改 task status，不修改正文页面。

### `produce-bundle`
推荐用作 request artifact 到 patch bundle artifact 的显式外部 agent adapter。

常用：
- `produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py" --dry-run`
- `produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py"`
- `produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py" --timeout 120`

默认行为：
- 读取 `wikify.patch-bundle-request.v1`
- 解析调用方显式传入的 `--agent-command`
- 非 dry-run 时以 `shell=false` 执行外部 command
- 通过 stdin 向外部 command 传入完整 request JSON
- 向外部 command 暴露 `WIKIFY_BASE`、`WIKIFY_PATCH_BUNDLE_REQUEST`、`WIKIFY_PATCH_BUNDLE`
- 如果 stdout 非空，把 stdout 当作 `wikify.patch-bundle.v1` JSON 写入 request 的 `suggested_bundle_path`
- 如果 stdout 为空，接受外部 command 已写好的 `suggested_bundle_path`
- 对产出的 bundle 运行 deterministic preflight
- 返回 `wikify.patch-bundle-production.v1`
- 不修改 task status
- 不修改 topic、parsed、sorted 等正文页面

`produce-bundle --dry-run` 不执行外部 command，不写 patch bundle，不运行 preflight；它只校验 request、解析 command，并返回 invocation contract。

外部 command contract：
- stdin：完整 `wikify.patch-bundle-request.v1` JSON
- `WIKIFY_BASE`：wiki root 绝对路径
- `WIKIFY_PATCH_BUNDLE_REQUEST`：request artifact 绝对路径
- `WIKIFY_PATCH_BUNDLE`：建议 patch bundle 绝对路径

`wikify.patch-bundle-production.v1` schema:

```json
{
  "schema_version": "wikify.patch-bundle-production.v1",
  "base": "/abs/kb",
  "dry_run": false,
  "executed": true,
  "status": "bundle_ready",
  "request_path": "/abs/kb/sorted/graph-patch-bundle-requests/agent-task-1.json",
  "suggested_bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json",
  "task_id": "agent-task-1",
  "agent_command": ["python3", "agent.py"],
  "invocation": {
    "stdin": "wikify.patch-bundle-request.v1 JSON",
    "env": {
      "WIKIFY_BASE": "/abs/kb",
      "WIKIFY_PATCH_BUNDLE_REQUEST": "/abs/kb/sorted/graph-patch-bundle-requests/agent-task-1.json",
      "WIKIFY_PATCH_BUNDLE": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json"
    },
    "shell": false
  },
  "output_mode": "stdout",
  "artifacts": {
    "patch_bundle": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json"
  },
  "preflight": {
    "schema_version": "wikify.patch-application-preflight.v1",
    "status": "ready"
  },
  "summary": {
    "task_id": "agent-task-1",
    "operation_count": 1,
    "affected_paths": ["topics/a.md"]
  }
}
```

状态：
- `dry_run`
  - request 和 command contract 可用，但 command 未执行
- `bundle_ready`
  - bundle 已生成或已存在于 suggested path，并通过 apply preflight

错误：
- request 文件不存在时返回 `bundle_producer_request_not_found`，exit code 为 `2`
- request 不是合法 JSON 时返回 `bundle_producer_request_invalid_json`，exit code 为 `2`
- request schema 不支持时返回 `bundle_producer_request_schema_invalid`，exit code 为 `2`
- command 为空或无法解析时返回 `bundle_producer_command_invalid`，exit code 为 `2`
- 外部 command 非零退出时返回 `bundle_producer_command_failed`，exit code 为 `2`
- 外部 command 超时时返回 `bundle_producer_timeout`，exit code 为 `2`
- stdout 不是合法 bundle JSON 时返回 `bundle_producer_invalid_output`，exit code 为 `2`
- stdout 为空且 suggested bundle 文件不存在时返回 `bundle_producer_no_bundle_output`，exit code 为 `2`
- bundle preflight 失败时沿用 `patch_*` code，exit code 为 `2`，`details.phase` 为 `preflight`

安全规则：`produce-bundle` 只调用用户显式提供的外部 command，不内置 provider，不选择模型，不读取 API key，不重试 provider，不直接应用正文修改。正文修改仍然只能由 `apply` 或 `run-task` 在 bundle preflight 通过后执行。

### `apply`
推荐用作 agent-generated patch bundle 的 deterministic apply 入口。

常用：
- `apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json --dry-run`
- `apply --proposal-path sorted/graph-patch-proposals/agent-task-1.json --bundle-path sorted/graph-patch-bundles/agent-task-1.json`

默认行为：
- 读取 patch proposal
- 读取 patch bundle
- 校验 bundle task id 与 proposal task id 一致
- 校验 operation path 在 proposal `write_scope` 内
- 校验 operation path 是 wiki-root 内的相对路径
- 校验 `replace_text.find` 在目标文件里恰好出现一次
- 返回 `wikify.patch-application-preflight.v1` 或 `wikify.patch-application.v1`
- 非 dry-run 写入 `sorted/graph-patch-applications/<application-id>.json`

`apply --dry-run` 不修改正文页面，不写 application record。

patch bundle schema:

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

V1.2 operation 限制：
- 只支持 `replace_text`
- `find` 必须非空
- `replace` 必须是字符串
- `find` 和 `replace` 不能相同
- 每个文件当前只允许一个 operation
- `find` 必须在当前文件中恰好出现一次

application record schema:

```json
{
  "schema_version": "wikify.patch-application.v1",
  "application_id": "agent-task-1-20260428T061700Z",
  "created_at": "2026-04-28T06:17:00Z",
  "status": "applied",
  "task_id": "agent-task-1",
  "proposal_path": "/abs/kb/sorted/graph-patch-proposals/agent-task-1.json",
  "bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json",
  "affected_paths": ["topics/a.md"],
  "operations": [
    {
      "operation": "replace_text",
      "path": "topics/a.md",
      "find": "[[Missing]]",
      "replace": "[[Existing]]",
      "before_hash": "<sha256>",
      "after_hash": "<sha256>",
      "occurrences": 1
    }
  ],
  "rollback": {
    "status": "available",
    "guard": "current file hash must match operation after_hash"
  }
}
```

错误：
- proposal 不存在时返回 `patch_proposal_not_found`，exit code 为 `2`
- bundle 不存在时返回 `patch_bundle_not_found`，exit code 为 `2`
- bundle task id 与 proposal 不一致时返回 `patch_bundle_task_mismatch`，exit code 为 `2`
- operation path 超出 proposal write scope 时返回 `patch_operation_out_of_scope`，exit code 为 `2`
- 同一 path 多个 operation 时返回 `patch_operation_conflict`，exit code 为 `2`
- `find` 不是恰好出现一次时返回 `patch_preflight_failed`，exit code 为 `2`

安全规则：`apply` 只消费显式 patch bundle，不生成语义内容，不调用隐藏 LLM，不改变 task status。task 状态仍由 `tasks` lifecycle 命令显式推进。

### `rollback`
推荐用作 patch application 的 hash-guarded rollback 入口。

常用：
- `rollback --application-path sorted/graph-patch-applications/<application-id>.json --dry-run`
- `rollback --application-path sorted/graph-patch-applications/<application-id>.json`

默认行为：
- 读取 application record
- 按 operation 反向顺序检查当前文件 hash
- 只有当前内容 hash 等于 recorded `after_hash` 时才执行恢复
- dry-run 只做校验，不写正文，不更新 application record
- 非 dry-run 写回原文本，并把 application record 标记为 `rolled_back`

rollback 成功返回 `wikify.patch-rollback.v1`。

错误：
- application record 不存在时返回 `patch_application_not_found`，exit code 为 `2`
- 当前文件内容与 recorded `after_hash` 不一致时返回 `patch_rollback_hash_mismatch`，exit code 为 `2`
- rollback 目标文本不再唯一时返回 `patch_rollback_preflight_failed`，exit code 为 `2`

### `run-task`
推荐用作单个 graph agent task 的低打扰 workflow runner。

常用：
- `run-task --id agent-task-1 --dry-run`
- `run-task --id agent-task-1`
- `run-task --id agent-task-1 --bundle-path sorted/graph-patch-bundles/custom.json`
- `run-task --id agent-task-1 --agent-command "python3 agent.py" --producer-timeout 120`
- `produce-bundle --request-path sorted/graph-patch-bundle-requests/agent-task-1.json --agent-command "python3 agent.py"`
- `run-task --id agent-task-1`

默认行为：
- 读取 `sorted/graph-agent-tasks.json`
- 选择指定 task id
- 创建或复用 `sorted/graph-patch-proposals/<task-id>.json`
- 如果 task 仍是 `queued`，非 dry-run 会通过 lifecycle 标记为 `proposed`
- 查找 patch bundle，默认路径为 `sorted/graph-patch-bundles/<task-id>.json`
- bundle 缺失时写入 `sorted/graph-patch-bundle-requests/<task-id>.json`
- bundle 缺失时返回 `waiting_for_patch_bundle` 和 `next_actions: ["generate_patch_bundle"]`
- 上层 agent 可调用 `produce-bundle` 执行显式外部 command 生成 bundle，再重试 `run-task`
- 如果调用方提供 `--agent-command`，bundle 缺失时 runner 会调用 producer 生成并 preflight bundle，然后继续 apply 和 mark-done
- 如果 bundle 已存在，即使提供 `--agent-command` 也不会执行 producer command
- bundle 存在时通过 deterministic `apply` 合约应用
- apply 成功后通过 lifecycle 标记 task 为 `done`

`run-task --dry-run` 不写 proposal，不写 bundle request，不写 lifecycle event，不改正文，不写 application record。`run-task --dry-run --agent-command <command>` 也不执行 command，不写 patch bundle。

返回 schema:

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
    "next_action": "generate_patch_bundle",
    "bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json",
    "bundle_request_path": "/abs/kb/sorted/graph-patch-bundle-requests/agent-task-1.json",
    "suggested_bundle_path": "/abs/kb/sorted/graph-patch-bundles/agent-task-1.json"
  }
}
```

状态：
- `waiting_for_patch_bundle`
  - runner 已尽可能推进，并已写入 patch bundle request；下一步由 agent 读取 request 生成 patch bundle，或调用 `produce-bundle` 委托显式外部 command 生成 patch bundle
- `ready_to_apply`
  - dry-run 已确认 proposal 和 bundle 可用于后续非 dry-run
- `completed`
  - apply 已完成，task lifecycle 已 mark-done

错误：
- 缺少 task queue 时返回 `agent_task_queue_missing`，exit code 为 `2`
- 找不到 task id 时返回 `agent_task_not_found`，exit code 为 `2`
- proposal 阶段错误沿用 `proposal_*` code，exit code 为 `2`
- bundle request 阶段错误沿用 `bundle_request_*` code，exit code 为 `2`，`details.phase` 为 `bundle_request`
- producer 阶段错误沿用 `bundle_producer_*` code，exit code 为 `2`，`details.phase` 为 `bundle_producer`
- apply 阶段错误沿用 `patch_*` code，exit code 为 `2`
- lifecycle 阶段错误沿用 `invalid_agent_task_transition` 等 code，exit code 为 `2`

安全规则：`run-task` 只编排现有 audited primitives。默认情况下它可以生成 patch bundle request，但不生成 patch bundle，不调用隐藏 LLM，不提示用户审批。只有调用方显式传入 `--agent-command` 时，它才会执行外部 producer command；provider、模型、密钥、retry 均不由 Wikify 隐式决定。

### `run-tasks`
推荐用作 bounded batch task automation。

常用：
- `run-tasks --dry-run`
- `run-tasks --limit 5 --agent-command "python3 agent.py"`
- `run-tasks --status queued --action queue_link_repair --limit 5 --agent-command "python3 agent.py"`
- `run-tasks --status queued --limit 5 --continue-on-error --agent-command "python3 agent.py"`

默认行为：
- 读取 `sorted/graph-agent-tasks.json`
- 默认选择 `status=queued`
- 默认 `limit=5`
- 按队列顺序顺序执行
- 每个 task 都调用现有 `run-task` 工作流
- 默认遇到第一个 per-task failure 停止
- 显式 `--continue-on-error` 时记录失败并继续后续 task
- 不新增 apply 语义，不并发执行

`run-tasks --dry-run` 在整个 batch 中不写 proposal、不写 bundle request、不写 patch bundle、不写 lifecycle event、不改正文、不写 application record。即使传入 `--agent-command`，dry-run 也不执行外部 command。

如果调用方需要“刷新维护发现并立刻处理一批 queued tasks”，应优先调用 `maintain-run`，而不是手工串 `maintain` 和 `run-tasks`。

`wikify.agent-task-batch-run.v1` schema:

```json
{
  "schema_version": "wikify.agent-task-batch-run.v1",
  "base": "/abs/kb",
  "dry_run": false,
  "status": "completed",
  "selection": {
    "status": "queued",
    "action": null,
    "id": null,
    "limit": 5,
    "source_schema_version": "wikify.graph-agent-tasks.v1",
    "total_task_count": 7
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
  },
  "next_actions": []
}
```

状态：
- `no_tasks`
  - 筛选后没有 task
- `dry_run`
  - 完成预演且零写入
- `completed`
  - 所有 selected tasks 完成
- `waiting_for_patch_bundle`
  - 至少一个 task 等待 bundle，且没有失败
- `stopped_on_error`
  - 默认 stop-on-error 触发
- `completed_with_errors`
  - `--continue-on-error` 模式下至少一个 task 失败，但 batch 跑完 selected tasks

错误：
- 缺少 task queue 时返回 `agent_task_queue_missing`，exit code 为 `2`
- 找不到指定 task id 时返回 `agent_task_not_found`，exit code 为 `2`
- 单个 task 失败不会让 batch command 变成 envelope error；失败进入 `items[].error`，batch status 进入 `stopped_on_error` 或 `completed_with_errors`

安全规则：`run-tasks` 是 bounded sequential orchestration。默认 limit 5、默认 stop-on-error。它只组合 `run-task`，不绕过 proposal/write_scope/preflight/apply/rollback/lifecycle 规则。只有显式 `--agent-command` 才会触发外部 command。

### `decide`
推荐用作 agent decision workflow 的最小接线入口。
优先应使用显式输入来源，而不是模糊依赖 history tail。

推荐方式：
- `decide --maintenance-path <path>` 基于显式 changed object 生成 decision
- `decide --last` 作为兼容模式，表示读取 maintenance history 最后一条

使用 `--execute` 时，会按当前 decision plan 执行最小 action。

返回结构：
```json
{
  "maintenance": {},
  "decision": {
    "verdict": "needs_promotion",
    "actions": [
      "promote_to_topic_or_timeline",
      "prepare_promotion_candidates"
    ],
    "rationale": [
      "maintenance verdict indicates stable promotion opportunity"
    ],
    "promotion_targets": []
  }
}
```

### decision schema v2
- `decision.verdict`
  - 通常继承 maintenance verdict
- `decision.actions`
  - 保留的兼容字段，供旧调用方读取
- `decision.rationale`
  - 保留的兼容字段
- `decision.promotion_targets`
  - 保留的兼容字段
- `decision.steps`
  - agent 应优先消费的机械执行计划数组
- `decision_source`
  - 决策输入来源摘要，避免 workflow 中误读 history tail
- `execution`
  - 可选，仅在 `decide --execute` 时出现，表示按 decision plan 实际执行的动作结果

### decision step schema v2
- `action`
- `target`
- `args`
- `can_execute`
- `idempotent`
- `retryable`
- `reason`
- `expected_result`

### execution result schema v2
- `action`
- `target`
- `status`
- `reason`
- `result`
  - action 原始结果，保留兼容与调试价值
- `artifacts`
  - `created[]` / `updated[]` / `skipped[]`
- `state_change`
  - 本 step 对控制状态的结构化影响摘要
- `side_effects`
  - 简短副作用标签数组

### completion schema v1
- `status`
- `summary`
- `artifacts`
- `next_actions`
- `user_message`

推荐在聊天场景、agent 回执和 UI 完成提示中优先消费 `result.completion`，而不是每次由上层自行拼装完成提醒。

### digest policy schema v1
- `eligible`
- `mode`
- `primary_topic`
- `recommended_action`
- `reason`
- `blocking_reasons`

仅在 `ingest` / `reingest` 成功结果中出现，路径为 `result.digest_policy`。

### digest trigger rule v1
`digest` 视为二阶段收束动作，不默认等同于 `ingest` 主流程。

#### 显式触发
以下情况可以直接运行 digest：
- 用户或上层 agent 明确要求生成 digest
- 调用 `digest <topic>`
- 调用 `ingest --with-digests` 或 `reingest --with-digests`

#### 自动触发资格
在没有显式要求时，只有同时满足以下条件，agent 才应自动跟进 `digest_optional`：
- `result.quality.review_required == false`
- `result.lifecycle_status == "integrated"`
- `result.routing.primary_topic` 存在
- `result.updated_topics` 非空
- `result.next_actions` 包含 `digest_optional`

#### 自动触发抑制条件
满足以下任一条件时，不应自动 digest：
- `result.quality.review_required == true`
- `result.routing.primary_topic` 缺失
- `result.lifecycle_status != "integrated"`
- 本次只完成抓取/解析，但没有稳定 topic 更新

#### agent 默认策略
- 主流程先完成 `ingest` / `reingest`，优先交付入库结果与 completion
- 遇到 `digest_optional` 时，把它视为“可跟进动作”，而不是“必须立即执行”
- 只有在满足自动触发资格，且调用方希望做二阶段收束时，才继续跑 digest
- `result.completion.next_actions` 会按 `result.digest_policy` 收口：只有 `eligible == true` 时才保留 `digest_optional`

### action registry v1
- `no_immediate_action`
- `monitor_and_collect_more_evidence`
- `manual_review_required`
- `promote_to_topic_or_timeline`
- `prepare_promotion_candidates`

### `promote`
最小可用 action 命令。当前 v1 支持把 `sorted` 候选对象提升为 `topics` 下的稳定 topic skeleton。

提升后的 topic skeleton 会带 `来源候选` 区块，maintenance 会把它识别为 `topic_seed_source_present`，而不是直接视为缺失回链的错误对象。
同时，template-aware extraction guardrail 会尽量跳过 skeleton 模板句，并抑制 markdown link / slug fragment 噪声及 placeholder semantic words，避免把占位文本误识别成真实 concept / claim。

## 11. Agent 调用建议

### 优先使用字段
- `ok`
- `exit_code`
- `command`
- `result`
- `error.code`
- `error.retryable`
- `result.maintenance.verdict`
- `result.maintenance.changed_objects`

### 推荐调用模式
#### 写操作后
优先读取：
- `result.maintenance.verdict`
- `result.maintenance.changed_objects[*].verdict`
- `result.maintenance.changed_objects[*].promotion_candidate`

#### 需要下一步动作时
优先读取：
- `decide --last`
- `decision.actions`
- `decision.promotion_targets`
- `result.digest_policy`

#### 控制面板 / 后台巡检
优先读取：
- `stats`
- `maintenance --last`
- `maintenance --limit N`
- `state`

### 不建议依赖
- 原始 stdout 文案
- `error.message` 措辞细节
- `pretty` 输出格式细节

## 12. 兼容性原则

- 新增字段允许
- 既有字段尽量不改名
- `ok / command / exit_code / result / error` 视为稳定保留字段
- `maintenance.verdict / maintenance.changed_objects / contradiction.baseline_side / decision.actions` 进入稳定协议面
- 算法可演进，但字段语义尽量保持稳定

## 13. 当前已知边界

- `claim extraction` 仍是 heuristic v1，不是完整语义解析
- `canonical_subject` 仍是弱归一化，不是完整 entity resolution
- `baseline_side` 表示维护判断倾向，不代表真实世界最终真值
- 对 `count: 0` 的 zero-context synthesis，可能没有邻域对象、claims 或 contradictions，这属于正常行为
- 对 zero-context changed object，`needs_promotion` 会被 guardrail 抑制，避免标题词噪声直接触发 promotion

## 14. 后续演进方向

- 更强的 subject clustering / entity resolution
- promotion 动作建议结构化
- verdict 到 action plan 的直接映射
- maintenance schema 单独版本化
