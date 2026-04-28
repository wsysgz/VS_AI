from __future__ import annotations

import json
from html import escape
from pathlib import Path

from auto_report.settings import load_settings
from auto_report.source_registry import build_source_governance_queue, build_source_registry


def _load_source_governance_artifact(root_dir: Path) -> dict[str, object]:
    path = root_dir / "out" / "source-governance" / "source-governance.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _coerce_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_metric(value: object, *, signed: bool = False, suffix: str = "") -> str:
    number = _coerce_float(value)
    if number is None:
        return "-"
    if signed:
        return f"{number:+.2f}{suffix}"
    return f"{number:.2f}{suffix}"


def _format_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return _format_metric(value)
    if isinstance(value, list):
        if not value:
            return "-"
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        if not value:
            return "-"
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value)
    return text if text else "-"


def _status_badge(status: str) -> str:
    tone = {
        "ok": "ok",
        "error": "error",
        "skipped": "muted",
    }.get(status, "muted")
    return f'<span class="badge badge-{tone}">{escape(status)}</span>'


def _render_channels(delivery_results: dict[str, object]) -> str:
    channels = delivery_results.get("channels", {})
    if not isinstance(channels, dict) or not channels:
        return '<tr><td colspan="5" class="empty">No delivery data</td></tr>'

    rows: list[str] = []
    for name, raw_item in channels.items():
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(name))}</td>"
            f"<td>{_status_badge(str(item.get('status', 'unknown')))}</td>"
            f"<td>{escape(str(item.get('error_type') or '-'))}</td>"
            f"<td>{escape(str(item.get('attempted_at') or '-'))}</td>"
            f"<td>{escape(str(item.get('detail') or '-'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_key_values(data: dict[str, object]) -> str:
    if not data:
        return '<div class="kv empty">No data</div>'

    items: list[str] = []
    for key, value in data.items():
        items.append(
            f'<div class="kv"><span>{escape(str(key))}</span><strong>{escape(_format_value(value))}</strong></div>'
        )
    return "\n".join(items)


def _render_reason_list(reasons: list[object]) -> str:
    if not reasons:
        return '<div class="empty">No enrichment diagnostics</div>'

    items: list[str] = []
    for reason in reasons:
        items.append(f"<li>{escape(str(reason))}</li>")
    return f"<ul class=\"reason-list\">{''.join(items)}</ul>"


def _render_source_failures(source_health: dict[str, object]) -> str:
    sources = source_health.get("sources", {})
    if not isinstance(sources, dict) or not sources:
        return '<tr><td colspan="7" class="empty">No source failure breakdown</td></tr>'

    rows: list[str] = []
    for source_id, raw_item in sorted(sources.items()):
        item = raw_item if isinstance(raw_item, dict) else {}
        categories = item.get("error_categories", [])
        category_text = ", ".join(str(category) for category in categories) if isinstance(categories, list) and categories else "-"
        rows.append(
            "<tr>"
            f"<td>{escape(str(source_id))}</td>"
            f"<td>{escape(str(item.get('collector') or '-'))}</td>"
            f"<td>{escape(str(item.get('stability_tier') or '-'))}</td>"
            f"<td>{escape(str(item.get('failure_count') or 0))}</td>"
            f"<td>{escape(category_text)}</td>"
            f"<td>{escape(str(item.get('replacement_hint') or '-'))}</td>"
            f"<td>{escape(str(item.get('last_error') or '-'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_source_registry(source_registry: dict[str, object]) -> str:
    if not isinstance(source_registry, dict) or not source_registry:
        return '<tr><td colspan="9" class="empty">No source registry data</td></tr>'

    rows: list[str] = []
    for source_id, raw_item in sorted(
        source_registry.items(),
        key=lambda item: (not bool((item[1] if isinstance(item[1], dict) else {}).get("enabled", False)), str(item[0])),
    ):
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(source_id))}</td>"
            f"<td>{escape(str(item.get('collector') or '-'))}</td>"
            f"<td>{escape(_format_value(item.get('enabled')))}</td>"
            f"<td>{escape(str(item.get('mode') or '-'))}</td>"
            f"<td>{escape(str(item.get('stability_tier') or '-'))}</td>"
            f"<td>{escape(str(item.get('watch_strategy') or '-'))}</td>"
            f"<td>{escape(str(item.get('source_group') or '-'))}</td>"
            f"<td>{escape(str(item.get('replacement_target') or '-'))}</td>"
            f"<td>{escape(str(item.get('replacement_hint') or '-'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_manual_review_focus(items: list[object]) -> str:
    if not items:
        return '<tr><td colspan="6" class="empty">No manual-review sources</td></tr>'

    rows: list[str] = []
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('source_id') or '-'))}</td>"
            f"<td>{escape(_format_value(item.get('enabled')))}</td>"
            f"<td>{escape(str(item.get('stability_tier') or '-'))}</td>"
            f"<td>{escape(str(item.get('replacement_target') or '-'))}</td>"
            f"<td>{escape(str(item.get('replacement_hint') or '-'))}</td>"
            f"<td>{escape(str(item.get('url') or '-'))}</td>"
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="6" class="empty">No manual-review sources</td></tr>'
    return "\n".join(rows)


def _render_governance_candidates(items: list[object], empty_label: str) -> str:
    if not items:
        return f'<tr><td colspan="6" class="empty">{escape(empty_label)}</td></tr>'

    rows: list[str] = []
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('source_id') or '-'))}</td>"
            f"<td>{escape(str(item.get('collector') or '-'))}</td>"
            f"<td>{escape(_format_value(item.get('enabled')))}</td>"
            f"<td>{escape(str(item.get('replacement_target') or '-'))}</td>"
            f"<td>{escape(str(item.get('replacement_hint') or '-'))}</td>"
            f"<td>{escape(str(item.get('url') or '-'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_governance_priority_queue(items: list[object]) -> str:
    if not items:
        return '<tr><td colspan="7" class="empty">No governance priority items</td></tr>'

    rows: list[str] = []
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('source_id') or '-'))}</td>"
            f"<td>{escape(str(item.get('candidate_kind') or '-'))}</td>"
            f"<td>{escape(str(item.get('priority_label') or '-'))}</td>"
            f"<td>{escape(str(item.get('priority_score') or '-'))}</td>"
            f"<td>{escape(str(item.get('reason') or '-'))}</td>"
            f"<td>{escape(str(item.get('next_action') or '-'))}</td>"
            f"<td>{escape(str(item.get('url') or '-'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_changedetection_watch_registry(items: list[object]) -> str:
    if not items:
        return '<tr><td colspan="8" class="empty">No changedetection watch registry items</td></tr>'

    rows: list[str] = []
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('source_id') or '-'))}</td>"
            f"<td>{escape(str(item.get('status') or '-'))}</td>"
            f"<td>{escape(str(item.get('priority_label') or '-'))}</td>"
            f"<td>{escape(str(item.get('priority_score') or '-'))}</td>"
            f"<td>{escape(str(item.get('watch_target') or '-'))}</td>"
            f"<td>{escape(str(item.get('watch_reference') or '-'))}</td>"
            f"<td>{escape(str(item.get('next_action') or '-'))}</td>"
            f"<td>{escape(str(item.get('note') or '-'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_watch_run_results(items: list[object]) -> str:
    if not items:
        return '<tr><td colspan="5" class="empty">No local watch run results</td></tr>'

    rows: list[str] = []
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('source_id') or '-'))}</td>"
            f"<td>{escape(str(item.get('status') or '-'))}</td>"
            f"<td>{escape(str(item.get('checked_at') or '-'))}</td>"
            f"<td>{escape(str(item.get('new_item_count') or 0))}</td>"
            f"<td>{escape(_format_value(item.get('new_items') or []))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_discovery_leads(items: list[object], empty_label: str) -> str:
    if not items:
        return f'<tr><td colspan="7" class="empty">{escape(empty_label)}</td></tr>'

    rows: list[str] = []
    for raw_item in items:
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('keyword') or '-'))}</td>"
            f"<td>{escape(str(item.get('title') or '-'))}</td>"
            f"<td>{escape(str(item.get('classification') or '-'))}</td>"
            f"<td>{escape(str(item.get('confidence') or '-'))}</td>"
            f"<td>{escape(str(item.get('feed_candidate') or item.get('rsshub_candidate') or item.get('changedetection_candidate') or '-'))}</td>"
            f"<td>{escape(str(item.get('next_action') or '-'))}</td>"
            f"<td>{escape(str(item.get('url') or '-'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _flatten_mapping(data: dict[str, object], prefix: str = "") -> dict[str, object]:
    flattened: dict[str, object] = {}
    for key, value in data.items():
        label = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten_mapping(value, label))
        else:
            flattened[label] = value
    return flattened


def _dataset_label(payload: dict[str, object], fallback: str) -> str:
    dataset_meta = payload.get("dataset_meta", {})
    if isinstance(dataset_meta, dict):
        dataset_id = str(dataset_meta.get("dataset_id", "")).strip()
        version = str(dataset_meta.get("version", "")).strip()
        if dataset_id and version:
            return f"{dataset_id} ({version})"
        if dataset_id:
            return dataset_id
    return fallback


def _load_recent_prompt_evals(root_dir: Path, limit: int = 5) -> list[dict[str, object]]:
    eval_dir = root_dir / "out" / "evals"
    if not eval_dir.exists():
        return []

    runs: list[dict[str, object]] = []
    for path in sorted(eval_dir.glob("prompt-eval-*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue

        leaderboard_rows: list[dict[str, object]] = []
        raw_leaderboard = payload.get("leaderboard", [])
        if isinstance(raw_leaderboard, list):
            for raw_item in raw_leaderboard:
                if not isinstance(raw_item, dict):
                    continue
                metrics = raw_item.get("metrics", {})
                leaderboard_rows.append(
                    {
                        "stage": str(raw_item.get("stage", "-")),
                        "prompt_id": str(raw_item.get("prompt_id", "-")),
                        "version": str(raw_item.get("version", "-")),
                        "model": str(raw_item.get("model", "-")),
                        "overall_score_avg": _coerce_float(
                            metrics.get("overall_score_avg") if isinstance(metrics, dict) else None
                        ),
                    }
                )

        runs.append(
            {
                "generated_at": str(payload.get("generated_at", path.stem)),
                "dataset_path": str(payload.get("dataset_path", path.name)),
                "dataset_label": _dataset_label(payload, str(payload.get("dataset_path", path.name))),
                "summary": payload.get("summary", {}),
                "leaderboard": leaderboard_rows,
            }
        )

    runs.sort(key=lambda item: str(item.get("generated_at", "")), reverse=True)
    return runs[:limit]


def _build_prompt_regressions(prompt_eval_runs: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(prompt_eval_runs) < 2:
        return []

    latest = prompt_eval_runs[0]
    previous_lookup: dict[tuple[str, str, str], dict[str, object]] = {}
    for run in prompt_eval_runs[1:]:
        for entry in run.get("leaderboard", []):
            if not isinstance(entry, dict):
                continue
            key = (
                str(entry.get("stage", "-")),
                str(entry.get("prompt_id", "-")),
                str(entry.get("model", "-")),
            )
            previous_lookup.setdefault(key, entry)

    regressions: list[dict[str, object]] = []
    for entry in latest.get("leaderboard", []):
        if not isinstance(entry, dict):
            continue
        key = (
            str(entry.get("stage", "-")),
            str(entry.get("prompt_id", "-")),
            str(entry.get("model", "-")),
        )
        previous = previous_lookup.get(key)
        if previous is None:
            continue

        latest_score = _coerce_float(entry.get("overall_score_avg"))
        previous_score = _coerce_float(previous.get("overall_score_avg"))
        if latest_score is None or previous_score is None:
            continue

        regressions.append(
            {
                "stage": str(entry.get("stage", "-")),
                "prompt_id": str(entry.get("prompt_id", "-")),
                "latest_version": str(entry.get("version", "-")),
                "previous_version": str(previous.get("version", "-")),
                "model": str(entry.get("model", "-")),
                "latest_score": latest_score,
                "previous_score": previous_score,
                "delta": round(latest_score - previous_score, 2),
            }
        )

    regressions.sort(key=lambda item: float(item["delta"]))
    return regressions[:8]


def _render_prompt_eval_runs(prompt_eval_runs: list[dict[str, object]]) -> str:
    if not prompt_eval_runs:
        return '<tr><td colspan="6" class="empty">No prompt evaluation history</td></tr>'

    rows: list[str] = []
    for run in prompt_eval_runs:
        summary = run.get("summary", {})
        summary_dict = summary if isinstance(summary, dict) else {}
        leaderboard = run.get("leaderboard", [])
        top_entry = leaderboard[0] if isinstance(leaderboard, list) and leaderboard else {}
        rows.append(
            "<tr>"
            f"<td>{escape(str(run.get('generated_at', '-')))}</td>"
            f"<td>{escape(str(run.get('dataset_label', run.get('dataset_path', '-'))))}</td>"
            f"<td>{escape(str(summary_dict.get('case_count', '-')))}</td>"
            f"<td>{escape(str(summary_dict.get('evaluation_count', '-')))}</td>"
            f"<td>{escape(str(top_entry.get('prompt_id', '-')))} / {escape(str(top_entry.get('version', '-')))}</td>"
            f"<td>{_format_metric(top_entry.get('overall_score_avg'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_prompt_regressions(regressions: list[dict[str, object]]) -> str:
    if not regressions:
        return '<tr><td colspan="7" class="empty">No comparable prompt regression history</td></tr>'

    rows: list[str] = []
    for item in regressions:
        delta_class = "metric-negative" if float(item["delta"]) < 0 else "metric-positive"
        rows.append(
            "<tr>"
            f"<td>{escape(str(item['stage']))}</td>"
            f"<td>{escape(str(item['prompt_id']))}</td>"
            f"<td>{escape(str(item['latest_version']))}</td>"
            f"<td>{escape(str(item['previous_version']))}</td>"
            f"<td>{escape(str(item['model']))}</td>"
            f"<td>{_format_metric(item['latest_score'])}</td>"
            f'<td class="{delta_class}">{_format_metric(item["delta"], signed=True)}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def _build_dashboard_html(
    status: dict[str, object],
    prompt_eval_runs: list[dict[str, object]],
    source_registry: dict[str, object],
    source_governance: dict[str, object],
    changedetection_watch_registry: dict[str, object],
    watch_run_results: dict[str, object],
) -> str:
    delivery_results = status.get("delivery_results", {})
    scheduler = status.get("scheduler", {})
    source_stats = status.get("source_stats", {})
    timings = status.get("timings", {})
    stage_status = status.get("stage_status", {})
    ai_metrics = status.get("ai_metrics", {})
    source_health = status.get("source_health", {})
    review = status.get("review", {})
    external_enrichment = status.get("external_enrichment", {})
    official_feed_leads = status.get("official_feed_leads", [])
    rsshub_leads = status.get("rsshub_leads", [])
    changedetection_leads = status.get("changedetection_leads", [])
    source_governance_dict = source_governance if isinstance(source_governance, dict) else {}
    governance_summary = source_governance_dict.get("summary", {})
    watch_registry_dict = changedetection_watch_registry if isinstance(changedetection_watch_registry, dict) else {}
    watch_results_dict = watch_run_results if isinstance(watch_run_results, dict) else {}
    regressions = _build_prompt_regressions(prompt_eval_runs)

    successful = len(delivery_results.get("successful_channels", []))
    failed = len(delivery_results.get("failed_channels", []))
    skipped = len(delivery_results.get("skipped_channels", []))
    attempted = successful + failed
    delivery_rate = (successful / attempted * 100) if attempted else None
    latest_eval = prompt_eval_runs[0] if prompt_eval_runs else {}
    latest_eval_summary = latest_eval.get("summary", {}) if isinstance(latest_eval, dict) else {}
    external_dict = external_enrichment if isinstance(external_enrichment, dict) else {}
    ai_metrics_view = (
        _flatten_mapping(ai_metrics)
        if isinstance(ai_metrics, dict)
        else {}
    )
    source_health_view = (
        _flatten_mapping(source_health)
        if isinstance(source_health, dict)
        else {}
    )
    review_view = review if isinstance(review, dict) else {}
    external_view = {
        "enabled": "on" if bool(external_dict.get("enabled", False)) else "off",
        "max_signals": external_dict.get("max_signals", 0),
        "attempted": external_dict.get("attempted", 0),
        "succeeded": external_dict.get("succeeded", 0),
        "failed": external_dict.get("failed", 0),
        "skipped": external_dict.get("skipped", 0),
        "budget_used": external_dict.get("budget_used", 0),
        "success_rate": _format_metric(external_dict.get("success_rate")),
        "circuit": "open" if bool(external_dict.get("circuit_open", False)) else "closed",
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Operations Dashboard</title>
<style>
  :root {{
    --bg: #07111f;
    --panel: rgba(10, 24, 41, 0.82);
    --panel-strong: #11213a;
    --text: #e8eef5;
    --muted: #9db1c7;
    --line: rgba(157, 177, 199, 0.18);
    --accent: #79d0ff;
    --ok: #53d79c;
    --warn: #ffd36a;
    --error: #ff7d7d;
    --shadow: 0 24px 80px rgba(0, 0, 0, 0.26);
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    min-height: 100vh;
    color: var(--text);
    background:
      radial-gradient(circle at top left, rgba(121, 208, 255, 0.18), transparent 28%),
      radial-gradient(circle at top right, rgba(83, 215, 156, 0.14), transparent 24%),
      linear-gradient(180deg, #050b15 0%, var(--bg) 100%);
  }}
  main {{
    max-width: 1180px;
    margin: 0 auto;
    padding: 40px 20px 56px;
  }}
  .hero {{
    display: grid;
    gap: 18px;
    padding: 28px;
    border: 1px solid var(--line);
    border-radius: 24px;
    background: linear-gradient(145deg, rgba(17, 33, 58, 0.96), rgba(7, 17, 31, 0.92));
    box-shadow: var(--shadow);
  }}
  .eyebrow {{
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 12px;
  }}
  h1 {{
    margin: 0;
    font-size: clamp(32px, 6vw, 54px);
    line-height: 0.98;
  }}
  .summary {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
  }}
  .card {{
    padding: 18px;
    border-radius: 18px;
    border: 1px solid var(--line);
    background: var(--panel);
    backdrop-filter: blur(12px);
  }}
  .card span {{
    display: block;
    margin-bottom: 10px;
    color: var(--muted);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .card strong {{
    font-size: 30px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 18px;
    margin-top: 18px;
  }}
  .section-title {{
    margin: 0 0 14px;
    font-size: 19px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    overflow: hidden;
  }}
  th, td {{
    padding: 12px 10px;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
    text-align: left;
    font-size: 14px;
  }}
  th {{
    color: var(--muted);
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 0.08em;
  }}
  .badge {{
    display: inline-flex;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }}
  .badge-ok {{
    color: #052612;
    background: var(--ok);
  }}
  .badge-error {{
    color: #350707;
    background: var(--error);
  }}
  .badge-muted {{
    color: #122538;
    background: var(--warn);
  }}
  .kv {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid var(--line);
    font-size: 14px;
  }}
  .kv span {{
    color: var(--muted);
  }}
  .empty {{
    color: var(--muted);
  }}
  .footnote {{
    margin-top: 18px;
    color: var(--muted);
    font-size: 13px;
  }}
  .reason-list {{
    margin: 0;
    padding-left: 18px;
    color: var(--text);
    display: grid;
    gap: 8px;
  }}
  .reason-list li {{
    line-height: 1.45;
  }}
  .metric-negative {{
    color: var(--error);
    font-weight: 700;
  }}
  .metric-positive {{
    color: var(--ok);
    font-weight: 700;
  }}
  @media (max-width: 900px) {{
    .grid {{
      grid-template-columns: 1fr;
    }}
  }}
</style>
</head>
<body>
<main>
  <section class="hero">
    <div class="eyebrow">Private Ops View</div>
    <h1>Operations Dashboard</h1>
    <div class="footnote">Generated at {escape(str(status.get("generated_at", "-")))}</div>
    <div class="summary">
      <div class="card"><span>Push State</span><strong>{escape(str(status.get("pushed", False)))}</strong></div>
      <div class="card"><span>Success</span><strong>{successful}</strong></div>
      <div class="card"><span>Failed</span><strong>{failed}</strong></div>
      <div class="card"><span>Skipped</span><strong>{skipped}</strong></div>
      <div class="card"><span>Risk Level</span><strong>{escape(str(status.get("risk_level", "low")))}</strong></div>
      <div class="card"><span>Delivery Rate</span><strong>{_format_metric(delivery_rate, suffix="%")}</strong></div>
      <div class="card"><span>Prompt Eval Runs</span><strong>{len(prompt_eval_runs)}</strong></div>
      <div class="card"><span>Latest Eval Cases</span><strong>{escape(str(latest_eval_summary.get("case_count", "-")))}</strong></div>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Delivery Channels</h2>
      <table>
        <thead>
          <tr>
            <th>Channel</th>
            <th>Status</th>
            <th>Error Type</th>
            <th>Attempted At</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          {_render_channels(delivery_results if isinstance(delivery_results, dict) else {})}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2 class="section-title">Scheduler</h2>
      {_render_key_values(scheduler if isinstance(scheduler, dict) else {})}
      <h2 class="section-title" style="margin-top: 22px;">Stage Status</h2>
      {_render_key_values(stage_status if isinstance(stage_status, dict) else {})}
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Source Stats</h2>
      {_render_key_values(source_stats if isinstance(source_stats, dict) else {})}
    </div>
    <div class="card">
      <h2 class="section-title">Timings</h2>
      {_render_key_values(timings if isinstance(timings, dict) else {})}
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">AI Metrics</h2>
      {_render_key_values(ai_metrics_view)}
    </div>
    <div class="card">
      <h2 class="section-title">Source Health</h2>
      {_render_key_values(source_health_view)}
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Source Failure Breakdown</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Collector</th>
            <th>Tier</th>
            <th>Failures</th>
            <th>Categories</th>
            <th>Replacement Hint</th>
            <th>Last Error</th>
          </tr>
        </thead>
        <tbody>
          {_render_source_failures(source_health if isinstance(source_health, dict) else {})}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Source Registry</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Collector</th>
            <th>Enabled</th>
            <th>Mode</th>
            <th>Tier</th>
            <th>Watch Strategy</th>
            <th>Group</th>
            <th>Replacement Target</th>
            <th>Replacement Hint</th>
          </tr>
        </thead>
        <tbody>
          {_render_source_registry(source_registry)}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Source Governance Queue</h2>
      {_render_key_values(governance_summary if isinstance(governance_summary, dict) else {})}
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Governance Priority Queue</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Candidate Kind</th>
            <th>Priority</th>
            <th>Score</th>
            <th>Reason</th>
            <th>Next Action</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_governance_priority_queue(
              source_governance_dict.get("priority_queue", [])
              if isinstance(source_governance_dict, dict)
              else []
          )}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Local Watch Registry</h2>
      {_render_key_values(watch_registry_dict.get("summary", {}) if isinstance(watch_registry_dict.get("summary", {}), dict) else {})}
      <table style="margin-top: 16px;">
        <thead>
          <tr>
            <th>Source</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Score</th>
            <th>Watch Target</th>
            <th>Watch Reference</th>
            <th>Next Action</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {_render_changedetection_watch_registry(
              watch_registry_dict.get("items", []) if isinstance(watch_registry_dict, dict) else []
          )}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Local Watch Run Results</h2>
      {_render_key_values(watch_results_dict.get("summary", {}) if isinstance(watch_results_dict.get("summary", {}), dict) else {})}
      <table style="margin-top: 16px;">
        <thead>
          <tr>
            <th>Source</th>
            <th>Status</th>
            <th>Checked At</th>
            <th>New Items</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {_render_watch_run_results(
              watch_results_dict.get("items", []) if isinstance(watch_results_dict, dict) else []
          )}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Discovery Leads</h2>
      <table>
        <thead>
          <tr>
            <th>Keyword</th>
            <th>Title</th>
            <th>Classification</th>
            <th>Confidence</th>
            <th>Candidate</th>
            <th>Next Action</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_discovery_leads(
              official_feed_leads if isinstance(official_feed_leads, list) else [],
              "No discovery leads",
          )}
        </tbody>
      </table>
      <h2 class="section-title" style="margin-top: 22px;">Official Feed Leads</h2>
      <table>
        <thead>
          <tr>
            <th>Keyword</th>
            <th>Title</th>
            <th>Classification</th>
            <th>Confidence</th>
            <th>Candidate</th>
            <th>Next Action</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_discovery_leads(
              official_feed_leads if isinstance(official_feed_leads, list) else [],
              "No official feed leads",
          )}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2 class="section-title">RSSHub Leads</h2>
      <table>
        <thead>
          <tr>
            <th>Keyword</th>
            <th>Title</th>
            <th>Classification</th>
            <th>Confidence</th>
            <th>Candidate</th>
            <th>Next Action</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_discovery_leads(
              rsshub_leads if isinstance(rsshub_leads, list) else [],
              "No RSSHub leads",
          )}
        </tbody>
      </table>

      <h2 class="section-title" style="margin-top: 22px;">changedetection Leads</h2>
      <table>
        <thead>
          <tr>
            <th>Keyword</th>
            <th>Title</th>
            <th>Classification</th>
            <th>Confidence</th>
            <th>Candidate</th>
            <th>Next Action</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_discovery_leads(
              changedetection_leads if isinstance(changedetection_leads, list) else [],
              "No changedetection leads",
          )}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Manual Review Focus</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Enabled</th>
            <th>Tier</th>
            <th>Replacement Target</th>
            <th>Replacement Hint</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_manual_review_focus(
              source_governance_dict.get("manual_review", [])
              if isinstance(source_governance_dict, dict)
              else []
          )}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">RSSHub Candidates</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Collector</th>
            <th>Enabled</th>
            <th>Replacement Target</th>
            <th>Replacement Hint</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_governance_candidates(
              source_governance_dict.get("rsshub_candidates", [])
              if isinstance(source_governance_dict, dict)
              else [],
              "No RSSHub candidates",
          )}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2 class="section-title">changedetection Candidates</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Collector</th>
            <th>Enabled</th>
            <th>Replacement Target</th>
            <th>Replacement Hint</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_governance_candidates(
              source_governance_dict.get("changedetection_candidates", [])
              if isinstance(source_governance_dict, dict)
              else [],
              "No changedetection candidates",
          )}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Replacement Candidates</h2>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Collector</th>
            <th>Enabled</th>
            <th>Replacement Target</th>
            <th>Replacement Hint</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {_render_governance_candidates(
              source_governance_dict.get("replacement_candidates", [])
              if isinstance(source_governance_dict, dict)
              else [],
              "No replacement candidates",
          )}
        </tbody>
      </table>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Review Metadata</h2>
      {_render_key_values(review_view)}
    </div>
    <div class="card">
      <h2 class="section-title">External Enrichment</h2>
      {_render_key_values(external_view)}
    </div>
    <div class="card">
      <h2 class="section-title">Enrichment Reasons</h2>
      {_render_reason_list(
          external_dict.get("reasons", [])
          if isinstance(external_dict, dict)
          else []
      )}
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <h2 class="section-title">Prompt Evaluation Trend</h2>
      <table>
        <thead>
          <tr>
            <th>Generated At</th>
            <th>Dataset</th>
            <th>Cases</th>
            <th>Evaluations</th>
            <th>Top Prompt</th>
            <th>Top Score</th>
          </tr>
        </thead>
        <tbody>
          {_render_prompt_eval_runs(prompt_eval_runs)}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2 class="section-title">Prompt Regression Watch</h2>
      <table>
        <thead>
          <tr>
            <th>Stage</th>
            <th>Prompt</th>
            <th>Latest Version</th>
            <th>Previous Version</th>
            <th>Model</th>
            <th>Latest Score</th>
            <th>Delta</th>
          </tr>
        </thead>
        <tbody>
          {_render_prompt_regressions(regressions)}
        </tbody>
      </table>
    </div>
  </section>
</main>
</body>
</html>"""


def build_ops_dashboard(root_dir: Path) -> Path:
    status_path = root_dir / "data" / "state" / "run-status.json"
    if not status_path.exists():
        raise FileNotFoundError(f"Run status not found: {status_path}")

    status = json.loads(status_path.read_text(encoding="utf-8"))
    prompt_eval_runs = _load_recent_prompt_evals(root_dir)
    source_registry = status.get("source_registry", {})
    if not isinstance(source_registry, dict) or not source_registry:
        source_registry = {}
    source_governance = status.get("source_governance", {})
    if not isinstance(source_governance, dict) or not source_governance:
        source_governance = {}
    changedetection_watch_registry = status.get("changedetection_watch_registry", {})
    if not isinstance(changedetection_watch_registry, dict) or not changedetection_watch_registry:
        changedetection_watch_registry = {}
    source_governance_artifact = _load_source_governance_artifact(root_dir)
    artifact_source_registry = source_governance_artifact.get("source_registry", {})
    if isinstance(artifact_source_registry, dict) and artifact_source_registry:
        source_registry = artifact_source_registry
    artifact_source_governance = source_governance_artifact.get("source_governance", {})
    if isinstance(artifact_source_governance, dict) and artifact_source_governance:
        source_governance = artifact_source_governance
    artifact_watch_registry = source_governance_artifact.get("changedetection_watch_registry", {})
    if isinstance(artifact_watch_registry, dict) and artifact_watch_registry:
        changedetection_watch_registry = artifact_watch_registry
    watch_run_results = status.get("watch_run_results", {})
    if not isinstance(watch_run_results, dict) or not watch_run_results:
        watch_run_results = {}
    config_dir = root_dir / "config"
    if not source_registry and config_dir.exists():
        source_registry = build_source_registry(load_settings(root_dir))
    if not source_governance and source_registry:
        source_governance = build_source_governance_queue(source_registry)
    if not changedetection_watch_registry:
        registry_path = root_dir / "out" / "source-governance" / "changedetection-watch-registry.json"
        if registry_path.exists():
            try:
                changedetection_watch_registry = json.loads(registry_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                changedetection_watch_registry = {}
    if not watch_run_results:
        watch_results_path = root_dir / "out" / "source-governance" / "watch-run-results.json"
        if watch_results_path.exists():
            try:
                watch_run_results = json.loads(watch_results_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                watch_run_results = {}
    output_dir = root_dir / "out" / "ops-dashboard"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(
        _build_dashboard_html(status, prompt_eval_runs, source_registry, source_governance, changedetection_watch_registry, watch_run_results),
        encoding="utf-8",
    )
    print(f"[OpsDashboard] Built at {output_path}")
    return output_path
