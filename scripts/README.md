# Scripts Index

这个目录下的脚本已经不算少了，后续统一按“入口层 / 底层 / 维护层”来理解。

## 一、最常用入口

### 0. `fokb.py`
面向 agent 的统一 CLI 入口。

推荐优先使用：

```bash
python3 file-organizer/scripts/fokb.py init
python3 file-organizer/scripts/fokb.py check
python3 file-organizer/scripts/fokb.py stats
python3 file-organizer/scripts/fokb.py maintenance --last
python3 file-organizer/scripts/fokb.py decide --last
python3 file-organizer/scripts/fokb.py decide --last --execute
python3 file-organizer/scripts/fokb.py promote file-organizer/sorted/wechat-agent-summary.md
python3 file-organizer/scripts/fokb.py lint --deep
python3 file-organizer/scripts/fokb.py list topics
python3 file-organizer/scripts/fokb.py search "quantum"
python3 file-organizer/scripts/fokb.py show quantum-computing-industry --scope topics
python3 file-organizer/scripts/fokb.py query "quantum financing"
python3 file-organizer/scripts/fokb.py writeback "quantum financing" --title "Quantum Financing Notes"
python3 file-organizer/scripts/fokb.py synthesize "quantum financing" --mode outline --title "Quantum Financing Outline"
python3 file-organizer/scripts/fokb.py ingest "<url>"
python3 file-organizer/scripts/fokb.py lint
python3 file-organizer/scripts/fokb.py status
python3 file-organizer/scripts/fokb.py review
python3 file-organizer/scripts/fokb.py review --summary
python3 file-organizer/scripts/fokb.py review --count
python3 file-organizer/scripts/fokb.py review --urls-only
python3 file-organizer/scripts/fokb.py reingest --last
python3 file-organizer/scripts/fokb.py resolve --last
python3 file-organizer/scripts/fokb.py --output pretty status
python3 file-organizer/scripts/fokb.py --output quiet lint
python3 file-organizer/scripts/fokb.py state
```

说明：
- `fokb` = File Organizer Knowledge Base
- 目标不是给人做 UI，而是给 agent 一个稳定 CLI 外壳
- 后续新能力优先挂到 `fokb.py` 子命令上，而不是继续散落成更多入口
- 协议说明见：`file-organizer/scripts/fokb_protocol.md`
- 对 agent / UI 而言，优先消费结构化字段，而不是依赖 pretty 输出文案
- `decide` 现已输出 `steps[]`，agent 应优先消费 step contract，而不是自行拼装 actions + targets
- `decide --execute` 产生的 action provenance 也会继续进入 maintenance/history

### 1. `ingest_any_url.py`
统一入库入口。

用途：
- 自动识别微信公众号链接 / 普通网页链接
- 调起对应底层 ingest
- 自动维护 topic
- 自动跑结果增强与质量评估
- 可选生成 digest

digest 规则：
- 默认不把 digest 当成 ingest 的硬绑定步骤
- 当结果已 `integrated`、`review_required = false`、存在 `primary_topic` 且 `next_actions` 包含 `digest_optional` 时，可由上层 agent 自动跟进 digest
- 若需要强制执行，可显式使用 `--with-digests`

推荐优先使用：

```bash
python3 file-organizer/scripts/ingest_any_url.py "<url>"
```

### 2. `wiki_lint.py`
知识库健康检查入口。

用途：
- 检查 schema/index
- 检查 parsed 是否缺 topic link
- 生成 lint 报告

---

## 二、底层 ingest 脚本

### 3. `ingest_wechat_direct_url.py`
微信公众号文章入库底层脚本。

### 4. `ingest_web_direct_url.py`
普通网页入库底层脚本。

说明：
- 一般不要直接先调这两个
- 默认优先走 `ingest_any_url.py`
- 只有调试具体 source 类型时才直接用

---

## 三、结果增强与维护

### 5. `ingest_result_enricher.py`
给 ingest 结果补充产品化字段：
- quality
- routing
- lifecycle_status
- review queue

### 6. `topic_maintainer.py`
在 ingest 后自动维护 topic 文件。

当前 topic 默认往 Obsidian-friendly 结构收：
- YAML frontmatter
- `## 笔记关系`
- `## 关联笔记（Obsidian）`
- 自动维护 `topics-moc.md`
- 保留原有 `关联文章` markdown 路径，兼顾现有维护协议

### 7. `source_index_manager.py`
统一维护 `sources/index.md` 的状态与统计。

### 8. `generate_topic_digest.py`
从 topic 生成 digest 输出。

当前 digest 默认按 Obsidian-friendly Markdown 产出：
- YAML frontmatter
- `[[wikilink]]` 关联 topic / article
- 更适合放进图谱、双链和 MOC 工作流
- 生成后会自动刷新 `topics-moc.md` 与 `sources/sources-index.md`

当前 parsed/article note 也开始往 Obsidian-friendly 收：
- YAML frontmatter
- `## 笔记关系`
- `## 关联笔记（Obsidian）`
- brief note 也补 frontmatter 和导航关系
- 同时保留 `## 关联主题` 原字段，兼顾现有 lint / maintenance 协议

---

## 四、抓取与素材处理

### 9. `fetch_wechat_article.py`
公众号文章抓取。

### 10. `fetch_web_article.py`
普通网页抓取。

### 11. `normalize_wechat_materials.py`
清洗公众号素材目录。

### 12. `build_wechat_assets_summary.py`
生成素材摘要。

### 13. `enrich_wechat_assets_semantics.py`
对公众号素材做语义增强。

---

## 五、历史脚本 / 专项脚本

### 14. `maintain_wechat_knowledge_base.py`
偏向早期微信知识库维护检查。

后续如果能力都迁入统一产品链路，这个脚本可逐步弱化或并入统一 maintenance。

---

## 六、命名约定

为了避免再出现 `ingestresultenricher.py` 这种误写，统一采用：

- 单词之间一律用下划线 `_`
- 动词在前，对象在后
- 入口脚本尽量可读可猜

例如：
- `ingest_any_url.py`
- `ingest_result_enricher.py`
- `source_index_manager.py`
- `topic_maintainer.py`

### 常见易错项

错误：
- `ingestresultenricher.py`
- `topicmaintainer.py`
- `sourceindexmanager.py`

正确：
- `ingest_result_enricher.py`
- `topic_maintainer.py`
- `source_index_manager.py`

---

## 七、一句话建议

如果不确定调用哪个脚本：

1. 入库 → `ingest_any_url.py`
2. 检查 → `wiki_lint.py`
3. 其余脚本默认视为底层或维护组件
