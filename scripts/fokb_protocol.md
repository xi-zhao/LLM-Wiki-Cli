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

### 巡检层
- `lint`
- `lint --deep`

## 5. Maintenance schema v1

`maintenance` 是 `wikify` 当前最重要的增量知识维护协议层之一。`graph` 是结构理解协议层，负责把已编译 Markdown wiki 转成可审计图谱产物。

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
