# VS_AI

AI 情报采集与分析系统。

主仓库：`https://github.com/wsysgz/VS_AI`

默认本地工作目录：`D:\GitHub\auto`

当前已经落地为一个面向以下方向的定时情报采集与自动快报框架：

- AI / 大模型 / Agent
- AI × 电子信息

当前默认运行模型：

- 每天北京时间 `07:00` 自动生成并推送 `1` 条综合总报
- `push` 到 `main` 会自动触发 GitHub Actions 做验证和归档，但默认不发微信消息
- PushPlus 当前优先尝试 `ClawBot`，并使用 `txt` 短摘要 + GitHub 详情链接
- 如果配置了 Telegram，会同步发送“完整报告正文 + GitHub 详情链接”，并自动按长度分段
- 本地优先开发，确认通过后再推送到仓库自动运行
- 当前第一轮升级后的主流程是：
  - `精选采集 -> 去噪过滤 -> 主题归并 -> 分析 -> 总结 -> 预测 -> 微信/Telegram 渲染 -> 归档/推送`
- 三份 AI 底层逻辑文件现在内置在仓库：
  - `config/ai_reading/analysis-before.md`
  - `config/ai_reading/summary-before.md`
  - `config/ai_reading/forecast-before.md`

## 快速接管

推荐把这个仓库当作一个“本地先验证，再交给 GitHub 自动运行”的长期项目来维护。

- 主本地目录：`D:\GitHub\auto`
- 主远端仓库：`git@github.com:wsysgz/VS_AI.git`
- SSH 连通性验证：`ssh -T git@github.com`
- `ssh-blog` 对应本机 `C:\Users\24160\.ssh\id_ed25519.pub`，指纹：`SHA256:5PsPPHvqPDYP7X15wLGZlQakseS8wmWYYqIYisx1Ixg`
- 也可以直接验证：`ssh -T ssh-blog`
- GitHub CLI：`C:\Program Files\GitHub CLI\gh.exe`
- GitHub CLI 登录状态检查：`& 'C:\Program Files\GitHub CLI\gh.exe' auth status`
- 推荐验证顺序：
  - `python -m pytest -q`
  - `python -m auto_report.cli run-once`
  - 确认 `data/reports/latest-summary.md` 与推送内容
  - 再推送到 `main`
- 阶段性交接入口：
  - `docs/superpowers/status/2026-04-10-stage1-handoff.md`

仓库根目录已经补充了 `AGENTS.md`，后续 AI / 开发者接手时优先读取它，可以更快恢复上下文。
当前 PAT 已接入本机 `gh auth` 的本地凭据存储，仓库文档不会保存 PAT 明文。

## 本地运行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m auto_report.cli run-once
```

本地运行前建议先准备 `.env`：

- 把 `.env.example` 复制为 `.env`
- 把真实 `DEEPSEEK_API_KEY` 只写入本地 `.env` 或 GitHub Actions Secrets，不要写进仓库 Markdown 或提交进 git
- 默认 `AI_MAX_ANALYSIS_TOPICS=6`，表示每轮只对优先级最高的 `6` 个主题走真实 AI 分析，兼顾质量、成本和耗时

## 当前能力

- 支持本地运行和 GitHub Actions 定时运行
- 支持推送到 `main` 后自动执行一次 GitHub Actions 验证和归档
- 生成综合总报和两个领域快报
- 在运行时读取仓库内置的分析 / 总结 / 预测前阅读文件
- 通过 staged AI 管线生成结构化分析、总结和预测
- 本地留档到 `data/`
- 预置 PushPlus 推送接口
- 预置 Telegram Bot 推送接口
- 预置 DeepSeek 分析接口
- 预留后续博客同步扩展点
- 预留后续周报、月报、更多信息源、更强分析、版面优化扩展点

## GitHub 自动运行说明

`Collect And Report` 现在支持三种触发方式：

- 手动触发 `workflow_dispatch`
- 定时触发 `schedule`
- 推送到 `main` 后自动触发 `push`

其中：

- `schedule` 是正式用户通知通道，每天北京时间 `07:00` 发送综合总报
- `push` 默认用于验证与归档，不主动打扰微信
- `workflow_dispatch` 默认不推送，但可以在手动运行时显式打开推送

可选消息通道：

- PushPlus ClawBot：发送 `txt` 短摘要 + GitHub 详情链接
- Telegram Bot：发送完整报告正文，并自动切分为 `<=4096` 字符的多条纯文本消息，末尾附 GitHub 详情链接

当前自动化约束：

- 每天正式自动推送只有 `1` 次
- GitHub Actions 主任务 `timeout-minutes: 25`
- 因此日常自动运行时间被限制在 `60` 分钟以内

为了避免工作流在提交 `data/` 归档后反复触发自己，`data/**` 已经被排除在 `push` 触发范围之外。
