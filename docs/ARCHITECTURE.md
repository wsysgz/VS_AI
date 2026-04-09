# 架构说明

## 当前执行链路

当前 V1 的执行路径是：

`cli.py` -> `app.py` -> `settings.py` -> `sources/` -> `pipeline/` -> `outputs/` -> `integrations/` -> `data/`

## 当前分层

- `config/`
  放领域、来源、调度和供应商配置。
- `src/auto_report/models/`
  放内部统一数据结构。
- `src/auto_report/sources/`
  放 RSS、GitHub、网页列表等采集适配器。
- `src/auto_report/pipeline/`
  放去重、分类、评分、分析、执行主流程。
- `src/auto_report/domains/`
  放领域判定规则。
- `src/auto_report/outputs/`
  放 Markdown / JSON 渲染和归档写入。
- `src/auto_report/integrations/`
  放 PushPlus、DeepSeek，以及后续博客同步接口。

## 已预留的扩展点

- `src/auto_report/sources/`
  后续可继续增加更多 API、RSS、网页解析器。
- `src/auto_report/pipeline/`
  后续可继续增加 AI 评分、趋势比较、历史回看。
- `src/auto_report/integrations/`
  后续可增加博客同步、邮件推送、更多消息渠道。
