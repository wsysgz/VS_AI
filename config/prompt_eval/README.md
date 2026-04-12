# Prompt Eval Assets

本目录保存仓库内正式管理的离线 Prompt/Eval 资产。

## 当前基线

- 数据集：`config/prompt_eval/baseline-v1.json`
- Prompt registry：`config/ai_reading/registry.json`
- 覆盖阶段：`summary`、`forecast`、`domain_briefs`

## 运行方式

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
```

## 维护约定

- `meta.dataset_id` 使用稳定标识，例如 `baseline-v1`
- `meta.version` 记录样例集版本日期
- `outputs[].prompt_id` 必须与 `config/ai_reading/registry.json` 中的正式 prompt id 对齐
- 新增样例时优先覆盖结构字段完整性、关键术语召回和可操作性，而不是追求大而全
