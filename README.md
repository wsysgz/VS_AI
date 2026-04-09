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
- 如果配置了 Telegram，也会同步发送同一份短摘要 + GitHub 详情链接
- 本地优先开发，确认通过后再推送到仓库自动运行

## 本地运行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m auto_report.cli run-once
```

## 当前能力

- 支持本地运行和 GitHub Actions 定时运行
- 支持推送到 `main` 后自动执行一次 GitHub Actions 验证和归档
- 生成综合总报和两个领域快报
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
- Telegram Bot：发送同一份短摘要 + GitHub 详情链接

为了避免工作流在提交 `data/` 归档后反复触发自己，`data/**` 已经被排除在 `push` 触发范围之外。
