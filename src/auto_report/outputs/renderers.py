from __future__ import annotations

import html as html_module
import json

from auto_report.pipeline.briefing import compose_executive_brief


def _escape(text: str) -> str:
    return html_module.escape(str(text))


def _html_attrs(attrs: dict[str, str]) -> str:
    return " ".join(f'{k}="{v}"' for k, v in attrs.items())


def _review_lines(payload: dict[str, object]) -> list[str]:
    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        return []
    publication_mode = str(meta.get("publication_mode", "")).strip().lower()
    if publication_mode != "reviewed":
        return []
    review = meta.get("review", {})
    if not isinstance(review, dict):
        review = {}
    reviewer = str(review.get("reviewer", "")).strip() or "未填写"
    review_note = str(review.get("review_note", "")).strip() or "未填写"
    return [
        "复核信息",
        f"- 审核人：{reviewer}",
        f"- 备注：{review_note}",
    ]


def _link_lines(public_site_url: str, raw_report_url: str) -> list[str]:
    return [
        "公开阅读：",
        public_site_url,
        "GitHub 原文：",
        raw_report_url,
    ]


def _comparison_highlight_lines(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        track = str(item.get("tech_track", "")).strip()
        source_ids = item.get("source_ids", [])
        source_text = ""
        if isinstance(source_ids, list) and source_ids:
            source_text = f"（来源：{', '.join(str(source_id) for source_id in source_ids[:3])}）"
        lines.append(f"- {track}：{title}{source_text}" if track else f"- {title}{source_text}")
    return lines


def _comparison_markdown_lines(brief: dict[str, object]) -> list[str]:
    comparison = brief.get("comparison_brief", {})
    if not isinstance(comparison, dict):
        comparison = {}
    head_to_head = "\n".join(
        f"- {item.get('readout')}"
        for item in comparison.get("head_to_head", [])
        if isinstance(item, dict) and str(item.get("readout", "")).strip()
    ) or "- 暂无"
    gaps = "\n".join(f"- {item}" for item in comparison.get("gaps", []) if str(item).strip()) or "- 暂无"
    watchpoints = "\n".join(f"- {item}" for item in comparison.get("watchpoints", []) if str(item).strip()) or "- 暂无"
    return [
        "## 国内外对比",
        "### 国内高亮信号",
        "\n".join(_comparison_highlight_lines(comparison.get("cn_highlights", []))) or "- 暂无",
        "",
        "### 海外高亮信号",
        "\n".join(_comparison_highlight_lines(comparison.get("intl_highlights", []))) or "- 暂无",
        "",
        "### 同轨对照",
        head_to_head,
        "",
        "### 覆盖缺口",
        gaps,
        "",
        "### 观察点",
        watchpoints,
    ]


def _comparison_delivery_lines(brief: dict[str, object]) -> list[str]:
    items = brief.get("comparison_head_to_head", [])
    if not isinstance(items, list):
        return []
    lines = [str(item).strip() for item in items if str(item).strip()]
    if not lines:
        return []
    return ["国内外对比："] + [f"- {line}" for line in lines]


def render_markdown_report(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"]) or "- 暂无"
    key_insights = "\n".join(f"- {item}" for item in brief["key_insights"]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}"
        for item in brief["mainlines"]
    ) or "- 暂无"
    mainline_memory = "\n".join(
        (
            f"- {item['title']}：{item['lifecycle_state']} / {item['risk_level']} / "
            f"已持续 {item['days_seen']} 天"
            + (f" / {item['enrichment_summary']}" if item.get("enrichment_summary") else "")
        )
        for item in brief["mainline_memory"]
    ) or "- 暂无"
    limitations = "\n".join(f"- {item}" for item in brief["limitations"]) or "- 暂无"
    actions = "\n".join(f"- {item}" for item in brief["actions"]) or "- 暂无"

    lines = [
        f"# {title}",
        "",
        f"生成时间：{generated_at}",
        "",
        "## 一句话判断",
        str(brief["judgment"]),
        "",
        "## 执行摘要",
        executive_summary,
        "",
        "## 关键洞察",
        key_insights,
        "",
        *_comparison_markdown_lines(brief),
        "",
        "## 重点主线",
        mainlines,
        "",
        "## 跨日主线记忆",
        mainline_memory,
        "",
        "## 重点主题分析",
    ]

    for topic in brief["topic_briefs"]:
        lines.extend(
            [
                f"### {topic['title']}",
                f"- 主领域：{topic['primary_domain']}",
                f"- 主要矛盾：{topic['primary_contradiction']}",
                f"- 核心洞察：{topic['core_insight']}",
                f"- 置信度：{topic['confidence']}",
                f"- 生命周期：{topic['lifecycle_state']}",
                f"- 风险等级：{topic['risk_level']}",
                f"- 交叉印证：{topic['enrichment_summary'] or '暂无'}",
                f"- 链接：{topic['url']}",
                "",
            ]
        )
        for evidence in topic.get("support_evidence", []):
            lines.extend(
                [
                    f"- 佐证：{evidence['source_type']} | {evidence['title']} | {evidence['url']}",
                ]
            )
        if topic.get("support_evidence"):
            lines.append("")

    lines.extend(
        [
            "## 短期推演",
            f"- 观察：{brief['watchlist']}",
            f"- 结论：{brief['forecast_conclusion'] or '暂无'}",
            "",
            "## 局限性",
            limitations,
            "",
            "## 行动建议",
            actions,
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_json_report(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_pushplus_notification(
    title: str,
    generated_at: str,
    payload: dict[str, object],
    public_site_url: str,
    raw_report_url: str,
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    lines = [
        title,
        f"生成时间：{generated_at}",
        "今日判断：",
        str(brief["judgment"]),
        "三条主线：",
    ]

    for index, item in enumerate(brief["mainlines"], start=1):
        lines.append(f"{index}. {item['title']}：{item['why_it_matters']}")

    comparison_lines = _comparison_delivery_lines(brief)
    if comparison_lines:
        lines.extend(comparison_lines)

    if brief["risk_note"]:
        lines.extend(["提醒：", brief["risk_note"]])

    lines.extend(["观察：", brief["watchlist"]])
    lines.extend(_link_lines(public_site_url, raw_report_url))
    return "\n".join(lines)


def render_text_notification(
    title: str,
    generated_at: str,
    payload: dict[str, object],
    public_site_url: str,
    raw_report_url: str,
) -> str:
    return render_pushplus_notification(
        title=title,
        generated_at=generated_at,
        payload=payload,
        public_site_url=public_site_url,
        raw_report_url=raw_report_url,
    )


def render_telegram_notification(
    title: str,
    generated_at: str,
    payload: dict[str, object],
    public_site_url: str,
    raw_report_url: str,
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}"
        for item in brief["mainlines"]
    ) or "- 暂无"
    topics = "\n".join(
        f"- {item['title']}：{item['core_insight']}"
        for item in brief["topic_briefs"]
    ) or "- 暂无"

    lines = [
        title,
        f"生成时间：{generated_at}",
        "",
        "今日判断：",
        str(brief["judgment"]),
        "",
        "执行摘要",
        executive_summary,
        "",
        "关键主线",
        mainlines,
        "",
        "重点主题",
        topics,
        "",
        "短期观察",
        f"- {brief['watchlist']}",
    ]

    comparison_lines = _comparison_delivery_lines(brief)
    if comparison_lines:
        lines.extend([""] + comparison_lines)

    if brief["risk_note"]:
        lines.extend(["", "局限与提醒", f"- {brief['risk_note']}"])

    review_lines = _review_lines(payload)
    if review_lines:
        lines.extend([""] + review_lines)

    lines.extend([""] + _link_lines(public_site_url, raw_report_url))
    return "\n".join(lines)


def render_feishu_notification(
    title: str,
    generated_at: str,
    payload: dict[str, object],
    public_site_url: str,
    raw_report_url: str,
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"][:2]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}"
        for item in brief["mainlines"][:3]
    ) or "- 暂无"
    actions = "\n".join(f"- {item}" for item in brief["actions"][:2]) or "- 暂无"

    lines = [
        title,
        f"生成时间：{generated_at}",
        "",
        "今日判断：",
        str(brief["judgment"]),
        "",
        "执行摘要",
        executive_summary,
        "",
        "关键主线",
        mainlines,
    ]

    comparison_lines = _comparison_delivery_lines(brief)
    if comparison_lines:
        lines.extend([""] + comparison_lines)

    if brief["risk_note"]:
        lines.extend(["", "局限与提醒", f"- {brief['risk_note']}"])

    review_lines = _review_lines(payload)
    if review_lines:
        lines.extend([""] + review_lines)

    lines.extend(["", "行动建议", actions, ""])
    lines.extend(_link_lines(public_site_url, raw_report_url))
    return "\n".join(lines)


def render_feishu_card_notification(
    title: str,
    generated_at: str,
    payload: dict[str, object],
    public_site_url: str,
    raw_report_url: str,
) -> dict[str, object]:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"][:2]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}"
        for item in brief["mainlines"][:3]
    ) or "- 暂无"
    actions = "\n".join(f"- {item}" for item in brief["actions"][:2]) or "- 暂无"

    elements: list[dict[str, object]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**生成时间**\n{generated_at}\n\n**今日判断**\n{brief['judgment']}",
            },
        },
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": f"**执行摘要**\n{executive_summary}"},
                },
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": f"**关键主线**\n{mainlines}"},
                },
            ],
        },
    ]

    comparison_lines = _comparison_delivery_lines(brief)
    if comparison_lines:
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**国内外对比**\n" + "\n".join(comparison_lines[1:])},
            }
        )

    if brief["risk_note"]:
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**局限与提醒**\n- {brief['risk_note']}"},
            }
        )

    review_lines = _review_lines(payload)
    if review_lines:
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(review_lines)},
            }
        )

    elements.extend(
        [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**行动建议**\n{actions}"},
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "公开阅读"},
                        "type": "primary",
                        "url": public_site_url,
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "GitHub 原文"},
                        "type": "default",
                        "url": raw_report_url,
                    },
                ],
            },
        ]
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": elements,
    }


def render_html_report(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)

    def _li(items):
        return "".join(f"<li>{_escape(item)}</li>" for item in items) if items else "<li>暂无</li>"

    def _topic_cards(topics):
        cards = []
        for t in topics:
            domain = _escape(t.get("primary_domain", ""))
            contradiction = _escape(t.get("primary_contradiction", ""))
            insight = _escape(t.get("core_insight", ""))
            confidence = _escape(str(t.get("confidence", "")))
            lifecycle_state = _escape(str(t.get("lifecycle_state", "")))
            risk_level = _escape(str(t.get("risk_level", "")))
            enrichment_summary = _escape(str(t.get("enrichment_summary", "")))
            support_evidence = t.get("support_evidence", [])
            url = _escape(t.get("url", ""))
            t_title = _escape(t.get("title", "未命名主题"))
            support_html = "".join(
                f"<li>{_escape(str(item.get('source_type', '')))} | "
                f"<a href=\"{_escape(str(item.get('url', '')))}\" target=\"_blank\" rel=\"noopener\">"
                f"{_escape(str(item.get('title', '')))}</a></li>"
                for item in support_evidence
                if str(item.get("title", "")).strip()
            ) or "<li>暂无</li>"
            cards.append(
                f"""<div class="signal-card">
                <div class="signal-header">
                  <h3>{t_title}</h3>
                  <span class="badge badge--{confidence}">{confidence}</span>
                </div>
                <div class="signal-body">
                  <p><strong>主领域：</strong>{domain}</p>
                  <p><strong>主要矛盾：</strong>{contradiction}</p>
                  <p><strong>核心洞察：</strong>{insight}</p>
                  <p><strong>生命周期：</strong>{lifecycle_state or 'new'}</p>
                  <p><strong>风险等级：</strong>{risk_level or 'low'}</p>
                  <p><strong>交叉印证：</strong>{enrichment_summary or '暂无'}</p>
                  <p><strong>佐证列表：</strong></p>
                  <ul>{support_html}</ul>
                </div>
                <a class="signal-link" href="{url}" target="_blank" rel="noopener">查看原文 →</a>
              </div>"""
            )
        return "\n".join(cards)

    def _key_points(points):
        items = []
        for p in points:
            pt = _escape(p.get("title", ""))
            wm = _escape(p.get("why_it_matters", ""))
            if pt or wm:
                items.append(f'<li><strong>{pt}</strong> {wm}</li>')
        return "\n".join(items) or "<li>暂无</li>"

    mainline_items = _key_points(brief["mainlines"])
    mainline_memory_items = "".join(
        (
            f"<li><strong>{_escape(item['title'])}</strong> "
            f"<span class=\"domain-tag\">{_escape(item['lifecycle_state'])}</span> "
            f"<span class=\"domain-tag\">{_escape(item['risk_level'])}</span> "
            f"已持续 {_escape(item['days_seen'])} 天"
            + (
                f" · {_escape(item['enrichment_summary'])}"
                if item.get("enrichment_summary")
                else ""
            )
            + "</li>"
        )
        for item in brief["mainline_memory"]
    ) or "<li>暂无</li>"
    topic_cards_html = _topic_cards(brief["topic_briefs"])
    exec_summary_li = _li(brief["executive_summary"])
    key_insights_li = _li(brief["key_insights"])
    limitations_li = _li(brief["limitations"])
    actions_li = _li(brief["actions"])

    total_items = int(payload.get("meta", {}).get("total_items", 0))
    total_topics = int(payload.get("meta", {}).get("total_topics", 0))

    forecast_html = ""
    fc = payload.get("forecast", {})
    if isinstance(fc, dict) and fc.get("forecast_conclusion"):
        best = _escape(fc.get("best_case", ""))
        worst = _escape(fc.get("worst_case", ""))
        likely = _escape(fc.get("most_likely_case", ""))
        conclusion = _escape(fc.get("forecast_conclusion", ""))
        variables = [f"<li>{_escape(v)}</li>" for v in (fc.get("key_variables") or [])]
        forecast_html = f"""
      <section id="forecast" class="section">
        <h2 class="section-title">📈 短期推演</h2>
        <div class="forecast-grid">
          <div class="forecast-card forecast-card--best"><h4>乐观情景</h4><p>{best}</p></div>
          <div class="forecast-card forecast-card--worst"><h4>悲观情景</h4><p>{worst}</p></div>
          <div class="forecast-card forecast-card--likely"><h4>最可能情景</h4><p>{likely}</p></div>
        </div>
        <p><strong>关键变量：</strong></p>
        <ul>{"".join(variables)}</ul>
        <p><strong>结论：</strong>{conclusion}</p>
      </section>""".strip()

    risk_note_html = ""
    if brief.get("risk_note"):
        risk_note_html = f'<p class="risk-note">⚠️ {_escape(brief["risk_note"])}</p>'

    signals_list_html = ""
    signals = payload.get("signals", [])
    if signals:
        signal_items = []
        for s in signals[:15]:
            s_title = _escape(s.get("title", ""))
            s_domain = _escape(s.get("primary_domain", ""))
            s_score = round(float(s.get("score", 0)), 1)
            s_evidence = int(s.get("evidence_count", 0))
            s_url = _escape(s.get("url", ""))
            signal_items.append(
                f'<tr><td>{s_title}<span class="domain-tag">{s_domain}</span></td>'
                f"<td>{s_score}</td>"
                f"<td>{s_evidence}</td>"
                f'<td><a href="{s_url}" target="_blank" rel="noopener">链接 →</a></td></tr>'
            )
        signals_list_html = (
            '<table class="signals-table">'
            "<thead><tr><th>信号</th><th>评分</th><th>证据数</th><th>来源</th></tr></thead>"
            "<tbody>"
            + "".join(signal_items)
            + "</tbody></table>"
        )

    stage_status = payload.get("stage_status", {})
    stage_badges = ""
    for stage, status in stage_status.items():
        color = "#10b981" if status == "ok" else ("#f59e0b" if status == "fallback" else "#6b7280")
        stage_badges += f'<span class="stage-badge" style="--stage-color:{color}">{_escape(stage)}: {_escape(status)}</span>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape(title)}</title>
<style>
  :root {{
    --bg:#0d1117; --bg2:#161b22; --bg3:#1c2333; --border:#30363d;
    --text:#e6edf3; --text2:#8b949e; --accent:#58a6ff; --green:#3fb950;
    --orange:#d29922; --red:#f85149; --purple:#bc8cff; --radius:8px;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;
  }}
  * {{ box-sizing:border-box;margin:0;padding:0; }}
  body {{ background:var(--bg);color:var(--text);line-height:1.6; }}
  .wrap {{ max-width:960px;margin:0 auto;padding:24px 20px 48px; }}
  header {{ text-align:center;padding:32px 0 24px;border-bottom:1px solid var(--border);margin-bottom:32px; }}
  header h1 {{ font-size:1.8em;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent; }}
  header .meta {{ color:var(--text2);font-size:.9em;margin-top:8px; }}
  header .stats {{ display:flex;gap:16px;justify-content:center;margin-top:12px;flex-wrap:wrap; }}
  header .stat-pill {{ background:var(--bg3);padding:4px 14px;border-radius:20px;font-size:.85em;color:var(--text2);border:1px solid var(--border); }}
  .stage-badges {{ display:flex;gap:8px;justify-content:center;margin-top:12px;flex-wrap:wrap; }}
  .stage-badge {{ background:var(--bg3);padding:3px 12px;border-radius:6px;font-size:.82em;border:1px solid var(--stage-color,#666);color:var(--text2); }}
  .section {{ margin-bottom:28px; }}
  .section-title {{ font-size:1.25em;font-weight:600;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--accent); }}
  .judgment {{ font-size:1.35em;font-weight:700;text-align:center;padding:20px;background:var(--bg2);border-radius:var(--radius);border-left:4px solid var(--accent); }}
  .grid-2 {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px; }}
  .card {{ background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:18px; }}
  .card h4 {{ color:var(--accent);margin-bottom:10px;font-size:.95em; }}
  .card ul {{ padding-left:18px;color:var(--text2); }}
  .card li {{ margin-bottom:4px; }}
  .signal-card {{ background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-bottom:12px;transition:border-color .2s; }}
  .signal-card:hover {{ border-color:var(--accent); }}
  .signal-header {{ display:flex;justify-content:space-between;align-items:start;margin-bottom:10px; }}
  .signal-header h3 {{ font-size:1em;color:var(--text); }}
  .badge {{ font-size:.75em;padding:2px 10px;border-radius:12px;font-weight:600; }}
  .badge--high {{ background:#1a3a2a;color:var(--green); }}
  .badge--medium {{ background:#3a3020;color:var(--orange); }}
  .badge--low {{ background:#3a2220;color:var(--red); }}
  .signal-body p {{ margin:4px 0;color:var(--text2);font-size:.9em; }}
  .signal-link {{ display:inline-block;margin-top:10px;font-size:.85em;color:var(--accent);text-decoration:none; }}
  .signal-link:hover {{ text-decoration:underline; }}
  .forecast-grid {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:14px 0; }}
  .forecast-card {{ background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:14px; }}
  .forecast-card h4 {{ font-size:.9em;margin-bottom:8px; }}
  .forecast-card--best {{ border-left:3px solid var(--green); }}
  .forecast-card--worst {{ border-left:3px solid var(--red); }}
  .forecast-card--likely {{ border-left:3px solid var(--accent); }}
  .forecast-card p {{ font-size:.88em;color:var(--text2); }}
  .risk-note {{ background:#3a2220;border:1px solid var(--red);border-radius:var(--radius);padding:12px 16px;margin-top:12px;color:#fdaebb;font-size:.9em; }}
  .domain-tag {{ display:inline-block;font-size:.72em;background:var(--bg3);color:var(--text2);padding:1px 8px;border-radius:10px;margin-left:8px; }}
  table.signals-table {{ width:100%;border-collapse:collapse;margin-top:10px;font-size:.88em; }}
  .signals-table th,.signals-table td {{ padding:8px 12px;text-align:left;border-bottom:1px solid var(--border); }}
  .signals-table th {{ background:var(--bg3);color:var(--text2);font-weight:600;position:sticky;top:0; }}
  .signals-table tr:hover td {{ background:var(--bg2); }}
  footer {{ text-align:center;padding:24px 0;border-top:1px solid var(--border);margin-top:40px;color:var(--text2);font-size:.82em; }}
  @media(max-width:640px) {{ header h1 {{ font-size:1.4em; }} .grid-2 {{ grid-template-columns:1fr; }} .forecast-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{_escape(title)}</h1>
    <div class="meta">生成时间：{_escape(generated_at)}</div>
    <div class="stats">
      <span class="stat-pill">📡 {total_items} 条原始信息</span>
      <span class="stat-pill">🎯 {total_topics} 个主题</span>
      <span class="stat-pill">📊 {len(brief['topic_briefs'])} 个重点分析</span>
    </div>
    <div class="stage-badges">{stage_badges}</div>
  </header>

  <section id="judgment" class="section">
    <div class="judgment">{_escape(str(brief['judgment']))}</div>
  </section>

  <section id="executive-summary" class="section">
    <h2 class="section-title">执行摘要</h2>
    <ul>{exec_summary_li}</ul>
  </section>

  <section id="key-insights" class="section">
    <h2 class="section-title">关键洞察</h2>
    <ul>{key_insights_li}</ul>
  </section>

  <section id="mainlines" class="section">
    <h2 class="section-title">重点主线</h2>
    <ul style="padding-left:20px;">{mainline_items}</ul>
  </section>

  <section id="memory" class="section">
    <h2 class="section-title">跨日主线记忆</h2>
    <ul style="padding-left:20px;">{mainline_memory_items}</ul>
  </section>

  <section id="topics" class="section">
    <h2 class="section-title">重点主题分析</h2>
    {topic_cards_html}
  </section>

  {forecast_html}

  <section id="limitations" class="section">
    <h2 class="section-title">局限性</h2>
    <ul>{limitations_li}</ul>
  </section>

  {risk_note_html}

  <section id="actions" class="section">
    <h2 class="section-title">行动建议</h2>
    <ul>{actions_li}</ul>
  </section>

  <section id="all-signals" class="section">
    <h2 class="section-title">全部信号</h2>
    {signals_list_html}
  </section>

  <footer>
    <p>VS_AI 情报采集系统自动生成 · 数据来源：RSS / GitHub / 官方网站</p>
  </footer>
</div>
</body>
</html>"""
