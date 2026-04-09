# LLM-Wiki-Cli

LLM-Wiki-Cli 是一个面向 agent 的 markdown 知识库控制 CLI，当前主入口为：

```bash
python3 scripts/fokb.py ...
```

安装后也可直接使用：

```bash
fokb ...
```

## 仓库状态

- 当前版本：`0.1.0a1`
- 发布定位：public alpha
- 样例内容：最小公开样例，仅用于演示和验证
- 许可证状态：见 `LICENSE.md`

## 这是什么

它的目标不是做人类终端 UI，而是给 agent 一个稳定的控制面，用来：

- ingest 新材料
- 查询知识对象
- 生成整理输出
- 做增量 maintenance
- 生成 decision plan
- 执行动作并记录 provenance
- 查询 history / state

## 文档分层

### 1. 完整产品说明
请优先阅读：

- `LLM-Wiki-Cli-README.md`

适合了解：
- 产品定位
- 核心能力
- maintenance / decision / execution / provenance 协议
- 推荐工作流
- 稳定字段与已知边界

### 2. 协议文档
结构化协议定义见：

- `scripts/fokb_protocol.md`

适合对接：
- agent
- UI
- 自动化脚本

### 3. 脚本索引
脚本入口与分层说明见：

- `scripts/README.md`

### 4. 快速上手
初始化：

```bash
fokb init
fokb check
```

常用命令：

```bash
fokb stats
fokb maintenance --last
fokb decide --maintenance-path /absolute/path/to/object.md
fokb decide --maintenance-path /absolute/path/to/object.md --execute
fokb promote /absolute/path/to/sorted/object.md
fokb synthesize "quantum financing" --mode outline --title "Quantum Financing Outline"
fokb ingest "<url>"
```

### 5. 示例与发布记录

- `examples/README.md`
- `examples/decide-quantum-topic.json`
- `CHANGELOG.md`
- `LICENSE.md`

## 路径约定
`fokb` 默认把 `scripts/fokb.py` 的上级目录识别为项目根目录。

如果要在其他位置运行，可设置：

```bash
export FOKB_BASE=/path/to/LLM-Wiki-Cli
```

## 当前状态
当前版本已经具备：

- 稳定 envelope
- maintenance 协议
- step-based decision contract
- execution result contract
- provenance / history / state

因此，它已经可以作为第一版完整可用的 agent-facing 产品使用。

## 许可证说明

当前仓库已经公开，但许可证文本仍保持保守状态，尚未切换到最终开源授权。
在正式选定 MIT / Apache-2.0 / 其他许可证之前，请以 `LICENSE.md` 为准。
