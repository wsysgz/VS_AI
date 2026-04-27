"""GitHub Pages 站点构建器 — V7 Milestone B public reading site."""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

from auto_report.pipeline.briefing import compose_executive_brief


SITE_TITLE = "VS_AI 情报阅读站"
SITE_URL = "https://wsysgz.github.io/VS_AI"
SITE_DESCRIPTION = "AI、智能体与电子信息每日情报工作台，提供归档、周报、专题、检索和订阅。"
FAVICON_LINK = (
    '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 '
    'viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%228%22 '
    'fill=%22%23081018%22/%3E%3Ccircle cx=%2216%22 cy=%2216%22 r=%227%22 '
    'fill=%22%2343d1bf%22/%3E%3C/svg%3E">'
)

DOMAIN_LABELS = {
    "ai-llm-agent": "AI/智能体",
    "ai-x-electronics": "AI × 电子",
}
PUBLICATION_PRIORITY = {"reviewed": 1, "auto": 0}
TRACK_LABELS = {
    "embedded": "嵌入式",
    "frontier-ai": "前沿 AI",
    "compute-infra": "算力基础设施",
    "agent-reliability": "智能体可靠性",
    "ai-infra": "AI 基础设施",
}
SOURCE_LABELS = {
    "espressif-blog": "乐鑫开发者博客",
    "nvidia-embedded": "英伟达嵌入式博客",
    "openai-news": "OpenAI 新闻",
    "zhipu-news": "智谱新闻",
}
TAG_LABELS = {
    "ai-llm-agent": "AI/智能体",
    "ai-x-electronics": "AI × 电子",
    "microsoft.com": "微软",
    "github.com": "GitHub",
    "arxiv.org": "arXiv",
    "Research Blog": "研究博客",
    "cs.AI": "AI 论文",
    "cs.LG": "机器学习论文",
    "hacker-news": "Hacker News",
    "show-hn": "展示项目",
    "release": "发布",
    "infra": "基础设施",
    "search": "检索",
    "archives": "归档",
}
TITLE_TRANSLATIONS = {
    "Systematic debugging for AI agents: Introducing the AgentRx framework": "AI 智能体系统化调试：AgentRx 框架",
    "Cyber Defense Benchmark: Agentic Threat Hunting Evaluation for LLMs in SecOps": "网络防御基准：安全运营中的智能体威胁狩猎评估",
    "Speculative Actions: A Lossless Framework for Faster Agentic Systems": "推测式动作：加速智能体系统的无损框架",
    "Hear your agent suffer through your code": "让智能体在代码中暴露问题",
    "Show HN: Browser Harness – Gives LLM freedom to complete any browser task": "Browser Harness：让大模型自主完成浏览器任务",
    "vllm-project/vllm": "vLLM 项目",
    "Automations": "自动化任务",
    "AI agent development is shifting from raw capability to production-readiness: new frameworks address debugging opacity and latency bottlenecks, while stark benchmarking reveals massive capability gaps in real-world security tasks.": "AI 智能体开发正在从单纯能力展示转向生产可用：新框架开始处理调试黑箱和延迟瓶颈，而安全任务基准暴露出现实能力缺口。",
    "The AI agent ecosystem is rapidly evolving from capability-focused to security-first, with OpenAI, Brex, and Microsoft independently addressing the core tension between agent autonomy and production safety.": "AI 智能体生态正在从能力优先转向安全优先，OpenAI、Brex 和 Microsoft 分别处理智能体自主性与生产安全之间的核心张力。",
}


def _normalize_publication_mode(value: object) -> str:
    return "reviewed" if str(value or "").strip().lower() == "reviewed" else "auto"


def _publication_label(publication_mode: str) -> str:
    return "人工复核版" if _normalize_publication_mode(publication_mode) == "reviewed" else "自动版"


def _parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _safe_text(value: object) -> str:
    return str(value or "").strip()


def _strip_html(raw: object) -> str:
    text = html.unescape(_safe_text(raw))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _domain_label(domain: str) -> str:
    return DOMAIN_LABELS.get(domain, domain or "unknown")


def _track_label(value: object) -> str:
    raw = _safe_text(value)
    return TRACK_LABELS.get(raw, raw)


def _localize_known_text(value: object) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    if text in TITLE_TRANSLATIONS:
        return TITLE_TRANSLATIONS[text]
    if " appeared across " in text and "Requires deeper verification" in text:
        title = text.split(" appeared across ", 1)[0]
        return f"{_localize_known_text(title)} 已进入信号池，仍需继续复核。"
    for raw, label in TRACK_LABELS.items():
        text = text.replace(raw, label)
    for raw, label in TITLE_TRANSLATIONS.items():
        text = text.replace(raw, label)
    return text


def _source_id_label(source_ids: object) -> str:
    if not isinstance(source_ids, list):
        return ""
    labels = [SOURCE_LABELS.get(str(source_id).strip(), str(source_id).strip()) for source_id in source_ids]
    labels = [label for label in labels if label]
    return "、".join(labels[:2])


def _comparison_signal_label(title: object, track: object, source_ids: object) -> str:
    track_text = _track_label(track) or "相关赛道"
    source_text = _source_id_label(source_ids)
    if source_text:
        return f"{source_text}：{track_text} 方向信号"
    return _localize_known_text(title)


def _href(url: object, prefix: str = "") -> str:
    text = _safe_text(url)
    if not text:
        return "#"
    if text.startswith(("http://", "https://", "#", "/")):
        return text
    return f"{prefix}{text}"


def _tag_label(value: object) -> str:
    text = _safe_text(value)
    return TAG_LABELS.get(text, _domain_label(text))


def _source_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    return _tag_label(host) if host else "unknown"


def _format_date(date_text: str) -> str:
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%Y.%m.%d")
    except ValueError:
        return date_text


def _parse_date(date_text: str) -> date:
    return datetime.strptime(date_text, "%Y-%m-%d").date()


def _normalize_review(meta: object) -> dict[str, str]:
    if not isinstance(meta, dict):
        return {"reviewer": "", "review_note": ""}
    review = meta.get("review", {})
    if not isinstance(review, dict):
        review = {}
    return {
        "reviewer": _safe_text(review.get("reviewer")),
        "review_note": _safe_text(review.get("review_note")),
    }


def _comparison_item_text(item: object) -> str:
    if isinstance(item, dict):
        return _localize_known_text(
            _safe_text(item.get("readout"))
            or _safe_text(item.get("title"))
            or _safe_text(item.get("summary"))
            or _safe_text(item.get("delta"))
        )
    return _localize_known_text(item)


def _normalize_comparison_highlights(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    highlights: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            title = _comparison_signal_label(
                _safe_text(item.get("title")) or _safe_text(item.get("readout")),
                item.get("tech_track") or item.get("track"),
                item.get("source_ids", []),
            )
            if not title:
                continue
            highlights.append(
                {
                    "title": title,
                    "meta": _track_label(item.get("tech_track") or item.get("track")),
                    "summary": _localize_known_text(item.get("summary")),
                }
            )
            continue
        text = _safe_text(item)
        if text:
            highlights.append({"title": text, "meta": "", "summary": ""})
    return highlights[:4]


def _normalize_comparison_rows(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            track = _track_label(item.get("tech_track") or item.get("track"))
            cn = _comparison_signal_label(
                _safe_text(item.get("cn_title")) or _safe_text(item.get("cn")),
                item.get("tech_track") or item.get("track"),
                item.get("cn_source_ids", []),
            )
            intl = _comparison_signal_label(
                _safe_text(item.get("intl_title")) or _safe_text(item.get("intl")),
                item.get("tech_track") or item.get("track"),
                item.get("intl_source_ids", []),
            )
            delta = _localize_known_text(item.get("delta"))
            has_structured_sources = bool(item.get("cn_source_ids")) or bool(item.get("intl_source_ids"))
            readout = "" if has_structured_sources and not delta else _localize_known_text(item.get("readout"))
            if not any((track, cn, intl, delta, readout)):
                continue
            rows.append(
                {
                    "track": track or "同轨对比",
                    "cn": cn or "暂无国内侧摘要",
                    "intl": intl or "暂无海外侧摘要",
                    "delta": delta or readout,
                }
            )
            continue
        text = _safe_text(item)
        if text:
            rows.append({"track": "同轨对比", "cn": text, "intl": "", "delta": ""})
    return rows[:4]


def _normalize_comparison_brief(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {
            "cn_highlights": [],
            "intl_highlights": [],
            "head_to_head": [],
            "gaps": [],
            "watchpoints": [],
        }
    comparison = {
        "cn_highlights": _normalize_comparison_highlights(raw.get("cn_highlights", [])),
        "intl_highlights": _normalize_comparison_highlights(raw.get("intl_highlights", [])),
        "head_to_head": _normalize_comparison_rows(raw.get("head_to_head", [])),
        "gaps": [_comparison_item_text(item) for item in raw.get("gaps", []) if _comparison_item_text(item)],
        "watchpoints": [
            _comparison_item_text(item)
            for item in raw.get("watchpoints", [])
            if _comparison_item_text(item)
        ],
    }
    return comparison


def _has_comparison_content(comparison: object) -> bool:
    if not isinstance(comparison, dict):
        return False
    return any(comparison.get(key) for key in ("cn_highlights", "intl_highlights", "head_to_head", "gaps", "watchpoints"))


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_latest_payload(reports_dir: Path) -> dict[str, object]:
    candidates = [
        reports_dir / "latest-summary-reviewed.json",
        reports_dir / "latest-summary-auto.json",
        reports_dir / "latest-summary.json",
    ]
    for path in candidates:
        if path.exists():
            return _read_json(path)
    raise FileNotFoundError(f"Latest report not found under {reports_dir}")


def _load_archive_payloads(archives_dir: Path) -> list[tuple[str, dict[str, object]]]:
    payloads: list[tuple[str, dict[str, object]]] = []
    if not archives_dir.exists():
        return payloads

    for day_dir in sorted((path for path in archives_dir.iterdir() if path.is_dir()), reverse=True):
        json_files = sorted(day_dir.glob("*-summary*.json"))
        if not json_files:
            continue
        for json_file in json_files:
            payloads.append((day_dir.name, _read_json(json_file)))
    return payloads


def _normalize_report(payload: dict[str, object], archive_date: str | None = None) -> dict[str, object]:
    meta = payload.get("meta", {})
    generated_at = _safe_text(meta.get("generated_at"))
    publication_mode = _normalize_publication_mode(meta.get("publication_mode"))
    review = _normalize_review(meta)
    brief = compose_executive_brief("自动情报快报", generated_at, payload)
    comparison_brief = _normalize_comparison_brief(payload.get("comparison_brief", {}))
    if not _has_comparison_content(comparison_brief):
        comparison_brief = _normalize_comparison_brief(brief.get("comparison_brief", {}))
    date_text = archive_date or (generated_at[:10] if generated_at else "unknown")
    signals = payload.get("signals", [])

    source_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    normalized_signals: list[dict[str, object]] = []
    for raw_signal in signals:
        if not isinstance(raw_signal, dict):
            continue
        title = _safe_text(raw_signal.get("title"))
        if not title:
            continue
        url = _safe_text(raw_signal.get("url"))
        signal_index = len(normalized_signals) + 1
        source = _source_label(url)
        domain = _safe_text(raw_signal.get("primary_domain")) or "unknown"
        tags = [str(tag).strip() for tag in raw_signal.get("tags", []) if str(tag).strip()]
        summary = _strip_html(raw_signal.get("summary"))
        signal = {
            "title": _localize_known_text(title),
            "raw_title": title,
            "url": url,
            "summary": summary or "暂无摘要",
            "domain": domain,
            "domain_label": _domain_label(domain),
            "source": source,
            "date": date_text,
            "date_label": _format_date(date_text),
            "article_url": f"archives/{date_text}/signals/{signal_index}/",
            "score": round(float(raw_signal.get("score", 0.0)), 1),
            "evidence_count": int(raw_signal.get("evidence_count", 0)),
            "lifecycle_state": _safe_text(raw_signal.get("lifecycle_state")) or "new",
            "risk_level": _safe_text(raw_signal.get("risk_level")) or "low",
            "enrichment_summary": _safe_text(raw_signal.get("enrichment_summary")) or "暂无交叉印证",
            "tags": tags,
        }
        normalized_signals.append(signal)
        source_counts[source] += 1
        domain_counts[_domain_label(domain)] += 1

    return {
        "date": date_text,
        "date_label": _format_date(date_text),
        "generated_at": generated_at,
        "judgment": _localize_known_text(brief["judgment"]),
        "executive_summary": [_localize_known_text(item) for item in brief["executive_summary"][:3]],
        "mainlines": brief["mainlines"][:3],
        "topic_briefs": brief["topic_briefs"][:3],
        "watchlist": _localize_known_text(brief["watchlist"]),
        "forecast_conclusion": _localize_known_text(brief["forecast_conclusion"]),
        "comparison_brief": comparison_brief,
        "publication_mode": publication_mode,
        "publication_label": _publication_label(publication_mode),
        "review": review,
        "signals": normalized_signals,
        "top_signals": normalized_signals[:6],
        "source_counts": dict(source_counts.most_common()),
        "domain_counts": dict(domain_counts.most_common()),
        "total_items": int(meta.get("total_items", 0)),
        "total_topics": int(meta.get("total_topics", 0)),
        "archive_url": f"archives/{date_text}/",
        "brief_url": f"archives/{date_text}/brief/",
    }


def _collect_reports(reports_dir: Path, archives_dir: Path) -> list[dict[str, object]]:
    latest_report = _normalize_report(_load_latest_payload(reports_dir))
    reports_by_date = {latest_report["date"]: latest_report}
    for archive_date, payload in _load_archive_payloads(archives_dir):
        report = _normalize_report(payload, archive_date=archive_date)
        existing = reports_by_date.get(report["date"])
        if not existing:
            reports_by_date[report["date"]] = report
            continue
        report_priority = PUBLICATION_PRIORITY.get(str(report["publication_mode"]), 0)
        existing_priority = PUBLICATION_PRIORITY.get(str(existing["publication_mode"]), 0)
        if report_priority > existing_priority or (
            report_priority == existing_priority
            and _parse_dt(str(report["generated_at"])) > _parse_dt(str(existing["generated_at"]))
        ):
            reports_by_date[report["date"]] = report

    return sorted(reports_by_date.values(), key=lambda item: str(item["generated_at"]), reverse=True)


def _build_weekly_reports(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[str, list[dict[str, object]]] = {}
    for report in reports:
        report_date = _parse_date(str(report["date"]))
        iso_year, iso_week, _ = report_date.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        buckets.setdefault(week_key, []).append(report)

    weekly_reports: list[dict[str, object]] = []
    for week_key, items in buckets.items():
        week_reports = sorted(items, key=lambda item: str(item["date"]), reverse=True)
        domain_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        signal_lookup: dict[str, dict[str, object]] = {}
        for report in week_reports:
            domain_counts.update(report["domain_counts"])
            source_counts.update(report["source_counts"])
            for signal in report["signals"]:
                signal_key = f"{signal['title']}|{signal['url']}"
                if signal_key not in signal_lookup:
                    signal_lookup[signal_key] = {
                        **signal,
                        "appearances": 1,
                        "publication_mode": report["publication_mode"],
                        "publication_label": report["publication_label"],
                        "review": report["review"],
                    }
                    continue
                signal_lookup[signal_key]["appearances"] = int(signal_lookup[signal_key]["appearances"]) + 1

        top_signals = sorted(
            signal_lookup.values(),
            key=lambda item: (-float(item["score"]), item["title"]),
        )[:8]
        persistent_mainlines = sorted(
            signal_lookup.values(),
            key=lambda item: (-int(item.get("appearances", 0)), -float(item.get("score", 0.0)), item["title"]),
        )[:4]
        start_date = min(_parse_date(str(report["date"])) for report in week_reports)
        end_date = max(_parse_date(str(report["date"])) for report in week_reports)
        weekly_reports.append(
            {
                "week_key": week_key,
                "week_label": week_key,
                "range_label": f"{_format_date(start_date.isoformat())} - {_format_date(end_date.isoformat())}",
                "report_count": len(week_reports),
                "total_items": sum(int(report["total_items"]) for report in week_reports),
                "total_topics": sum(int(report["total_topics"]) for report in week_reports),
                "domain_counts": dict(domain_counts.most_common()),
                "source_counts": dict(source_counts.most_common()),
                "reports": week_reports,
                "top_signals": top_signals,
                "persistent_mainlines": persistent_mainlines,
                "archive_url": f"weekly/{week_key}/",
                "generated_at": week_reports[0]["generated_at"],
            }
        )

    return sorted(weekly_reports, key=lambda item: item["week_key"], reverse=True)


def _build_special_collections(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    definitions = [
        (
            "verified",
            "已验证主线",
            "聚合跨日持续和多源印证后已经形成确认主线的主题。",
            lambda signal: str(signal.get("lifecycle_state", "new")) == "verified",
        ),
        (
            "emerging",
            "新兴主题",
            "聚合仍在抬升中的新主题，方便提前观察后续是否进入持续主线。",
            lambda signal: str(signal.get("lifecycle_state", "new")) in {"new", "rising"},
        ),
        (
            "risk-watch",
            "风险观察",
            "聚合当前仍需要继续盯防和人工复核的高风险主题。",
            lambda signal: str(signal.get("risk_level", "low")) == "high",
        ),
    ]

    collections: list[dict[str, object]] = []
    for slug, title, description, predicate in definitions:
        entry_map: dict[str, dict[str, object]] = {}
        for report in reports:
            for signal in report["signals"]:
                if not predicate(signal):
                    continue
                key = f"{signal['title']}|{signal['url']}"
                entry = entry_map.get(key)
                if not entry:
                    entry_map[key] = {
                        "title": signal["title"],
                        "url": signal["url"],
                        "summary": signal["summary"],
                        "domain_label": signal["domain_label"],
                        "source": signal["source"],
                        "score": signal["score"],
                        "lifecycle_state": signal["lifecycle_state"],
                        "risk_level": signal["risk_level"],
                        "enrichment_summary": signal["enrichment_summary"],
                        "first_date": report["date"],
                        "last_date": report["date"],
                        "appearances": 1,
                        "archive_url": report["archive_url"],
                        "publication_mode": report["publication_mode"],
                        "publication_label": report["publication_label"],
                        "review": report["review"],
                    }
                    continue

                entry["appearances"] = int(entry["appearances"]) + 1
                if str(report["date"]) > str(entry["last_date"]):
                    entry["last_date"] = report["date"]
                    entry["summary"] = signal["summary"]
                    entry["score"] = signal["score"]
                    entry["lifecycle_state"] = signal["lifecycle_state"]
                    entry["risk_level"] = signal["risk_level"]
                    entry["enrichment_summary"] = signal["enrichment_summary"]
                    entry["archive_url"] = report["archive_url"]
                    entry["publication_mode"] = report["publication_mode"]
                    entry["publication_label"] = report["publication_label"]
                    entry["review"] = report["review"]
                if str(report["date"]) < str(entry["first_date"]):
                    entry["first_date"] = report["date"]

        entries = sorted(
            entry_map.values(),
            key=lambda item: (-int(item["appearances"]), -float(item["score"]), str(item["title"])),
        )
        collections.append(
            {
                "slug": slug,
                "title": title,
                "description": description,
                "entries": entries,
                "entry_count": len(entries),
                "archive_url": f"special/{slug}/",
            }
        )
    return collections


def _slugify(value: object) -> str:
    raw = _safe_text(value).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    if slug:
        return slug
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"track-{digest}"


def _build_track_summaries(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for report in reports:
        seen_in_report: set[str] = set()
        for signal in report["signals"]:
            track_key = _safe_text(signal.get("domain")) or _safe_text(signal.get("domain_label"))
            track_name = _safe_text(signal.get("domain_label")) or _domain_label(track_key)
            if not track_key or track_key in seen_in_report:
                continue
            seen_in_report.add(track_key)
            row = summaries.setdefault(
                track_key,
                {
                    "key": track_key,
                    "name": track_name,
                    "count": 0,
                    "latest_date": str(report["date"]),
                    "latest_title": str(report["judgment"]),
                    "archive_url": f"tracks/{_slugify(track_key)}/",
                },
            )
            row["count"] = int(row["count"]) + int(report["domain_counts"].get(track_name, 1))
            if str(report["date"]) > str(row["latest_date"]):
                row["latest_date"] = str(report["date"])
                row["latest_title"] = str(report["judgment"])
    return sorted(summaries.values(), key=lambda item: (-int(item["count"]), str(item["name"])))


def _search_result_tags(signal: dict[str, object]) -> list[str]:
    seen = {_safe_text(signal.get("domain_label")), _safe_text(signal.get("source"))}
    tags: list[str] = []
    for tag in signal.get("tags", []):
        label = _tag_label(tag)
        if not label or label in seen:
            continue
        seen.add(label)
        tags.append(label)
    return tags


def _build_search_index(reports: list[dict[str, object]]) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for report in reports:
        for index, signal in enumerate(report["signals"]):
            entries.append(
                {
                    "id": f"{report['date']}-{index}",
                    "date": report["date"],
                    "generated_at": report["generated_at"],
                    "title": signal["title"],
                    "summary": signal["summary"],
                    "domain": signal["domain_label"],
                    "source": signal["source"],
                    "tags": _search_result_tags(signal),
                    "raw_tags": signal["tags"],
                    "url": signal["url"],
                    "article_url": signal["article_url"],
                    "archive_url": report["archive_url"],
                    "publication_mode": report["publication_mode"],
                    "score": signal["score"],
                }
            )
    return {
        "meta": {
            "generated_at": reports[0]["generated_at"] if reports else "",
            "entry_count": len(entries),
        },
        "entries": entries,
    }


def _build_json_feed(reports: list[dict[str, object]]) -> dict[str, object]:
    items = []
    for report in reports:
        summary = " ".join(report["executive_summary"]) or report["judgment"]
        items.append(
            {
                "id": f"{SITE_URL}/{report['archive_url']}",
                "url": f"{SITE_URL}/{report['archive_url']}",
                "title": report["judgment"],
                "content_text": summary,
                "date_published": report["generated_at"],
                "tags": list(report["domain_counts"].keys()),
            }
        )
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": SITE_TITLE,
        "home_page_url": SITE_URL,
        "feed_url": f"{SITE_URL}/feed.json",
        "description": SITE_DESCRIPTION,
        "items": items,
    }


def _build_rss(reports: list[dict[str, object]]) -> str:
    items: list[str] = []
    for report in reports:
        summary = " ".join(report["executive_summary"]) or report["judgment"]
        items.append(
            f"""<item>
  <title>{xml_escape(report["judgment"])}</title>
  <link>{xml_escape(f"{SITE_URL}/{report['archive_url']}")}</link>
  <guid>{xml_escape(f"{SITE_URL}/{report['archive_url']}")}</guid>
  <pubDate>{_parse_dt(str(report["generated_at"])).strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
  <description>{xml_escape(summary)}</description>
</item>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{xml_escape(SITE_TITLE)}</title>
  <link>{xml_escape(SITE_URL)}</link>
  <description>{xml_escape(SITE_DESCRIPTION)}</description>
  {''.join(items)}
</channel>
</rss>
"""


def _base_css() -> str:
    return """
  :root {
    --bg: #081018;
    --panel: #101a24;
    --panel-strong: #142231;
    --panel-soft: #0c1620;
    --ink: #edf4f7;
    --muted: #9fb0bd;
    --line: rgba(181, 200, 211, 0.18);
    --accent: #43d1bf;
    --accent-soft: rgba(67, 209, 191, 0.12);
    --blue: #8fb8ff;
    --amber: #e9b56f;
    --danger: #f08d8d;
    --shadow: 0 18px 50px rgba(0, 0, 0, 0.26);
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0;
    color: var(--ink);
    background: linear-gradient(180deg, #071019 0%, #0a121b 58%, #071019 100%);
  }
  a { color: inherit; }
  .site-shell { max-width: 1240px; margin: 0 auto; padding: 0 20px 48px; }
  .topbar {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 16px;
    align-items: center;
    padding: 16px 0;
    color: var(--muted);
    font-size: 14px;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    font-weight: 700;
  }
  .brand-mark {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: var(--accent);
    box-shadow: 0 0 18px rgba(67, 209, 191, 0.5);
  }
  .nav-links {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .nav-links a {
    color: var(--muted);
    text-decoration: none;
  }
  .nav-links a:hover { color: var(--ink); }
  .workbench {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
    gap: 16px;
    align-items: stretch;
  }
  .panel,
  .section,
  .stat,
  .signal,
  .article-card,
  .archive-card,
  .summary-card,
  .topic-card,
  .comparison-card,
  .comparison-list,
  .search-hit {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: rgba(16, 26, 36, 0.88);
    box-shadow: var(--shadow);
  }
  .panel { padding: 22px; }
  .section { margin-top: 16px; padding: 22px; }
  .section-title {
    margin: 0 0 14px;
    font-size: 22px;
    line-height: 1.35;
  }
  .page-title {
    margin: 0;
    font-size: 34px;
    line-height: 1.18;
  }
  .eyebrow {
    color: var(--accent);
    font-size: 12px;
    font-weight: 700;
  }
  .subtle { color: var(--muted); }
  .lead {
    margin: 14px 0 0;
    max-width: 820px;
    font-size: 18px;
    line-height: 1.78;
  }
  .compact-list {
    margin: 16px 0 0;
    padding-left: 20px;
    color: var(--muted);
    line-height: 1.72;
  }
  .meta-row,
  .hero-meta,
  .signal-tags,
  .filter-group,
  .archive-meta,
  .feed-links {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .meta-row { margin-top: 16px; }
  .chip,
  .tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 30px;
    padding: 5px 10px;
    border-radius: 999px;
    border: 1px solid rgba(181, 200, 211, 0.16);
    background: rgba(12, 22, 32, 0.88);
    color: var(--muted);
    font-size: 12px;
    text-decoration: none;
  }
  .chip:hover { color: var(--ink); border-color: rgba(67, 209, 191, 0.36); }
  .tag { color: var(--accent); background: var(--accent-soft); }
  .tag.alt { color: var(--blue); background: rgba(143, 184, 255, 0.12); }
  .tag.warm { color: var(--amber); background: rgba(233, 181, 111, 0.12); }
  .tag.danger { color: var(--danger); background: rgba(240, 141, 141, 0.12); }
  .stats-grid,
  .signal-grid,
  .archive-grid,
  .summary-grid,
  .comparison-grid {
    display: grid;
    gap: 12px;
  }
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-grid { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  .signal-grid { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
  .archive-grid { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
  .comparison-grid { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
  .stat,
  .signal,
  .article-card,
  .archive-card,
  .summary-card,
  .topic-card,
  .comparison-card,
  .comparison-list,
  .search-hit {
    padding: 16px;
    box-shadow: none;
  }
  .stat strong {
    display: block;
    margin-top: 6px;
    font-size: 28px;
    line-height: 1;
  }
  .stat span { color: var(--muted); font-size: 13px; }
  .signal h3,
  .article-card h3,
  .archive-card h3,
  .summary-card h3,
  .topic-card h3,
  .comparison-card h3,
  .comparison-list h3 {
    margin: 8px 0 8px;
    font-size: 17px;
    line-height: 1.42;
  }
  .signal p,
  .article-card p,
  .archive-card p,
  .summary-card p,
  .topic-card p,
  .comparison-card p,
  .comparison-list p {
    margin: 0;
    color: var(--muted);
    line-height: 1.72;
  }
  .comparison-card dl {
    display: grid;
    gap: 8px;
    margin: 12px 0 0;
  }
  .comparison-card dt { color: var(--accent); font-size: 13px; font-weight: 700; }
  .comparison-card dd { margin: 0; color: var(--muted); line-height: 1.68; }
  .comparison-list ul { margin: 10px 0 0; padding-left: 18px; color: var(--muted); line-height: 1.72; }
  .article-card {
    display: flex;
    flex-direction: column;
    min-height: 188px;
  }
  .article-date {
    margin: 0 0 10px;
    color: var(--muted);
    font-size: 13px;
  }
  .article-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    align-self: flex-start;
    min-height: 34px;
    margin-top: 14px;
    padding: 7px 13px;
    border-radius: 999px;
    border: 1px solid rgba(67, 209, 191, 0.34);
    background: var(--accent-soft);
    color: var(--ink);
    font-size: 13px;
    text-decoration: none;
  }
  .article-action:hover {
    border-color: rgba(67, 209, 191, 0.64);
    color: var(--accent);
  }
  .signal-footer,
  .archive-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-top: 14px;
    color: var(--muted);
    font-size: 13px;
  }
  .signal a,
  .article-card a,
  .archive-card a,
  .feed-links a {
    text-decoration: none;
  }
  .signal a:hover,
  .article-card a:hover,
  .archive-card a:hover,
  .feed-links a:hover {
    color: var(--accent);
  }
  .search-shell { display: grid; gap: 14px; }
  .search-shell input {
    width: 100%;
    padding: 12px 14px;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: var(--panel-soft);
    color: var(--ink);
    font: inherit;
  }
  .filter-search {
    width: 100%;
    max-width: 360px;
    margin: 0 0 10px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: var(--panel-soft);
    color: var(--ink);
    font: inherit;
  }
  .search-results { display: grid; gap: 10px; }
  .feed-links { margin-top: 14px; }
  .archive-filters { display: grid; gap: 14px; margin-bottom: 16px; }
  .filter-group button {
    padding: 8px 12px;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--muted);
    font: inherit;
    cursor: pointer;
  }
  .filter-group button.is-active,
  .filter-group button:hover {
    color: var(--ink);
    border-color: rgba(67, 209, 191, 0.4);
    background: var(--accent-soft);
  }
  .footer {
    margin-top: 18px;
    padding: 18px 0 6px;
    color: var(--muted);
    text-align: center;
    font-size: 13px;
  }
  @media (max-width: 880px) {
    .site-shell { padding: 0 14px 36px; }
    .topbar { grid-template-columns: 1fr; gap: 10px; }
    .nav-links { justify-content: flex-start; }
    .workbench { grid-template-columns: 1fr; }
    .panel, .section { padding: 18px; }
    .page-title { font-size: 28px; }
    .lead { font-size: 16px; }
    .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .signal-footer,
    .archive-footer {
      align-items: flex-start;
      flex-direction: column;
    }
  }
  @media (max-width: 420px) {
    .stats-grid { grid-template-columns: 1fr; }
    .nav-links { gap: 10px; }
  }
"""


def _summary_cards(report: dict[str, object]) -> str:
    cards = []
    for line in report["mainlines"]:
        cards.append(
            f"""<article class="summary-card">
  <h3>{html.escape(_localize_known_text(line["title"]))}</h3>
  <p>{html.escape(_localize_known_text(line["why_it_matters"]))}</p>
</article>"""
        )
    return "".join(cards) or '<article class="summary-card"><h3>暂无主线</h3><p>等待更多高置信度信号。</p></article>'


def _review_meta_tags(publication_label: str, review: dict[str, str] | None) -> str:
    review = review or {}
    tags = [f'<span class="tag">{html.escape(publication_label)}</span>']
    reviewer = _safe_text(review.get("reviewer"))
    if reviewer:
        tags.append(f'<span class="tag alt">{html.escape(reviewer)}</span>')
    review_note = _safe_text(review.get("review_note"))
    if review_note:
        tags.append(f'<span class="tag warm">{html.escape(review_note)}</span>')
    return "".join(tags)


def _topic_cards(report: dict[str, object]) -> str:
    cards = []
    for topic in report["topic_briefs"]:
        cards.append(
            f"""<article class="topic-card">
  <h3>{html.escape(_localize_known_text(topic["title"]))}</h3>
  <p>{html.escape(_localize_known_text(topic["core_insight"]))}</p>
  <div class="archive-meta" style="margin-top:12px;">
    <span class="tag alt">{html.escape(_domain_label(topic["primary_domain"]))}</span>
    <span class="tag warm">{html.escape(topic["confidence"])}</span>
  </div>
</article>"""
        )
    return "".join(cards) or '<article class="topic-card"><h3>暂无重点分析</h3><p>等待下一轮信号收敛。</p></article>'


def _tag_chips(tags: object, limit: int = 4) -> str:
    if not isinstance(tags, list):
        return ""
    labels: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        label = _tag_label(tag)
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
        if len(labels) >= limit:
            break
    return "".join(f'<span class="tag">{html.escape(label)}</span>' for label in labels)


def _article_card(
    title: object,
    date_label: object,
    tags: object,
    article_url: object,
    link_prefix: str,
    button_label: str = "阅读文章",
) -> str:
    tag_html = _tag_chips(tags)
    return f"""<article class="article-card">
  <p class="article-date">{html.escape(_safe_text(date_label))}</p>
  <h3>{html.escape(_localize_known_text(title))}</h3>
  <div class="archive-meta" style="margin-top:12px;">{tag_html}</div>
  <a class="article-action" href="{html.escape(_href(article_url, link_prefix))}">{html.escape(button_label)}</a>
</article>"""


def _signal_cards(signals: list[dict[str, object]], link_prefix: str = "./") -> str:
    cards = []
    for signal in signals:
        tags = [signal["domain_label"], signal["source"], *signal["tags"]]
        cards.append(
            _article_card(
                signal["title"],
                signal.get("date_label", ""),
                tags,
                signal.get("article_url", signal.get("url", "")),
                link_prefix,
            )
        )
    return "".join(cards) or '<article class="article-card"><h3>暂无信号</h3><p>等待下一次构建。</p></article>'


def _archive_cards(reports: list[dict[str, object]], link_prefix: str = "./") -> str:
    cards = []
    for report in reports:
        tags = [*list(report["domain_counts"].keys())[:2], report["publication_label"]]
        cards.append(
            _article_card(
                report["judgment"],
                report["date_label"],
                tags,
                report.get("brief_url", report["archive_url"]),
                link_prefix,
            ).replace(
                '<article class="article-card">',
                f'<article class="article-card" data-domain="{" ".join(report["domain_counts"].keys())}" data-source="{" ".join(report["source_counts"].keys())}">',
            )
        )
    return "".join(cards)


def _track_summary_cards(tracks: list[dict[str, object]], link_prefix: str = "./") -> str:
    cards = []
    for track in tracks:
        cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">赛道</span>
  <h3>{html.escape(str(track["name"]))}</h3>
  <p>{int(track["count"])} 条信号 · 最近 {_format_date(str(track["latest_date"]))}</p>
  <div class="archive-footer">
    <span>{html.escape(str(track["latest_title"]))}</span>
    <a href="{html.escape(_href(track["archive_url"], link_prefix))}">打开赛道</a>
  </div>
</article>"""
        )
    return "".join(cards) or '<article class="archive-card"><h3>暂无赛道</h3><p>等待下一次日报生成。</p></article>'


def _weekly_cards(weeks: list[dict[str, object]]) -> str:
    cards = []
    for week in weeks:
        domain_tags = "".join(
            f'<span class="tag alt">{html.escape(name)}</span>'
            for name in list(week["domain_counts"].keys())[:2]
        )
        lead_report = week["reports"][0]
        review_tags = _review_meta_tags(str(lead_report["publication_label"]), lead_report.get("review", {}))
        cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">{html.escape(week["week_label"])}</span>
  <h3>{html.escape(week["range_label"])}</h3>
  <p>{week["report_count"]} 份日报 · {week["total_topics"]} 个主题 · {week["total_items"]} 条原始信息</p>
  <div class="archive-meta" style="margin-top:12px;">{domain_tags}{review_tags}</div>
  <div class="archive-footer">
    <span>{html.escape(week["reports"][0]["judgment"])}</span>
    <a href="{html.escape(week["archive_url"])}">打开周报</a>
  </div>
</article>"""
        )
    return "".join(cards)


def _special_collection_cards(collections: list[dict[str, object]]) -> str:
    cards = []
    for collection in collections:
        cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">{html.escape(collection["title"])}</span>
  <h3>{collection["entry_count"]} 个聚合主题</h3>
  <p>{html.escape(collection["description"])}</p>
  <div class="archive-footer">
    <span>专题聚合页</span>
    <a href="{html.escape(collection["archive_url"])}">打开专题</a>
  </div>
</article>"""
        )
    return "".join(cards)


def _special_signal_cards(entries: list[dict[str, object]]) -> str:
    cards = []
    for item in entries:
        review_tags = _review_meta_tags(str(item["publication_label"]), item.get("review", {}))
        cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">{html.escape(_format_date(str(item["last_date"])))}</span>
  <h3>{html.escape(item["title"])}</h3>
  <p>{html.escape(item["summary"])}</p>
  <div class="archive-meta" style="margin-top:12px;">
    <span class="tag alt">{html.escape(item["domain_label"])}</span>
    <span class="tag warm">{html.escape(str(item["lifecycle_state"]))}</span>
    <span class="tag">{html.escape(str(item["risk_level"]))}</span>
    {review_tags}
  </div>
  <p class="subtle" style="margin-top:12px;">{html.escape(str(item["enrichment_summary"]))}</p>
  <div class="archive-footer">
    <span>出现 {item["appearances"]} 次 · {_format_date(str(item["first_date"]))} → {_format_date(str(item["last_date"]))}</span>
    <a href="{html.escape(item["archive_url"])}">打开日报</a>
  </div>
</article>"""
        )
    return "".join(cards) or '<article class="archive-card"><h3>暂无专题主题</h3><p>等待后续日报累积更多信号。</p></article>'


def _comparison_highlight_list(title: str, items: list[dict[str, str]]) -> str:
    if not items:
        return ""
    rows = "".join(
        f"""<li>
  <strong>{html.escape(item["title"])}</strong>
  {f'<span class="tag alt">{html.escape(item["meta"])}</span>' if item["meta"] else ""}
  {f'<p>{html.escape(item["summary"])}</p>' if item["summary"] else ""}
</li>"""
        for item in items[:3]
    )
    return f"""<article class="comparison-list">
  <h3>{html.escape(title)}</h3>
  <ul>{rows}</ul>
</article>"""


def _comparison_row_cards(rows: list[dict[str, str]]) -> str:
    cards = []
    for row in rows[:3]:
        delta = f'<dt>差异</dt><dd>{html.escape(row["delta"])}</dd>' if row["delta"] else ""
        delta_line = f"\n    {delta}" if delta else ""
        cards.append(
            f"""<article class="comparison-card">
  <span class="tag">{html.escape(row["track"])}</span>
  <dl>
    <dt>国内侧</dt><dd>{html.escape(row["cn"])}</dd>
    <dt>海外侧</dt><dd>{html.escape(row["intl"])}</dd>{delta_line}
  </dl>
</article>"""
        )
    return "".join(cards)


def _comparison_bullet_list(title: str, items: list[str], tag_class: str = "warm") -> str:
    if not items:
        return ""
    rows = "".join(f"<li>{html.escape(item)}</li>" for item in items[:4])
    return f"""<article class="comparison-list">
  <h3><span class="tag {tag_class}">{html.escape(title)}</span></h3>
  <ul>{rows}</ul>
</article>"""


def _comparison_section(comparison: object, compact: bool = False) -> str:
    if not _has_comparison_content(comparison):
        return ""
    assert isinstance(comparison, dict)
    rows = comparison.get("head_to_head", [])
    cn_highlights = comparison.get("cn_highlights", [])
    intl_highlights = comparison.get("intl_highlights", [])
    gaps = comparison.get("gaps", [])
    watchpoints = comparison.get("watchpoints", [])
    if compact:
        content = _comparison_row_cards(rows if isinstance(rows, list) else [])
        if not content:
            content = _comparison_highlight_list("国内信号", cn_highlights if isinstance(cn_highlights, list) else [])
            content += _comparison_highlight_list("海外信号", intl_highlights if isinstance(intl_highlights, list) else [])
        content += _comparison_bullet_list("覆盖缺口", gaps if isinstance(gaps, list) else [], "danger")
        content += _comparison_bullet_list("观察点", watchpoints if isinstance(watchpoints, list) else [], "warm")
        return f"""<section class="section">
      <h2 class="section-title">国内外对比</h2>
      <div class="comparison-grid">{content}</div>
    </section>"""

    content = _comparison_row_cards(rows if isinstance(rows, list) else [])
    content += _comparison_highlight_list("国内信号", cn_highlights if isinstance(cn_highlights, list) else [])
    content += _comparison_highlight_list("海外信号", intl_highlights if isinstance(intl_highlights, list) else [])
    content += _comparison_bullet_list("覆盖缺口", gaps if isinstance(gaps, list) else [], "danger")
    content += _comparison_bullet_list("观察点", watchpoints if isinstance(watchpoints, list) else [], "warm")
    return f"""<section class="section">
      <h2 class="section-title">国内外对比</h2>
      <div class="comparison-grid">{content}</div>
    </section>"""


def _build_signal_article_page(report: dict[str, object], signal: dict[str, object]) -> str:
    tags = [signal["domain_label"], signal["source"], *signal["tags"]]
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(str(signal["title"]))} | VS_AI 文章</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../../../assets/site.css">
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../../../../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../../">返回日报</a>
        <a href="../../../../archives/">归档</a>
        <a href="../../../../tracks/">赛道</a>
        <a href="../../../../weekly/">周报</a>
        <a href="../../../../special/">专题</a>
      </nav>
    </header>

    <section class="panel">
      <div class="eyebrow">文章</div>
      <p class="article-date">{html.escape(str(report["date_label"]))}</p>
      <h1 class="page-title">{html.escape(str(signal["title"]))}</h1>
      <div class="archive-meta" style="margin-top:16px;">{_tag_chips(tags)}</div>
      <a class="article-action" href="{html.escape(str(signal["url"]))}" target="_blank" rel="noopener">查看正文</a>
    </section>
  </div>
</body>
</html>
"""


def _build_report_teaser_page(report: dict[str, object]) -> str:
    tags = [*list(report["domain_counts"].keys())[:3], report["publication_label"]]
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(str(report["judgment"]))} | VS_AI 日报</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../../assets/site.css">
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../../../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">返回正文</a>
        <a href="../../../archives/">归档</a>
        <a href="../../../tracks/">赛道</a>
        <a href="../../../weekly/">周报</a>
        <a href="../../../special/">专题</a>
      </nav>
    </header>

    <section class="panel">
      <div class="eyebrow">日报文章</div>
      <p class="article-date">{html.escape(str(report["date_label"]))}</p>
      <h1 class="page-title">{html.escape(str(report["judgment"]))}</h1>
      <div class="archive-meta" style="margin-top:16px;">{_tag_chips(tags)}</div>
      <a class="article-action" href="../">查看正文</a>
    </section>
  </div>
</body>
</html>
"""


def _build_homepage(
    report: dict[str, object],
    reports: list[dict[str, object]],
    track_summaries: list[dict[str, object]],
) -> str:
    recent_archives = reports[:6]
    featured_tracks = track_summaries[:4]
    comparison_html = _comparison_section(report.get("comparison_brief", {}), compact=True)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(SITE_TITLE)}</title>
<meta name="description" content="{html.escape(report["judgment"])}">
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="./"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="./archives/">归档</a>
        <a href="./tracks/">赛道</a>
        <a href="./weekly/">周报</a>
        <a href="./special/">专题</a>
        <a href="./feed.json">JSON</a>
        <a href="./rss.xml">订阅</a>
        <a href="https://github.com/wsysgz/VS_AI" target="_blank" rel="noopener">仓库</a>
      </nav>
    </header>

    <section class="workbench">
      <article class="panel">
        <div class="eyebrow">情报工作台</div>
        <h1 class="page-title">今日判断</h1>
        <p class="lead">{html.escape(report["judgment"])}</p>
        <ul class="compact-list">
          {"".join(f"<li>{html.escape(item)}</li>" for item in report["executive_summary"][:3])}
        </ul>
        <div class="meta-row">
          <span class="chip">最新更新 {html.escape(report["generated_at"])}</span>
          <span class="chip">{html.escape(report["publication_label"])}</span>
          <a class="chip" href="./archives/">归档检索</a>
          <a class="chip" href="./tracks/">赛道</a>
          <a class="chip" href="./weekly/">周报</a>
          <a class="chip" href="./special/">专题</a>
        </div>
      </article>
      <aside class="panel">
        <h2 class="section-title">覆盖状态</h2>
        <div class="stats-grid">
          <article class="stat"><span>原始条目</span><strong>{report["total_items"]}</strong></article>
          <article class="stat"><span>主题数量</span><strong>{report["total_topics"]}</strong></article>
          <article class="stat"><span>领域覆盖</span><strong>{len(report["domain_counts"])}</strong></article>
          <article class="stat"><span>来源数量</span><strong>{len(report["source_counts"])}</strong></article>
        </div>
        <p class="subtle" style="margin-top:14px;">{html.escape(report["watchlist"])}</p>
      </aside>
    </section>

{comparison_html}

    <section class="section">
      <h2 class="section-title">赛道</h2>
      <div class="archive-grid">
        {_track_summary_cards(featured_tracks, link_prefix="./")}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">关键主线</h2>
      <div class="summary-grid">
        {_summary_cards(report)}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">重点信号</h2>
      <div class="signal-grid">
        {_signal_cards(report["top_signals"], link_prefix="./")}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">检索</h2>
      <div class="search-shell">
        <p class="subtle">基础检索覆盖标题、标签、领域、来源，索引来自 <code>search-index.json</code>。</p>
        <input id="site-search" type="search" placeholder="搜索标题、标签、领域、来源">
        <div id="search-results" class="search-results"></div>
      </div>
      <div class="feed-links">
        <a class="chip" href="./search-index.json">search-index.json</a>
        <a class="chip" href="./feed.json">feed.json</a>
        <a class="chip" href="./rss.xml">rss.xml</a>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">最近归档</h2>
      <div class="archive-grid">
        {_archive_cards(recent_archives, link_prefix="./")}
      </div>
    </section>

    <footer class="footer">
      <p>公开站只展示可公开阅读内容；运维诊断保留在私有看板。</p>
    </footer>
  </div>

  <script>
    (async function() {{
      const input = document.getElementById("site-search");
      const results = document.getElementById("search-results");
      const response = await fetch("./search-index.json");
      const payload = await response.json();
      const entries = payload.entries || [];

      function escapeHtml(value) {{
        return String(value || "").replace(/[&<>"']/g, (char) => ({{
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;"
        }}[char] || char));
      }}

      function safeSearchHref(value) {{
        const text = String(value || "").trim();
        if (!text) {{
          return "#";
        }}
        if (text.startsWith("archives/") || text.startsWith("weekly/") || text.startsWith("special/")) {{
          return `./${{text}}`;
        }}
        if (text.startsWith("./") || text.startsWith("../") || text.startsWith("#")) {{
          return text;
        }}
        if (text.startsWith("http://") || text.startsWith("https://")) {{
          return text;
        }}
        return "#";
      }}

      function render(list) {{
        if (!list.length) {{
          results.innerHTML = '<div class="search-hit"><h4>暂无结果</h4><p>换一个关键词试试。</p></div>';
          return;
        }}
        results.innerHTML = list.slice(0, 8).map((entry) => {{
          const tags = [entry.domain, entry.source, ...(entry.tags || [])].filter(Boolean).slice(0, 4).map((tag) => `<span class="tag">${{escapeHtml(tag)}}</span>`).join("");
          const articleUrl = entry.article_url || entry.archive_url || entry.url;
          return `
            <article class="article-card search-hit">
              <p class="article-date">${{escapeHtml(entry.date || "")}}</p>
              <h3>${{escapeHtml(entry.title || "")}}</h3>
              <div class="archive-meta" style="margin-top:10px;">${{tags}}</div>
              <a class="article-action" href="${{escapeHtml(safeSearchHref(articleUrl))}}">阅读文章</a>
            </article>
          `;
        }}).join("");
      }}

      render(entries.slice(0, 6));
      input.addEventListener("input", () => {{
        const query = input.value.trim().toLowerCase();
        if (!query) {{
          render(entries.slice(0, 6));
          return;
        }}
        const filtered = entries.filter((entry) => {{
          const haystack = [
            entry.title,
            entry.summary,
            entry.domain,
            entry.source,
            ...(entry.tags || [])
          ].join(" ").toLowerCase();
          return haystack.includes(query);
        }});
        render(filtered);
      }});
    }})();
  </script>
</body>
</html>
"""


def _build_archives_index(reports: list[dict[str, object]]) -> str:
    all_domains = sorted({domain for report in reports for domain in report["domain_counts"].keys()})
    all_sources = sorted({source for report in reports for source in report["source_counts"].keys()})
    domain_buttons = "".join(
        f'<button type="button" data-kind="domain" data-value="{html.escape(value)}">{html.escape(value)}</button>'
        for value in all_domains
    )
    source_buttons = "".join(
        f'<button type="button" data-kind="source" data-value="{html.escape(value)}">{html.escape(value)}</button>'
        for value in all_sources
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VS_AI 归档</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">首页</a>
        <a href="../tracks/">赛道</a>
        <a href="../weekly/">周报</a>
        <a href="../special/">专题</a>
        <a href="../feed.json">JSON</a>
        <a href="../rss.xml">订阅</a>
      </nav>
    </header>

    <section class="section">
      <h1 class="section-title">归档</h1>
      <p class="subtle">按日期、领域、来源浏览过去的每日情报摘要。</p>
    </section>

    <section class="section archive-filters">
      <div>
        <h2 class="section-title">按领域浏览</h2>
        <div class="filter-group">
          <button type="button" class="is-active" data-kind="domain" data-value="">全部</button>
          {domain_buttons}
        </div>
      </div>
      <div>
        <h2 class="section-title">按来源浏览</h2>
        <input id="source-filter-search" class="filter-search" type="search" placeholder="筛选来源">
        <div class="filter-group">
          <button type="button" class="is-active" data-kind="source" data-value="">全部</button>
          {source_buttons}
        </div>
      </div>
    </section>

    <section class="section">
      <div id="archive-grid" class="archive-grid">
        {_archive_cards(reports, link_prefix="../")}
      </div>
    </section>
  </div>

  <script>
    const archiveCards = [...document.querySelectorAll(".archive-card")];
    const sourceFilterSearch = document.getElementById("source-filter-search");
    const filters = {{ domain: "", source: "" }};
    if (sourceFilterSearch) {{
      sourceFilterSearch.addEventListener("input", () => {{
        const query = sourceFilterSearch.value.trim().toLowerCase();
        document.querySelectorAll('button[data-kind="source"]').forEach((button) => {{
          const value = (button.dataset.value || button.textContent || "").toLowerCase();
          button.style.display = !query || !button.dataset.value || value.includes(query) ? "" : "none";
        }});
      }});
    }}
    document.querySelectorAll(".filter-group button").forEach((button) => {{
      button.addEventListener("click", () => {{
        const kind = button.dataset.kind;
        filters[kind] = button.dataset.value || "";
        document.querySelectorAll(`button[data-kind="${{kind}}"]`).forEach((item) => item.classList.remove("is-active"));
        button.classList.add("is-active");
        archiveCards.forEach((card) => {{
          const domainOk = !filters.domain || (card.dataset.domain || "").includes(filters.domain);
          const sourceOk = !filters.source || (card.dataset.source || "").includes(filters.source);
          card.style.display = domainOk && sourceOk ? "" : "none";
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def _build_tracks_index(track_summaries: list[dict[str, object]]) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VS_AI 赛道</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">首页</a>
        <a href="../archives/">归档</a>
        <a href="../weekly/">周报</a>
        <a href="../special/">专题</a>
        <a href="../feed.json">JSON</a>
      </nav>
    </header>

    <section class="section">
      <h1 class="section-title">赛道</h1>
      <p class="subtle">按技术方向聚合日报信号，先看赛道，再回到日期和来源。</p>
    </section>

    <section class="section">
      <div class="archive-grid">
        {_track_summary_cards(track_summaries, link_prefix="../")}
      </div>
    </section>
  </div>
</body>
</html>
"""


def _signal_matches_track(signal: dict[str, object], track: dict[str, object]) -> bool:
    track_key = _safe_text(track.get("key"))
    track_name = _safe_text(track.get("name"))
    return _safe_text(signal.get("domain")) == track_key or _safe_text(signal.get("domain_label")) == track_name


def _reports_for_track(track: dict[str, object], reports: list[dict[str, object]]) -> list[dict[str, object]]:
    return [report for report in reports if any(_signal_matches_track(signal, track) for signal in report["signals"])]


def _signals_for_track(track: dict[str, object], reports: list[dict[str, object]]) -> list[dict[str, object]]:
    signal_map: dict[str, dict[str, object]] = {}
    for report in reports:
        for signal in report["signals"]:
            if not _signal_matches_track(signal, track):
                continue
            key = f"{signal['title']}|{signal['url']}"
            signal_map.setdefault(key, signal)
    return sorted(
        signal_map.values(),
        key=lambda item: (str(item.get("date", "")), float(item.get("score", 0.0))),
        reverse=True,
    )[:8]


def _build_track_page(track: dict[str, object], reports: list[dict[str, object]]) -> str:
    track_reports = _reports_for_track(track, reports)
    track_signals = _signals_for_track(track, reports)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(str(track["name"]))} | VS_AI 赛道</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">赛道</a>
        <a href="../../archives/">归档</a>
        <a href="../../weekly/">周报</a>
        <a href="../../special/">专题</a>
        <a href="../../">首页</a>
      </nav>
    </header>

    <section class="section">
      <div class="eyebrow">赛道</div>
      <h1 class="section-title" style="font-size:34px;">{html.escape(str(track["name"]))}</h1>
      <p class="subtle">{int(track["count"])} 条信号 · 最近 {_format_date(str(track["latest_date"]))}</p>
    </section>

    <section class="section">
      <h2 class="section-title">最近日报</h2>
      <div class="archive-grid">
        {_archive_cards(track_reports[:8], link_prefix="../../")}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">重点信号</h2>
      <div class="signal-grid">
        {_signal_cards(track_signals, link_prefix="../../")}
      </div>
    </section>
  </div>
</body>
</html>
"""


def _build_day_page(report: dict[str, object]) -> str:
    comparison_html = _comparison_section(report.get("comparison_brief", {}))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(report["date_label"])} | VS_AI</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">归档</a>
        <a href="../../tracks/">赛道</a>
        <a href="../../weekly/">周报</a>
        <a href="../../special/">专题</a>
        <a href="../../">首页</a>
      </nav>
    </header>

    <section class="section">
      <div class="eyebrow">{html.escape(report["date_label"])}</div>
      <h1 class="section-title" style="font-size:34px;">{html.escape(report["judgment"])}</h1>
      <p class="subtle">{html.escape(" ".join(report["executive_summary"]) or report["watchlist"])}</p>
      <div class="archive-meta" style="margin-top:14px;">
        <span class="tag alt">{report["total_topics"]} 个主题</span>
        <span class="tag warm">{report["total_items"]} 条原始信息</span>
        <span class="tag">{html.escape(report["publication_label"])}</span>
        <span class="tag">{html.escape(report["generated_at"])}</span>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">关键主线</h2>
      <div class="summary-grid">
        {_summary_cards(report)}
      </div>
    </section>

{comparison_html}

    <section class="section">
      <h2 class="section-title">深度解读</h2>
      <div class="summary-grid">
        {_topic_cards(report)}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">全部信号</h2>
      <div class="signal-grid">
        {_signal_cards(report["signals"], link_prefix="../../")}
      </div>
    </section>
  </div>
</body>
</html>
"""


def _build_weekly_index(weeks: list[dict[str, object]]) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VS_AI 周报</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">首页</a>
        <a href="../archives/">归档</a>
        <a href="../tracks/">赛道</a>
        <a href="../special/">专题</a>
        <a href="../feed.json">JSON</a>
      </nav>
    </header>

    <section class="section">
      <h1 class="section-title">周报</h1>
      <p class="subtle">按周聚合过去的日报，帮助快速回看一周内延续的主线和高分信号。</p>
    </section>

    <section class="section">
      <div class="archive-grid">
        {_weekly_cards(weeks)}
      </div>
    </section>
  </div>
</body>
</html>
"""


def _build_week_page(week: dict[str, object]) -> str:
    daily_cards = []
    for report in week["reports"]:
        review_tags = _review_meta_tags(str(report["publication_label"]), report.get("review", {}))
        daily_cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">{html.escape(report["date_label"])}</span>
  <h3>{html.escape(report["judgment"])}</h3>
  <p>{html.escape(" ".join(report["executive_summary"]) or report["watchlist"])}</p>
  <div class="archive-meta" style="margin-top:12px;">{review_tags}</div>
  <div class="archive-footer">
    <span>{report["total_topics"]} 个主题 · {report["total_items"]} 条原始信息</span>
    <a href="../../archives/{html.escape(report["date"])}/">打开日报</a>
  </div>
</article>"""
        )

    mainline_cards = []
    for signal in week.get("persistent_mainlines", []):
        review_tags = _review_meta_tags(str(signal.get("publication_label", "自动版")), signal.get("review", {}))
        mainline_cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">出现 {int(signal.get("appearances", 1))} 次</span>
  <h3>{html.escape(str(signal["title"]))}</h3>
  <p>{html.escape(str(signal["summary"]))}</p>
  <div class="archive-meta" style="margin-top:12px;">
    <span class="tag alt">{html.escape(str(signal["domain_label"]))}</span>
    <span class="tag warm">{html.escape(str(signal["lifecycle_state"]))}</span>
    {review_tags}
  </div>
  <div class="archive-footer">
    <span>评分 {float(signal.get("score", 0.0)):.1f}</span>
    <a href="{html.escape(str(signal["url"]))}" target="_blank" rel="noopener">查看原文</a>
  </div>
</article>"""
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(week["week_label"])} | VS_AI 周报</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">周报</a>
        <a href="../../archives/">归档</a>
        <a href="../../tracks/">赛道</a>
        <a href="../../special/">专题</a>
        <a href="../../">首页</a>
      </nav>
    </header>

    <section class="section">
      <div class="eyebrow">{html.escape(week["week_label"])}</div>
      <h1 class="section-title" style="font-size:34px;">{html.escape(week["range_label"])}</h1>
      <p class="subtle">{week["report_count"]} 份日报 · {week["total_topics"]} 个主题 · {week["total_items"]} 条原始信息</p>
    </section>

    <section class="section">
      <h2 class="section-title">持续主线</h2>
      <div class="archive-grid">
        {"".join(mainline_cards) or '<article class="archive-card"><h3>暂无持续主线</h3><p>等待更多跨日报重复信号。</p></article>'}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">日报流</h2>
      <div class="archive-grid">
        {"".join(daily_cards)}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">重点信号</h2>
      <div class="signal-grid">
        {_signal_cards(week["top_signals"], link_prefix="../../")}
      </div>
    </section>
  </div>
</body>
</html>
"""


def _build_special_index(collections: list[dict[str, object]]) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VS_AI 专题</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">首页</a>
        <a href="../archives/">归档</a>
        <a href="../tracks/">赛道</a>
        <a href="../weekly/">周报</a>
      </nav>
    </header>

    <section class="section">
      <h1 class="section-title">专题</h1>
      <p class="subtle">按“已验证主线”和“高风险观察”聚合跨日报的重点主题，方便长期跟踪。</p>
    </section>

    <section class="section">
      <div class="archive-grid">
        {_special_collection_cards(collections)}
      </div>
    </section>
  </div>
</body>
</html>
"""


def _build_special_page(collection: dict[str, object]) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(collection["title"])} | VS_AI 专题</title>
{FAVICON_LINK}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="../../"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="../">专题</a>
        <a href="../../weekly/">周报</a>
        <a href="../../archives/">归档</a>
        <a href="../../tracks/">赛道</a>
        <a href="../../">首页</a>
      </nav>
    </header>

    <section class="section">
      <div class="eyebrow">{html.escape(collection["title"])}</div>
      <h1 class="section-title" style="font-size:34px;">{collection["entry_count"]} 个聚合主题</h1>
      <p class="subtle">{html.escape(collection["description"])}</p>
    </section>

    <section class="section">
      <div class="archive-grid">
        {_special_signal_cards(collection["entries"])}
      </div>
    </section>
  </div>
</body>
</html>
"""


def build_pages_site(root_dir: Path) -> Path:
    """Build the public reading site under docs/ for GitHub Pages main/docs deployment."""
    reports_dir = root_dir / "data" / "reports"
    archives_dir = root_dir / "data" / "archives"
    dist_dir = root_dir / "docs"
    assets_dist = dist_dir / "assets"
    archives_dist = dist_dir / "archives"
    tracks_dist = dist_dir / "tracks"
    weekly_dist = dist_dir / "weekly"
    special_dist = dist_dir / "special"

    reports = _collect_reports(reports_dir, archives_dir)
    if not reports:
        raise FileNotFoundError("No report payloads available for pages build")
    weekly_reports = _build_weekly_reports(reports)
    special_collections = _build_special_collections(reports)
    track_summaries = _build_track_summaries(reports)

    dist_dir.mkdir(parents=True, exist_ok=True)

    if archives_dist.exists():
        shutil.rmtree(archives_dist)
    if tracks_dist.exists():
        shutil.rmtree(tracks_dist)
    if weekly_dist.exists():
        shutil.rmtree(weekly_dist)
    if special_dist.exists():
        shutil.rmtree(special_dist)
    for generated_file in ("index.html", "search-index.json", "feed.json", "rss.xml"):
        target = dist_dir / generated_file
        if target.exists():
            target.unlink()
    assets_dist.mkdir(parents=True, exist_ok=True)
    archives_dist.mkdir(parents=True, exist_ok=True)
    tracks_dist.mkdir(parents=True, exist_ok=True)
    weekly_dist.mkdir(parents=True, exist_ok=True)
    special_dist.mkdir(parents=True, exist_ok=True)

    nojekyll = dist_dir / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.touch()

    latest_report = reports[0]
    search_index = _build_search_index(reports)
    json_feed = _build_json_feed(reports)
    rss_feed = _build_rss(reports)

    _write_text(dist_dir / "index.html", _build_homepage(latest_report, reports, track_summaries))
    _write_text(dist_dir / "search-index.json", json.dumps(search_index, ensure_ascii=False, indent=2))
    _write_text(dist_dir / "feed.json", json.dumps(json_feed, ensure_ascii=False, indent=2))
    _write_text(dist_dir / "rss.xml", rss_feed)
    _write_text(assets_dist / "site.css", _base_css())
    _write_text(archives_dist / "index.html", _build_archives_index(reports))
    _write_text(tracks_dist / "index.html", _build_tracks_index(track_summaries))
    _write_text(weekly_dist / "index.html", _build_weekly_index(weekly_reports))
    _write_text(special_dist / "index.html", _build_special_index(special_collections))

    for report in reports:
        _write_text(archives_dist / str(report["date"]) / "index.html", _build_day_page(report))
        _write_text(archives_dist / str(report["date"]) / "brief" / "index.html", _build_report_teaser_page(report))
        for index, signal in enumerate(report["signals"], start=1):
            _write_text(
                archives_dist / str(report["date"]) / "signals" / str(index) / "index.html",
                _build_signal_article_page(report, signal),
            )
    for week in weekly_reports:
        _write_text(weekly_dist / str(week["week_key"]) / "index.html", _build_week_page(week))
    for track in track_summaries:
        _write_text(tracks_dist / _slugify(track["key"]) / "index.html", _build_track_page(track, reports))
    for collection in special_collections:
        _write_text(special_dist / str(collection["slug"]) / "index.html", _build_special_page(collection))

    print(f"[Pages] Site built at {dist_dir}")
    print(f"[Pages] Index: {dist_dir / 'index.html'}")
    print(f"[Pages] Archives: {len(list(archives_dist.rglob('*.html')))} files")
    return dist_dir
