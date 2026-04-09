# Auto Report

面向以下方向的定时情报采集与自动快报框架：

- AI / 大模型 / Agent
- AI × 电子信息

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
- 生成综合总报和两个领域快报
- 本地留档到 `data/`
- 预置 PushPlus 推送接口
- 预置 DeepSeek 分析接口
- 预留后续博客同步扩展点
