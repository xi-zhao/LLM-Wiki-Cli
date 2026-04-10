# LLM Wiki Schema

本文件把 `file-organizer/` 约定为一个由 LLM 维护的持久化知识库，而不是一次性资料堆。

这套 schema 的总体方向明确参考了 Andrej Karpathy 的 LLM Wiki / markdown-first knowledge workflow 思路，也就是先把资料编译成可维护的 Markdown wiki，再让后续问答、维护和产出围绕这层知识资产展开。

## 1. 目标

LLM Wiki 的目标不是在用户提问时临时从原文里重新检索一遍，而是把信息逐步编译成可复用、可链接、可持续维护的 markdown wiki。这一点本身就延续了 Karpathy 那条路线的核心判断，也就是“先整理成 wiki，再围绕 wiki 工作”，而不是每次都回到原始资料堆里重新检索。

这套目录有三层：

1. `articles/raw/`：原始资料留底，视为不可变 source of truth
2. `articles/parsed/`、`articles/briefs/`、`topics/`、`timelines/`、`sorted/`：LLM 维护的 wiki 层
3. `WIKI_SCHEMA.md`、`sources/index.md`：约束结构和导航方式的 schema/index 层

## 2. 目录角色

### 原始层
- `inbox/`：待处理输入
- `articles/raw/`：原文、摘录、抓取结果
- `materials/wechat/`、`materials/web/`、`materials/local/`：页面素材包、图片、HTML、文本等

### 编译层
- `articles/parsed/`：单篇材料的结构化文章卡
- `articles/briefs/`：一页式 brief，面向快速消费
- `topics/`：长期主题卡，是知识复利的核心单元
- `timelines/`：跟踪演化、节点变化、阶段判断
- `sorted/`：按主题生成的综述、digest、可直接输出的成品草稿

### 导航层
- `sources/index.md`：内容目录，优先供 LLM 查询入口使用
- `WIKI_SCHEMA.md`：告诉代理如何 ingest、query、lint、maintain

## 3. 基本工作流

### Ingest
当新增一篇文章、网页、笔记或其他材料时：

1. 先保存 raw source，不要直接只写总结
2. 创建或更新 parsed 卡
3. 创建或更新 brief
4. 更新一个或多个 topic 文件
5. 如果有明显时间演化意义，更新 timeline
6. 更新 `sources/index.md`
7. 在必要时维护 `sorted/` 里的 digest 或专题输出

原则：一次 ingest 不应只停在“抓到原文”这一步。

### 聊天触发约定
在当前工作流中，用户只要发送 URL，并伴随以下意图表达之一：
- “记录这个”
- “收一下”
- “整理一下”
- “存一下”
- “归档这个”

默认都视为 **直接进入 wiki ingest**。

执行规则：
1. 优先调用统一入口：`python3 file-organizer/scripts/ingest_any_url.py "<url>"`
2. 不要再手工判断走哪个单独脚本，除非统一入口失败
3. 若用户同时明确要求“顺手产出专题综述/摘要”，可追加 `--with-digests`
4. 若只给了链接、未给更多说明，也默认先入库，再在回执里说明已完成归档

换句话说，聊天里的“发链接 + 记录类动词”应被当成标准化入库指令，而不是普通聊天消息。

### Query
当用户围绕某主题提问时：

1. 先读 `sources/index.md` 找候选条目和主题
2. 再读相关 `topics/`、`timelines/`、`articles/parsed/`
3. 尽量基于已编译的 wiki 回答，而不是每次重新翻 raw
4. 如果回答本身具有长期复用价值，可以沉淀到 `sorted/` 或相应 topic 中

### Lint / Maintenance
定期检查：

- 有没有 topic 已有相关文章但未更新
- 有没有 parsed 文件缺少 topic 关联
- 有没有 timeline 可以从“散点观察”升级为结构化时间线
- 有没有 `sorted/` digest 应该重生成
- 有没有重复 topic 需要合并
- 有没有稳定结论该从文章卡提升到主题卡

## 4. 文件规范

### parsed 文件
每篇材料至少包含：
- 元信息
- 一句话摘要
- 核心结论
- 关键事实 / 证据
- 可复用素材
- 风险 / 待验证
- 关联主题

### topic 文件
topic 是长期复用单元，优先维护：
- 主题定义
- 当前核心问题
- 稳定结论
- 新增观察（按月份追加）
- 代表性案例 / 证据
- 可输出方向
- 关联文章
- 待跟进

### timeline 文件
适合处理：
- 行业阶段变化
- 技术路线切换
- 公司动作序列
- 融资、发布、政策、能力演进

### sorted 文件
适合保存：
- 主题综述
- 领导简报
- PPT 提纲
- 阶段性判断
- 问答沉淀后可复用的输出稿

## 5. 链接和命名

- 文件命名尽量稳定、可排序：`YYYY-MM-DD_slug.md`
- topic / timeline 名称使用稳定英文 slug
- parsed 与 brief 尽量反链到 topic
- topic 中应显式链接代表性 parsed 文件
- 用户经常问的问题，如果可复用，应进入 `sorted/`

## 6. 查询优先级

当信息足够时，优先读取顺序：

1. `sources/index.md`
2. `topics/*.md`
3. `timelines/*.md`
4. `sorted/*.md`
5. `articles/parsed/*.md`
6. `articles/raw/*.md`
7. `materials/*`

即：先读编译后的知识，再读原文证据。

## 7. 维护原则

- Preserve detail first, summarize second
- 区分事实、判断、猜测
- 对不确定内容明确标记
- 不为了“结构完整”伪造结论
- 尽量少建低质量 topic，多维护高价值 topic
- 让 wiki 变成“越用越强”的中间层，而不是归档墓地

## 8. 与当前脚本的关系

当前已有脚本：
- `scripts/ingest_any_url.py`
- `scripts/ingest_wechat_direct_url.py`
- `scripts/ingest_web_direct_url.py`
- `scripts/generate_topic_digest.py`
- `scripts/maintain_wechat_knowledge_base.py`
- `scripts/wiki_lint.py`

默认入口应是 `scripts/ingest_any_url.py`。
只有在统一入口失败、或明确需要单独调试某一类 source 时，才直接调用底层脚本。

后续新脚本应优先遵守本 schema，而不是各自定义一套目录和产物。

## 9. 最小可行判断

如果时间紧，只做最小闭环也至少要完成：

- raw
- parsed
- sources/index.md
- 至少一个 topic 的更新或显式标记“暂未归入主题”

如果用户要求“记录这个”，默认目标仍然是进入 wiki，而不是只把链接存下来。

如果用户只发链接但上下文明显处于 file-organizer 归档流程中，也默认按可入库链接处理。
