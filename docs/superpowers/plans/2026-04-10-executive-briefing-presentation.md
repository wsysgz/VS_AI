# Executive Briefing Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade VS_AI text outputs so WeChat, Telegram, and Markdown all render from one executive-brief structure with channel-specific depth.

**Architecture:** Keep the current staged AI pipeline and `summary_payload` shape intact, but add a lightweight briefing composer that normalizes payload data into reusable brief blocks. Renderers then consume those brief blocks to produce a short WeChat brief, a fuller Telegram brief, and a formal Markdown archive without each channel re-deriving its own structure.

**Tech Stack:** Python 3.14, pytest, dataclasses, existing `auto_report` pipeline/app modules

---

### Task 1: Add The Executive Brief Composer

**Files:**
- Create: `src/auto_report/pipeline/briefing.py`
- Create: `tests/test_briefing.py`

- [ ] **Step 1: Write the failing tests**

```python
from auto_report.pipeline.briefing import compose_executive_brief


def test_compose_executive_brief_builds_mainlines_topics_and_notes():
    brief = compose_executive_brief(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload={
            "meta": {"total_items": 12, "total_topics": 5},
            "one_line_core": "Agent 工具链继续向专业化和评估化收敛。",
            "executive_summary": ["评估框架继续增加。", "部署链路开始收敛。"],
            "key_points": [
                {"title": "评估框架增加", "why_it_matters": "可靠性门槛提高"},
                {"title": "模型发布提速", "why_it_matters": "生态竞争升温"},
            ],
            "key_insights": ["评估和交付正绑定出现。"],
            "analyses": [
                {
                    "title": "Signal A",
                    "primary_domain": "ai-llm-agent",
                    "primary_contradiction": "速度 vs 可靠性",
                    "core_insight": "评估开始前置。",
                    "confidence": "medium",
                    "url": "https://example.com/a",
                }
            ],
            "forecast": {
                "most_likely_case": "短期继续围绕评估与部署演进",
                "forecast_conclusion": "继续看真实落地反馈。",
            },
            "limitations": ["部分信号仍需复核"],
            "actions": ["继续跟踪评估框架"],
            "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
        },
    )

    assert brief["judgment"] == "Agent 工具链继续向专业化和评估化收敛。"
    assert brief["mainlines"][0]["title"] == "评估框架增加"
    assert brief["topic_briefs"][0]["title"] == "Signal A"
    assert brief["watchlist"] == "短期继续围绕评估与部署演进"
    assert brief["risk_note"] == "部分信号仍需复核"
    assert brief["action_note"] == "继续跟踪评估框架"


def test_compose_executive_brief_degrades_gracefully_with_sparse_payload():
    brief = compose_executive_brief(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload={
            "one_line_core": "",
            "executive_summary": [],
            "key_points": [],
            "key_insights": [],
            "analyses": [],
            "forecast": {},
            "limitations": [],
            "actions": [],
            "meta": {"total_items": 0, "total_topics": 0},
            "stage_status": {"analysis": "fallback", "summary": "fallback", "forecast": "fallback"},
        },
    )

    assert brief["judgment"] == "暂无核心判断"
    assert brief["mainlines"] == []
    assert brief["topic_briefs"] == []
    assert brief["watchlist"] == "本轮先保持观察，等待更多高置信度信号。"
    assert brief["risk_note"] == ""
    assert brief["action_note"] == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_briefing.py -v`
Expected: FAIL with `ModuleNotFoundError` for `auto_report.pipeline.briefing`

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations


def _pick_judgment(payload: dict[str, object]) -> str:
    return str(payload.get("one_line_core") or "").strip() or "暂无核心判断"


def _build_mainlines(payload: dict[str, object]) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    for point in payload.get("key_points", [])[:3]:
        title = str(point.get("title", "")).strip()
        why = str(point.get("why_it_matters", "")).strip()
        if title:
            lines.append({"title": title, "why_it_matters": why or "需要继续观察"})
    return lines


def _build_topic_briefs(payload: dict[str, object]) -> list[dict[str, str]]:
    topics: list[dict[str, str]] = []
    for analysis in payload.get("analyses", [])[:3]:
        title = str(analysis.get("title", "")).strip()
        if not title:
            continue
        topics.append(
            {
                "title": title,
                "primary_domain": str(analysis.get("primary_domain", "unknown")),
                "core_insight": str(analysis.get("core_insight", "需要继续观察。")),
                "primary_contradiction": str(analysis.get("primary_contradiction", "待补充")),
                "confidence": str(analysis.get("confidence", "low")),
                "url": str(analysis.get("url", "")).strip(),
            }
        )
    return topics


def compose_executive_brief(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> dict[str, object]:
    limitations = [str(item).strip() for item in payload.get("limitations", []) if str(item).strip()]
    actions = [str(item).strip() for item in payload.get("actions", []) if str(item).strip()]
    forecast = payload.get("forecast", {})

    return {
        "title": title,
        "generated_at": generated_at,
        "judgment": _pick_judgment(payload),
        "executive_summary": [str(item).strip() for item in payload.get("executive_summary", []) if str(item).strip()],
        "key_insights": [str(item).strip() for item in payload.get("key_insights", []) if str(item).strip()],
        "mainlines": _build_mainlines(payload),
        "topic_briefs": _build_topic_briefs(payload),
        "watchlist": str(forecast.get("most_likely_case", "")).strip() or "本轮先保持观察，等待更多高置信度信号。",
        "forecast_conclusion": str(forecast.get("forecast_conclusion", "")).strip(),
        "risk_note": limitations[0] if limitations else "",
        "action_note": actions[0] if actions else "",
        "limitations": limitations,
        "actions": actions,
        "stage_status": payload.get("stage_status", {}),
        "meta": payload.get("meta", {}),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_briefing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/pipeline/briefing.py tests/test_briefing.py
git commit -m "feat: add executive briefing composer"
```

### Task 2: Render WeChat, Telegram, And Markdown From Shared Brief Blocks

**Files:**
- Modify: `src/auto_report/outputs/renderers.py`
- Modify: `tests/test_renderers.py`

- [ ] **Step 1: Write the failing tests**

```python
from auto_report.outputs.renderers import (
    render_markdown_report,
    render_telegram_notification,
    render_text_notification,
)


def _sample_payload() -> dict[str, object]:
    return {
        "one_line_core": "Agent 工具链继续向专业化和评估化收敛。",
        "executive_summary": ["评估框架继续增加。", "部署链路开始收敛。"],
        "key_points": [
            {"title": "评估框架增加", "why_it_matters": "可靠性门槛提高"},
            {"title": "模型发布提速", "why_it_matters": "生态竞争升温"},
        ],
        "key_insights": ["评估与交付开始绑定出现。"],
        "analyses": [
            {
                "title": "Signal A",
                "primary_domain": "ai-llm-agent",
                "primary_contradiction": "速度 vs 可靠性",
                "core_insight": "评估开始前置。",
                "confidence": "medium",
                "url": "https://example.com/a",
            }
        ],
        "forecast": {
            "most_likely_case": "短期继续围绕评估与部署演进",
            "forecast_conclusion": "继续看真实落地反馈。",
        },
        "limitations": ["部分信号仍需复核"],
        "actions": ["继续跟踪评估框架"],
        "meta": {"total_items": 12, "total_topics": 5},
        "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
    }


def test_render_text_notification_uses_executive_brief_short_shape():
    text = render_text_notification(
        title="AI情报早报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "今日判断：" in text
    assert "三条主线：" in text
    assert "1. 评估框架增加" in text
    assert "提醒：" in text
    assert "观察：" in text


def test_render_telegram_notification_uses_full_brief_shape():
    text = render_telegram_notification(
        title="AI情报完整简报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "执行摘要" in text
    assert "关键主线" in text
    assert "重点主题" in text
    assert "局限与提醒" in text


def test_render_markdown_report_uses_formal_brief_sections():
    report = render_markdown_report(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
    )

    assert "## 一句话判断" in report
    assert "## 重点主线" in report
    assert "## 重点主题分析" in report
    assert "## 行动建议" in report
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_renderers.py -v`
Expected: FAIL because `render_telegram_notification` does not exist and current headings still use first-round wording

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations

import json

from auto_report.pipeline.briefing import compose_executive_brief


def render_markdown_report(title: str, generated_at: str, payload: dict[str, object]) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"]) or "- 暂无"
    key_insights = "\n".join(f"- {item}" for item in brief["key_insights"]) or "- 暂无"
    limitations = "\n".join(f"- {item}" for item in brief["limitations"]) or "- 暂无"
    actions = "\n".join(f"- {item}" for item in brief["actions"]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}" for item in brief["mainlines"]
    ) or "- 暂无"

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
        "## 重点主线",
        mainlines,
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
                f"- 链接：{topic['url']}",
                "",
            ]
        )

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


def render_text_notification(title: str, generated_at: str, payload: dict[str, object], detail_url: str) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    lines = [title, f"生成时间：{generated_at}", "今日判断：", str(brief["judgment"]), "三条主线："]
    for index, item in enumerate(brief["mainlines"], start=1):
        lines.append(f"{index}. {item['title']}：{item['why_it_matters']}")
    if brief["risk_note"]:
        lines.extend(["提醒：", brief["risk_note"]])
    lines.extend(["观察：", brief["watchlist"], "详情链接：", detail_url])
    return "\n".join(lines)


def render_telegram_notification(title: str, generated_at: str, payload: dict[str, object], detail_url: str) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}" for item in brief["mainlines"]
    ) or "- 暂无"
    topics = "\n".join(
        f"- {item['title']}：{item['core_insight']}" for item in brief["topic_briefs"]
    ) or "- 暂无"

    parts = [
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

    if brief["risk_note"]:
        parts.extend(["", "局限与提醒", f"- {brief['risk_note']}"])

    parts.extend(["", "详情链接：", detail_url])
    return "\n".join(parts)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_renderers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/outputs/renderers.py tests/test_renderers.py
git commit -m "feat: render executive briefing text outputs"
```

### Task 3: Route PushPlus And Telegram Through Their Own Brief Renderers

**Files:**
- Modify: `src/auto_report/app.py`
- Modify: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_render_reports_writes_executive_brief_markdown(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    sample_items = [
        CollectedItem(
            source_id="rss",
            item_id="1",
            title="Agent platform launched",
            url="https://example.com/agent-platform",
            summary="A new reasoning agent stack for enterprise deployment",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "reasoning"],
            language="en",
            metadata={},
        )
    ]

    monkeypatch.setattr("auto_report.app.collect_all_items", lambda settings: (sample_items, ["测试诊断"]))

    render_reports(tmp_path)

    content = (tmp_path / "data" / "reports" / "latest-summary.md").read_text(encoding="utf-8")
    assert "## 一句话判断" in content
    assert "## 重点主线" in content
    assert "## 行动建议" in content


def test_run_once_uses_executive_brief_short_pushplus_content(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    sample_items = [
        CollectedItem(
            source_id="rss",
            item_id="1",
            title="Agent platform launched",
            url="https://example.com/agent-platform",
            summary="A new reasoning agent stack for enterprise deployment",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "reasoning"],
            language="en",
            metadata={},
        )
    ]

    captured = {}
    monkeypatch.setattr("auto_report.app.collect_all_items", lambda settings: (sample_items, ["测试诊断"]))

    def fake_send_pushplus(token, title, content, channel="", template="markdown"):
        captured["content"] = content
        captured["channel"] = channel
        captured["template"] = template
        return {"code": 200}

    monkeypatch.setattr("auto_report.app.send_pushplus", fake_send_pushplus)
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")

    run_once(tmp_path)

    assert captured["channel"] == "clawbot"
    assert captured["template"] == "txt"
    assert "今日判断：" in captured["content"]
    assert "三条主线：" in captured["content"]


def test_run_once_uses_executive_brief_full_telegram_content(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    sample_items = [
        CollectedItem(
            source_id="rss",
            item_id="1",
            title="Agent platform launched",
            url="https://example.com/agent-platform",
            summary="A new reasoning agent stack for enterprise deployment",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "reasoning"],
            language="en",
            metadata={},
        )
    ]

    captured = {}
    monkeypatch.setattr("auto_report.app.collect_all_items", lambda settings: (sample_items, ["测试诊断"]))
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: {"code": 200})

    def fake_send_telegram_messages(token, chat_id, text):
        captured["text"] = text
        return [{"ok": True}]

    monkeypatch.setattr("auto_report.app.send_telegram_messages", fake_send_telegram_messages)
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "8566057843")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")

    run_once(tmp_path)

    assert "执行摘要" in captured["text"]
    assert "关键主线" in captured["text"]
    assert "重点主题" in captured["text"]
    assert "详情链接：" in captured["text"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_run_once.py -v`
Expected: FAIL because `app.py` still builds Telegram content from raw Markdown and the Markdown headings are still first-round wording

- [ ] **Step 3: Write the minimal implementation**

```python
from auto_report.outputs.renderers import (
    render_json_report,
    render_markdown_report,
    render_telegram_notification,
    render_text_notification,
)


def _build_text_notification(root_dir: Path, settings) -> str:
    payload = _load_summary_payload(root_dir)
    generated_at = str(payload.get("meta", {}).get("generated_at", datetime.now().astimezone().isoformat()))
    local_date = generated_at[:10]
    return render_text_notification(
        title=f"AI情报早报 | {local_date} | 北京时间 07:00",
        generated_at=generated_at,
        payload=payload,
        detail_url=_build_detail_url(settings),
    )


def _build_telegram_notification(root_dir: Path, settings) -> str:
    payload = _load_summary_payload(root_dir)
    generated_at = str(payload.get("meta", {}).get("generated_at", datetime.now().astimezone().isoformat()))
    local_date = generated_at[:10]
    return render_telegram_notification(
        title=f"AI情报完整简报 | {local_date} | 北京时间 07:00",
        generated_at=generated_at,
        payload=payload,
        detail_url=_build_detail_url(settings),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_run_once.py -v`
Expected: PASS

- [ ] **Step 5: Run the full verification sequence**

Run: `python -m pytest -q`
Expected: PASS

Run: `python -m auto_report.cli run-once`
Expected: exit code `0`

Run: `Get-Content -Raw 'D:\GitHub\worktrees\auto\feature-executive-briefing\data\reports\latest-summary.md'`
Expected: contains `## 一句话判断`, `## 重点主线`, and `## 行动建议`

- [ ] **Step 6: Commit**

```bash
git add src/auto_report/app.py tests/test_run_once.py
git commit -m "feat: route briefing outputs by channel"
```

## Self-Review

### Spec coverage

- shared executive brief adaptation layer: Task 1
- WeChat short brief contract: Task 2 and Task 3
- Telegram full brief contract: Task 2 and Task 3
- Markdown formal archive contract: Task 2 and Task 3
- keep current AI payload and pipeline stable: Tasks avoid changing AI stage interfaces

No approved requirement from the presentation spec is left without a task.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later”
- Every task lists exact file paths
- Every code-changing step contains concrete code
- Every verification step includes exact commands and expected outcomes

### Type consistency

- `compose_executive_brief()` returns the same normalized keys used by all renderers
- renderers continue to accept `title`, `generated_at`, and raw `payload`
- `app.py` continues to load `summary_payload` from `latest-summary.json` and only changes renderer routing
