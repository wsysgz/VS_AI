# 技术指导手册

## 项目定位

这是一个“本地优先 + GitHub 可部署”的定时情报采集与自动快报框架，目标是让后续 AI 或开发者可以在这个基础上持续扩展，而不是每次重搭。

当前主仓库是 `https://github.com/wsysgz/VS_AI`，默认本地工作目录是 `D:\GitHub\auto`。

## 给后续 AI / 开发者的规则

- 先改 `config/sources/*.yaml`，再决定是否需要改采集代码。
- 领域规则尽量放在 `src/auto_report/domains/`，不要散落到各处。
- 归档输出统一留在 `src/auto_report/outputs/`。
- 推送和模型供应商适配器统一放在 `src/auto_report/integrations/`。
- 博客同步必须保持“可选扩展”，不要反向耦合进 `run-once`。
- GitHub Actions 主工作流是 `.github/workflows/collect-report.yml`，当前支持 `push + workflow_dispatch + schedule` 三种触发。
- 官方用户通知目前只保留北京时间 `07:00` 的综合总报。
- `push` 和 `workflow_dispatch` 触发默认用于验证与归档，默认 `AUTO_PUSH_ENABLED=false`。
- `workflow_dispatch` 可通过输入参数显式打开推送，用于仓库侧受控验证。
- PushPlus 当前优先走 `clawbot` 渠道；如果后续要回退到其他渠道，必须显式配置，不要做静默回退。
- `collect-report.yml` 已对 `data/**` 使用 `paths-ignore`，后续如果继续扩展自动提交范围，必须先检查是否会造成工作流自触发回环。

## 当前主要命令

```powershell
python -m auto_report.cli run-once
python -m auto_report.cli render-report
```

## 当前最安全的扩展顺序

1. 增加周报
2. 增加月报
3. 继续补真实 RSS / API / 页面采集器
4. 给 GitHub 源增加更细的查询策略
5. 把 DeepSeek 真正用于候选主题摘要和趋势整理
6. 扩充 `run-status.json` 与 `dedup-index.json`
7. 优化版面和阅读体验
8. 增加博客同步接口桩

## 当前已知限制

- 真实来源已经接入，但还属于第一批基础适配器
- `backfill` 还不是完整历史回放引擎
- 当前预测与分析仍以规则摘要为底，DeepSeek 是增强层，不是唯一依赖
