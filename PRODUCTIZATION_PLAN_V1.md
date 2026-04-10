# File Organizer 产品化改造方案 V1

## 1. 文档目的

本方案不再从“脚本能不能跑”出发，而是从成熟产品视角重构 `file-organizer/`。
目标是把当前的归档流水线，升级为一个 **可预测、可解释、可恢复、可运营** 的知识入库产品。

---

## 2. 当前产品现状判断

当前已经具备的能力：
- 聊天触发入库
- 微信 / 网页统一 ingest 入口
- raw / parsed / brief / source index 产出
- 初步 topic 路由
- 初步 topic 增量维护
- wiki lint

当前主要问题不在“有没有功能”，而在：
1. 同类输入结果不稳定
2. 抽取质量没有质量门禁
3. 状态模型不完整
4. 自动维护结果不够可解释
5. 失败链路不够可恢复
6. 缺少运营视图和质量指标

一句话判断：
**现在更像一套能力很强的内部流水线，而不是一个成熟产品。**

---

## 3. 产品目标

### 3.1 短期目标
把系统从“脚本组合”提升为“有稳定状态机的入库产品”。

### 3.2 中期目标
把 topic / timeline / digest 的维护变成可持续、可观测、可治理的自动化系统。

### 3.3 长期目标
把 `file-organizer/` 做成一个真正的 LLM Wiki 产品底座，支持：
- 多源入库
- 自动知识编译
- 自动维护
- 高质量输出
- 运维视图

---

## 4. 产品原则

### 4.1 质量优先于自动化广度
宁可少自动一点，也不能把脏正文、脏摘要、脏 topic 混进系统。

### 4.2 状态清晰优先于表面成功
不要把“抓错了但产出了文件”当成成功。

### 4.3 降级优先于中断
抓取失败、topic 失败、digest 失败都应允许局部失败，不阻塞整条链路。

### 4.4 结果必须可解释
系统应能回答：
- 为什么进了这个 topic
- 为什么没进
- 为什么需要人工复核

### 4.5 输出必须面向用户价值
用户不关心内部产物分层，用户关心：
- 最终是否进库
- 是否可复用
- 是否能直接拿去用

---

## 5. 建议的正式状态机

为 source entry 与单篇条目引入统一生命周期：

- `captured`：已抓到原始材料
- `parsed`：已完成结构化文章卡
- `briefed`：已生成 brief
- `linked`：已建立有效 topic 关联
- `integrated`：topic 已吸收主要信息
- `digested`：已进入专题输出 / digest
- `needs_review`：抽取、分类或维护质量可疑
- `failed`：关键步骤失败

### 状态说明
- `captured` 不代表内容质量达标，只代表拿到了材料
- `linked` 代表 parsed 与 topic 已建立可验证关系
- `integrated` 代表 topic 已有实质增量，不只是挂了个链接
- `needs_review` 是一种可运营状态，不是失败

### 当前建议
短期不要一次性替换全部历史状态，可先做兼容：
- 现有 `briefed` 保留
- 新流程内部增加更细粒度状态字段
- `sources/index.md` 先逐步扩展，不立即强制迁移全部存量

---

## 6. 质量门禁（Quality Gate）

这是当前最重要的新模块。

### 6.1 正文提取质量检查
每次 ingest 后，新增 `extraction_quality` 判定：
- `high`
- `medium`
- `low`

### 6.2 建议检查项
- 正文长度是否低于阈值
- 是否命中站点 chrome 噪音（登录提示、导航、页脚、share 文案）
- 是否存在高比例重复短句
- 是否提取到了主内容结构（段落、标题、正文块）
- source_account / title / publish_time 是否明显异常

### 6.3 质量门禁策略
- `high`：允许正常进入后续总结和 topic 维护
- `medium`：允许继续，但标记 `needs_review`
- `low`：保留 raw 与 materials，停止强总结与 topic 集成，标记 `needs_review`

### 6.4 产品收益
这一步会显著减少“看起来成功，实际进脏数据”的情况。

---

## 7. 结构化结果模型

统一 ingest 的返回结果应正规化为结构化事件结果，而不是仅靠零散字段。

建议格式：

```json
{
  "status": "linked",
  "source_type": "web",
  "quality": {
    "extraction": "high",
    "routing": "medium",
    "review_required": false
  },
  "files": {
    "raw": "...",
    "parsed": "...",
    "brief": "..."
  },
  "routing": {
    "topics_detected": ["ai-research-writing.md", "ai-coding-and-autoresearch.md"],
    "primary_topic": "ai-research-writing.md",
    "secondary_topics": ["ai-coding-and-autoresearch.md"],
    "reasons": ["matched persistent wiki", "matched agent/skills vocabulary"]
  },
  "topic_updates": [
    {
      "topic": "ai-research-writing.md",
      "actions": ["append_observation", "append_related_article"],
      "status": "updated"
    }
  ],
  "next_actions": ["generate_digest", "needs_review"]
}
```

### 核心目的
让系统对外解释自己做了什么，而不是只产出文件。

---

## 8. Topic 路由产品化

### 8.1 当前问题
现在 topic 路由仍主要靠硬编码关键词，维护成本会越来越高。

### 8.2 建议方案
把路由规则抽成独立配置文件，例如：
- `config/topic_rules.json`

建议字段：
- topic 文件名
- 主命中词
- 辅命中词
- 排除词
- 最低命中阈值
- 是否允许作为 primary topic

### 8.3 路由结果分层
- `primary_topic`
- `secondary_topics`
- `candidate_topics`

### 8.4 产品收益
- 规则可调，不必频繁改 Python
- 更方便灰度和回归测试
- 更接近成熟产品的“策略层 / 引擎层”分离

---

## 9. Topic 增量维护产品化

### 9.1 当前问题
虽然已经有 `topic_maintainer.py`，但维护结果还不够产品化。

### 9.2 应升级的能力
每次维护 topic 后，返回：
- 命中的 topic
- 实际更新了什么 section
- 是否只是补了链接
- 是否完成了真正的 integrated

### 9.3 建议动作类型
- `append_observation`
- `append_evidence`
- `append_related_article`
- `bootstrap_topic`
- `promote_stable_conclusion`
- `no_change`

### 9.4 产品收益
能真正区分“挂了链接”和“吸收了知识”。

---

## 10. 失败恢复机制

成熟产品必须允许失败，但不能无法恢复。

### 10.1 典型失败类型
- 抓取失败
- 正文提取失败
- source 元信息异常
- topic 路由为空
- topic 维护失败
- digest 失败

### 10.2 建议恢复策略
- 抓取失败：保留失败原因，允许重跑
- 提取失败：保留 raw/materials，标 `needs_review`
- topic 失败：文章先保留，状态标 `briefed` 或 `needs_review`
- digest 失败：不影响 source 入库主流程

### 10.3 建议新增文件
- `sorted/ingest-failures.json`
- `sorted/review-queue.json`

---

## 11. 输出层产品化

建议标准化 4 类输出：

### 11.1 归档回执
面向用户即时反馈。

### 11.2 领导摘要
100-300 字，可直接聊天回复。

### 11.3 专题 digest
沉淀进 `sorted/`，面向后续复用。

### 11.4 PPT 提纲
面向 presentation 场景。

当前系统更偏“资料产品”，下一步要变成“知识 + 输出产品”。

---

## 12. 运营视图（Dashboard）

建议增加一个轻量 dashboard 文件，例如：
- `sorted/dashboard.md`

建议展示：
- 今日新增入库数
- 最近 7 天入库数
- 失败条目数
- needs_review 条目数
- topic 最后更新时间
- topic 厚度排名
- 最近自动生成的 digest

这一步会让系统从“能跑”进入“可运营”。

---

## 13. 指标体系（Metrics）

建议从最小指标集开始：

- ingest 成功率
- 抽取质量 high/medium/low 占比
- topic 命中率
- topic 自动更新成功率
- needs_review 占比
- digest 生成数
- digest 被实际引用/复用次数（后续可扩展）

没有指标，就无法做真正的产品迭代。

---

## 14. 建议路线图

### Phase 1，底盘稳定
1. 质量门禁
2. 正式状态机
3. 结构化结果模型

### Phase 2，策略产品化
4. topic 路由配置化
5. topic 更新结果结构化
6. 失败恢复与 review queue

### Phase 3，运营化
7. dashboard
8. 指标体系
9. 输出模板升级

---

## 15. 推荐下一步

如果只做一件事，我建议先做：

### **状态机 + 质量门禁 + 结构化结果 三件套**

原因：
- 它们直接决定系统是否可控
- 它们是后续 dashboard、metrics、review 流程的前提
- 它们比继续补单点功能更接近成熟产品的底层能力

---

## 16. 一句话总结

当前 `file-organizer` 已经证明“这个方向可行”；
下一阶段的核心不是继续加脚本，而是把它打磨成一个：

**可预测、可解释、可恢复、可运营的知识入库产品。**
