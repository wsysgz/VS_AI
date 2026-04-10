# VS_AI 接手手册

> **最后更新**: 2026-04-11
> **当前版本**: V6 (Phase 0~4 已完成, Phase 5 待定)
> **测试状态**: 91 passed, 0 failed

---

## 一句话说明

这是一个 **AI 情报自动采集 → 去重分类评分 → AI 三阶段分析(分析/总结/预测) → 多通道推送** 的每日定时系统。

---

## 快速启动（3 步到位）

### 1. 环境准备

```powershell
# 进入项目目录
cd D:\AI\workbuddy\auto\auto

# 创建虚拟环境（如果没有）
python -m venv .venv
.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
pip install -e .

# 复制环境变量模板（首次需要）
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

### 2. 配置 `.env` 必填项

| 变量 | 说明 | 是否必须 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | ✅ AI 分析必需 |
| `GITHUB_TOKEN` | GitHub PAT（用于 GitHub 源采集） | 推荐 |
| `PUSHPLUS_TOKEN` | PushPlus 推送 token | 可选 |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram 推送 | 可选 |
| `AI_MAX_ANALYSIS_TOPICS` | 每轮 AI 分析的最大主题数，默认 6 | 可选 |

> ⚠️ **绝对不要**把真实 token 写入仓库或提交到 git。

### 3. 验证运行

```powershell
# 设置模块搜索路径
$env:PYTHONPATH = "src"

# 运行测试（预期 91 passed）
python -m pytest tests -q

# 运行一次完整流程
python -m auto_report.cli run-once

# 检查输出
cat data/reports/latest-summary.md
cat data/state/run-status.json
```

---

## 项目架构

### 目录结构

```
auto/                          # Git 仓库根目录
├── .github/workflows/
│   └── collect-report.yml     # CI/CD: 5 个 job（test → collect → analyze → report → deploy-pages）
├── config/
│   ├── sources/               # 数据源配置（RSS/GitHub/HN/Website）
│   │   ├── github.yaml        # GitHub 仓库组配置
│   │   ├── rss.yaml           # RSS 订阅源配置
│   │   ├── hacker_news.yaml   # HN 热门故事配置
│   │   └── websites.yaml      # 网站爬取源配置
│   ├── domains.yaml           # 领域定义（ai-llm-agent / ai-x-electronics）
│   └── ai_reading/            # AI 三阶段提示词前缀文件
│       ├── analysis-before.md
│       ├── summary-before.md
│       └── forecast-before.md
├── src/auto_report/
│   ├── cli.py                 # CLI 入口（7 个子命令）
│   ├── app.py                 # 核心编排：StageTimer + run_once/render_reports/run_backfill + CI 三子命令
│   ├── settings.py            # Settings 数据类 + 环境变量加载
│   ├── pipeline/              # 核心处理管线
│   │   ├── analysis.py        # build_report_package() = dedup→classify→score→topic→AI 全流程
│   │   ├── ai_pipeline.py     # run_staged_ai_pipeline() = Analysis→Summary→Forecast
│   │   ├── run_once.py        # _to_relative_paths() + build_run_status() 增强
│   │   ├── dedup.py           # 去重（基于 URL+标题相似度）
│   │   ├── scoring.py         # 主题评分
│   │   ├── topic_builder.py   # TopicCandidate 构建
│   │   └── prompt_loader.py   # AI 提示词加载
│   ├── sources/               # 数据源采集层
│   │   ├── collector.py       # collect_all_items() — 四大类并发采集
│   │   ├── rss.py             # RSS 解析
│   │   ├── github.py          # GitHub API（仓库趋势/ releases）
│   │   ├── hn.py              # Hacker News Top Stories
│   │   └── websites.py        # 网站列表页爬取
│   ├── integrations/          # 外部服务集成
│   │   ├── llm_client.py      # 统一 LLM 客户端（DeepSeek/OpenAI 兼容）
│   │   ├── pushplus.py        # PushPlus 推送
│   │   ├── telegram.py        # Telegram Bot 推送
│   │   └── feishu.py          # 飞书机器人推送
│   ├── outputs/               # 输出渲染
│   │   ├── renderers.py       # MD / JSON / HTML 渲染器
│   │   └── archive.py         # 归档写入
│   ├── domains/               # 领域分类器
│   └── models/                # 数据模型（TopicCandidate / CollectedItem 等）
├── tests/                     # 测试套件（91 个用例）
│   ├── test_observability.py  # Phase 4: StageTimer / 路径转换 / status 增强（12 个）
│   ├── test_cli_smoke.py      # CLI 冒烟测试
│   ├── test_run_once.py       # 核心流程测试
│   ├── test_sources.py        # 数据源测试
│   └── ...
├── data/                      # 运行数据（由 CI 自动提交，本地 gitignore 不强制排除）
│   ├── reports/               # 最新报告（latest-*.md/json/html）
│   ├── state/                 # 运行状态（run-status.json / dedup-index.json）
│   └── archives/              # 历史归档（按日期目录）
├── docs/
│   ├── upgrade-plan-v6/       # V6 升级完整计划文档
│   └── index.html             # Pages 站点入口
├── AGENTS.md                  # AI 接手速查表
├── README.md                  # 项目说明
├── pyproject.toml             # Python 包配置
└── requirements.txt           # 依赖清单
```

### 数据流总览

```
CLI 子命令                    数据流向
═════════                   ═══════════════════════════════════════

run-once（本地一体）:
  collect_all_items() ──→ items[]
       ↓
  build_report_package() ──→ package (dedup→classify→score→AI三阶段)
       ↓
  render_reports() ──→ MD + JSON + HTML (+ timings)
       ↓
  三通道推送 (PushPlus / Telegram / 飞书)
       ↓
  write run-status.json (含 timings + relative paths)

CI 五 Job 模式:
  [test]          ← pytest 并行，不阻塞
      ↓
  [collect]       ← collect-only → intermediate.json → artifact
      ↓
  [analyze]       ← analyze-only → analysis-result.json → artifact
      ↓
  [report]        ← render-and-push → 推送 + git-auto-commit
      ↓
  [deploy-pages]  ← build-pages → docs/ → git push Pages
```

### CLI 子命令一览

| 命令 | 用途 | 使用场景 |
|------|------|----------|
| `run-once` | 完整流程：采集→分析→渲染→推送 | 本地开发/调试 |
| `backfill` | 补报指定日期 | 手动补历史 |
| `collect-only` | 仅采集+预处理→存中间结果 | CI Job 1 |
| `analyze-only` | 加载中间结果→AI 分析 | CI Job 2 |
| `render-and-push` | 渲染+推送+归档 | CI Job 3 |
| `build-pages` | 构建 GitHub Pages 站点 | CI Job 4 |
| `render-report` | 仅渲染不推送 | 调试用 |

---

## V6 升级完成情况

| Phase | 内容 | 状态 | 关键产出 |
|-------|------|------|----------|
| **0** | 工程加固 & CI 重构 | ✅ | 3-job→5-job 拆分, 采集并发化, timeout=60min 安全 |
| **1** | AI Pipeline 性能优化 | ✅ | Analysis 5路并行, LLM客户端抽象, retry+连接池 |
| **2** | GitHub Pages 在线快报 | ✅ | docs/index.html + 历史归档导航 |
| **3** | 能力增强 | ✅ | HN数据源, Arxiv RSS, 多模型LLM, 新GitHub仓库组 |
| **4** | 可观测性 & 运维 | ✅ | StageTimer全面覆盖, test job + junitxml, 91个测试 |
| **5** | 进阶功能(MCP/邮件/双语) | ⏭️ | 暂不实施 |

---

## 关键设计决策（接手必读）

### 1. StageTimer 计时系统

- `app.py` 中定义了 `StageTimer` 上下文管理器
- `render_reports()` 返回值从 `list[str]` 改为 **`tuple[list[str], dict[str, float]]`**
  - 第一个元素：生成的文件路径列表
  - 第二个元素：各阶段计时字典 `{collection, dedup_score, rendering}`
- `run_once()` 和 `run_backfill()` 都会写入 `timings` 到 `run-status.json`
- `run-status.json` 中 `generated_files` 字段是**相对路径**（通过 `_to_relative_paths()` 转换）

### 2. AI 调用不要在外部重复！

`build_report_package()` 内部已经包含了完整的 AI 三阶段管线。
**错误做法**：在 `render_reports()` 或 `run_backfill()` 中再调一次 `run_staged_ai_pipeline()`
**正确做法**：直接使用 `build_report_package()` 的返回值，AI 耗时包含在 `dedup_score` 计时中

### 3. LLM 客户端已抽象为统一接口

- `integrations/llm_client.py` 提供 `call_llm()` 统一函数
- 支持 DeepSeek 和 OpenAI 兼容 API（通过 `AI_PROVIDER` / `OPENAI_API_KEY` 切换）
- `ai_pipeline.py` 中 import 已从旧版 `deepseek.summarize_with_deepseek` 改为新版 `llm_client.call_llm`

### 4. Windows 路径处理坑

- `_to_relative_paths()` 内部做了正斜杠统一：`.replace("\\", "/")`
- 所有路径比较必须先 normalize 再 `startswith`，否则 Windows 下反斜杠会导致匹配失败

### 5. 数据源扩展方法

1. 在 `config/sources/` 下添加 YAML 配置
2. 在 `src/auto_report/sources/` 下添加采集函数
3. 在 `collector.py` 的 `collect_all_items()` 中注册新采集器
4. 更新 `ThreadPoolExecutor(max_workers=N)` 的 N 值

---

## 常见操作

### 本地调试

```powershell
$env:PYTHONPATH = "src"

# 只跑采集（不看 AI 输出）
python -m auto_report.cli collect-only

# 跳过采集，用已有中间结果跑 AI
python -m auto_report.cli analyze-only

# 只渲染不推送
python -m auto_report.cli render-report

# 完整跑一次
python -m auto_report.cli run-once
```

### 推送到远程

```powershell
git add src/ tests/ config/ .github/ docs/ AGENTS.md README.md pyproject.toml requirements.txt
git commit -m "feat: 描述改动内容"
git push origin main
# 注意：data/ 目录由 CI 自动提交，一般不需要手动 add
```

### CI 手动触发

```bash
gh workflow run collect-report.yml
# 或带推送：
gh workflow run collect-report.yml -f push_enabled=true
```

### 查看 CI 运行状态

```bash
gh run list --repo wsysgz/VS_AI --limit 5
gh run view --repo wsysgz/VS_AI --log-failed
```

---

## 环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | *(空)* | DeepSeek API 密钥 |
| `OPENAI_API_KEY` | *(空)* | OpenAI 兼容 API 密钥 |
| `AI_PROVIDER` | `deepseek` | LLM 提供商：`deepseek` 或 `openai` |
| `AI_MODEL` | `deepseek-chat` | 模型名称 |
| `AI_TEMPERATURE` | `0.2` | AI 生成温度 |
| `AI_MAX_ANALYSIS_TOPICS` | `6` | 每轮最大 AI 分析主题数 |
| `GITHUB_TOKEN` | *(空)* | GitHub API Token（源采集用） |
| `PUSHPLUS_TOKEN` | *(空)* | PushPlus 推送 Token |
| `PUSHPLUS_CHANNEL` | `clawbot` | PushPlus 通道 |
| `TELEGRAM_BOT_TOKEN` | *(空)* | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | *(空)* | Telegram Chat ID |
| `FEISHU_APP_ID` | *(空)* | 飞书 App ID |
| `FEISHU_APP_SECRET` | *(空)* | 飞书 App Secret |
| `FEISHU_CHAT_ID` | *(空)* | 飞书 Chat ID |
| `AUTO_PUSH_ENABLED` | `true` | 是否启用自动推送 |
| `AUTO_TIMEZONE` | `Asia/Shanghai` | 时区 |
| `REPORT_REPO_URL` | `https://github.com/wsysgz/VS_AI` | 报告详情链接前缀 |

---

## 测试指南

```powershell
$env:PYTHONPATH = "src"

# 全量测试（预期 91 passed）
python -m pytest tests -q

# 只跑可观测性相关测试
python -m pytest tests/test_observability -v

# 只跑冒烟测试
python -m pytest tests/test_cli_smoke -v

# 带覆盖率
python -m pytest tests --cov=src/auto_report --cov-report=term-missing
```

测试文件分布：

| 文件 | 用例数 | 覆盖范围 |
|------|--------|----------|
| `test_observability.py` | 12 | Phase 4: StageTimer, _to_relative_paths, build_run_status |
| `test_cli_smoke.py` | 2 | CLI 子命令存在性 + argparse 解析 |
| `test_run_once.py` | ~15 | 核心流程端到端 |
| `test_sources.py` | ~40+ | RSS/GitHub/HN/Website 各数据源 |
| 其他 | ~22 | dedup/scoring/classifier/renderer 等 |

---

## 下一步可做（但当前不做）

按优先级排列，供后续迭代参考：

1. **MCP Server** — 暴露标准接口给 Claude/GPT 等工具调用管线
2. **邮件订阅 (SMTP)** — 自建 Newsletter 系统
3. **双语报告** — 中英双语版本
4. **知识增强** — 对高分信号网络搜索补充上下文
5. **周报/月报** — 从日报扩展到更长周期报告

详见 `docs/upgrade-plan-v6/升级计划_V6_全面增强方案.md` 的 Phase 5 章节。

---

*本手册面向 AI 编程助手和开发者接手维护。如有疑问优先阅读 AGENTS.md 和 README.md。*
