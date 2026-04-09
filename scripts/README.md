# Scripts Index

这个目录下的脚本已经不算少了，后续统一按“入口层 / 底层 / 维护层”来理解。

## 一、最常用入口

### 0. `fokb.py`
面向 agent 的统一 CLI 入口。

推荐优先使用：

```bash
python3 scripts/fokb.py init
python3 scripts/fokb.py check
python3 scripts/fokb.py stats
python3 scripts/fokb.py maintenance --last
python3 scripts/fokb.py decide --last
python3 scripts/fokb.py decide --last --execute
python3 scripts/fokb.py promote sorted/sample-summary.md
python3 scripts/fokb.py lint --deep
python3 scripts/fokb.py list topics
python3 scripts/fokb.py search "quantum"
python3 scripts/fokb.py show quantum-computing-industry --scope topics
python3 scripts/fokb.py query "quantum financing"
python3 scripts/fokb.py writeback "quantum financing" --title "Quantum Financing Notes"
python3 scripts/fokb.py synthesize "quantum financing" --mode outline --title "Quantum Financing Outline"
python3 scripts/fokb.py ingest "<url>"
python3 scripts/fokb.py lint
python3 scripts/fokb.py status
python3 scripts/fokb.py review
python3 scripts/fokb.py review --summary
python3 scripts/fokb.py review --count
python3 scripts/fokb.py review --urls-only
python3 scripts/fokb.py reingest --last
python3 scripts/fokb.py resolve --last
python3 scripts/fokb.py --output pretty status
python3 scripts/fokb.py --output quiet lint
python3 scripts/fokb.py state
```

说明：
- `fokb` = File Organizer Knowledge Base
- 目标不是给人做 UI，而是给 agent 一个稳定 CLI 外壳
- 后续新能力优先挂到 `fokb.py` 子命令上，而不是继续散落成更多入口
- 协议说明见：`scripts/fokb_protocol.md`
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

推荐优先使用：

```bash
python3 scripts/ingest_any_url.py "<url>"
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

### 7. `source_index_manager.py`
统一维护 `sources/index.md` 的状态与统计。

### 8. `generate_topic_digest.py`
从 topic 生成 digest 输出。

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
