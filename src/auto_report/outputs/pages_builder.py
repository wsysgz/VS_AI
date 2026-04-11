"""GitHub Pages 站点构建器 — V7 Milestone B public reading site."""

from __future__ import annotations

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
SITE_DESCRIPTION = "AI / Agent / Electronics daily intelligence briefing with archives, search, and feeds."

DOMAIN_LABELS = {
    "ai-llm-agent": "AI / Agent",
    "ai-x-electronics": "AI × Electronics",
}
PUBLICATION_PRIORITY = {"reviewed": 1, "auto": 0}


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


def _source_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    return host or "unknown"


def _format_date(date_text: str) -> str:
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%Y.%m.%d")
    except ValueError:
        return date_text


def _parse_date(date_text: str) -> date:
    return datetime.strptime(date_text, "%Y-%m-%d").date()


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
    brief = compose_executive_brief("自动情报快报", generated_at, payload)
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
        source = _source_label(url)
        domain = _safe_text(raw_signal.get("primary_domain")) or "unknown"
        tags = [str(tag).strip() for tag in raw_signal.get("tags", []) if str(tag).strip()]
        summary = _strip_html(raw_signal.get("summary"))
        signal = {
            "title": title,
            "url": url,
            "summary": summary or "暂无摘要",
            "domain": domain,
            "domain_label": _domain_label(domain),
            "source": source,
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
        "judgment": brief["judgment"],
        "executive_summary": brief["executive_summary"][:3],
        "mainlines": brief["mainlines"][:3],
        "topic_briefs": brief["topic_briefs"][:3],
        "watchlist": brief["watchlist"],
        "forecast_conclusion": brief["forecast_conclusion"],
        "publication_mode": publication_mode,
        "publication_label": _publication_label(publication_mode),
        "signals": normalized_signals,
        "top_signals": normalized_signals[:6],
        "source_counts": dict(source_counts.most_common()),
        "domain_counts": dict(domain_counts.most_common()),
        "total_items": int(meta.get("total_items", 0)),
        "total_topics": int(meta.get("total_topics", 0)),
        "archive_url": f"archives/{date_text}/",
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
                    signal_lookup[signal_key] = signal

        top_signals = sorted(
            signal_lookup.values(),
            key=lambda item: (-float(item["score"]), item["title"]),
        )[:8]
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
                "archive_url": f"weekly/{week_key}/",
                "generated_at": week_reports[0]["generated_at"],
            }
        )

    return sorted(weekly_reports, key=lambda item: item["week_key"], reverse=True)


def _build_special_collections(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    definitions = [
        (
            "verified",
            "Verified Themes",
            "聚合跨日持续和多源印证后已经形成确认主线的主题。",
            lambda signal: str(signal.get("lifecycle_state", "new")) == "verified",
        ),
        (
            "risk-watch",
            "Risk Watch",
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
                    "tags": signal["tags"],
                    "url": signal["url"],
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
    --ink: #eef4fb;
    --muted: #9fb2c8;
    --line: rgba(255,255,255,0.10);
    --surface: rgba(6, 18, 31, 0.78);
    --surface-strong: #08192a;
    --accent: #7be0d6;
    --accent-2: #f3b562;
    --accent-3: #7ca6ff;
    --bg: #03101d;
    --hero: linear-gradient(135deg, #061c31 0%, #0f3a52 42%, #174a49 72%, #80603a 100%);
    --shadow: 0 24px 80px rgba(0, 0, 0, 0.24);
    font-family: "Space Grotesk", "IBM Plex Sans", "Segoe UI", sans-serif;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0;
    color: var(--ink);
    background:
      radial-gradient(circle at 12% 0%, rgba(123, 224, 214, 0.18), transparent 24%),
      radial-gradient(circle at 100% 20%, rgba(243, 181, 98, 0.14), transparent 28%),
      linear-gradient(180deg, #020b14 0%, var(--bg) 100%);
  }
  a { color: inherit; }
  .site-shell { max-width: 1200px; margin: 0 auto; padding: 0 20px 56px; }
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 18px 0;
    font-size: 14px;
    color: var(--muted);
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  .brand-mark {
    width: 11px;
    height: 11px;
    border-radius: 999px;
    background: var(--accent);
    box-shadow: 0 0 18px rgba(123, 224, 214, 0.55);
  }
  .nav-links {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }
  .nav-links a {
    color: var(--muted);
    text-decoration: none;
  }
  .nav-links a:hover { color: var(--ink); }
  .hero {
    position: relative;
    min-height: calc(100svh - 72px);
    display: grid;
    align-items: end;
    padding: 72px 28px 36px;
    border: 1px solid var(--line);
    border-radius: 30px;
    background: var(--hero);
    overflow: hidden;
    box-shadow: var(--shadow);
  }
  .hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
      linear-gradient(130deg, rgba(255,255,255,0.04), transparent 35%),
      linear-gradient(0deg, rgba(2,11,20,0.58), rgba(2,11,20,0.18));
    pointer-events: none;
  }
  .hero-grid {
    position: relative;
    z-index: 1;
    display: grid;
    gap: 24px;
  }
  .eyebrow {
    font-size: 12px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: rgba(238,244,251,0.72);
  }
  .hero h1 {
    margin: 0;
    max-width: 9ch;
    font-size: clamp(42px, 9vw, 96px);
    line-height: 0.92;
    letter-spacing: -0.05em;
  }
  .hero-copy {
    max-width: 620px;
    color: rgba(238,244,251,0.84);
    font-size: 16px;
    line-height: 1.8;
  }
  .hero-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(2,11,20,0.18);
    color: rgba(238,244,251,0.78);
    font-size: 13px;
    text-decoration: none;
    backdrop-filter: blur(10px);
  }
  .chip:hover { background: rgba(2,11,20,0.28); }
  .section {
    margin-top: 28px;
    padding: 28px;
    border: 1px solid var(--line);
    border-radius: 26px;
    background: var(--surface);
    backdrop-filter: blur(14px);
  }
  .section-title {
    margin: 0 0 18px;
    font-size: 21px;
    letter-spacing: -0.02em;
  }
  .subtle { color: var(--muted); }
  .stats-grid,
  .signal-grid,
  .archive-grid,
  .summary-grid {
    display: grid;
    gap: 16px;
  }
  .stats-grid { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
  .summary-grid { grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  .signal-grid { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
  .archive-grid { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
  .stat, .signal, .archive-card, .summary-card, .topic-card {
    padding: 18px;
    border: 1px solid var(--line);
    border-radius: 20px;
    background: rgba(4, 15, 28, 0.54);
  }
  .stat strong, .summary-card strong {
    display: block;
    margin-top: 8px;
    font-size: 30px;
    letter-spacing: -0.04em;
  }
  .signal h3, .archive-card h3, .topic-card h3 {
    margin: 0 0 8px;
    font-size: 18px;
    letter-spacing: -0.02em;
  }
  .signal p, .archive-card p, .summary-card p, .topic-card p {
    margin: 0;
    color: var(--muted);
    line-height: 1.72;
  }
  .signal-tags, .filter-group, .archive-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .tag {
    display: inline-flex;
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(123, 224, 214, 0.08);
    color: var(--accent);
    font-size: 12px;
  }
  .tag.alt {
    background: rgba(124, 166, 255, 0.10);
    color: #9bb7ff;
  }
  .tag.warm {
    background: rgba(243, 181, 98, 0.10);
    color: #ffd089;
  }
  .signal-footer, .archive-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-top: 14px;
    color: var(--muted);
    font-size: 13px;
  }
  .signal a, .archive-card a, .feed-links a {
    text-decoration: none;
  }
  .signal a:hover, .archive-card a:hover, .feed-links a:hover {
    color: var(--accent);
  }
  .search-shell {
    display: grid;
    gap: 16px;
  }
  .search-shell input {
    width: 100%;
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: rgba(1, 9, 17, 0.56);
    color: var(--ink);
    font: inherit;
  }
  .search-results {
    display: grid;
    gap: 12px;
  }
  .search-hit {
    padding: 14px 16px;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: rgba(4, 15, 28, 0.48);
  }
  .search-hit h4 {
    margin: 0 0 8px;
    font-size: 16px;
  }
  .search-hit p {
    margin: 0;
    color: var(--muted);
    line-height: 1.65;
  }
  .feed-links {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 16px;
  }
  .archive-filters {
    display: grid;
    gap: 14px;
    margin-bottom: 20px;
  }
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
    border-color: rgba(123, 224, 214, 0.32);
    background: rgba(123, 224, 214, 0.08);
  }
  .footer {
    margin-top: 28px;
    padding: 24px 0 8px;
    color: var(--muted);
    text-align: center;
    font-size: 13px;
  }
  @media (max-width: 760px) {
    .site-shell { padding: 0 14px 40px; }
    .hero { min-height: auto; padding: 56px 18px 24px; border-radius: 24px; }
    .section { padding: 18px; border-radius: 20px; }
    .topbar { flex-direction: column; align-items: flex-start; }
  }
"""


def _summary_cards(report: dict[str, object]) -> str:
    cards = []
    for line in report["mainlines"]:
        cards.append(
            f"""<article class="summary-card">
  <h3>{html.escape(line["title"])}</h3>
  <p>{html.escape(line["why_it_matters"])}</p>
</article>"""
        )
    return "".join(cards) or '<article class="summary-card"><h3>暂无主线</h3><p>等待更多高置信度信号。</p></article>'


def _topic_cards(report: dict[str, object]) -> str:
    cards = []
    for topic in report["topic_briefs"]:
        cards.append(
            f"""<article class="topic-card">
  <h3>{html.escape(topic["title"])}</h3>
  <p>{html.escape(topic["core_insight"])}</p>
  <div class="archive-meta" style="margin-top:12px;">
    <span class="tag alt">{html.escape(_domain_label(topic["primary_domain"]))}</span>
    <span class="tag warm">{html.escape(topic["confidence"])}</span>
  </div>
</article>"""
        )
    return "".join(cards) or '<article class="topic-card"><h3>暂无重点分析</h3><p>等待下一轮信号收敛。</p></article>'


def _signal_cards(signals: list[dict[str, object]]) -> str:
    cards = []
    for signal in signals:
        tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in signal["tags"][:3])
        cards.append(
            f"""<article class="signal">
  <span class="tag alt">{html.escape(signal["domain_label"])}</span>
  <h3>{html.escape(signal["title"])}</h3>
  <p>{html.escape(signal["summary"])}</p>
  <div class="signal-tags" style="margin-top:12px;">{tags}</div>
  <div class="signal-footer">
    <span>{html.escape(signal["source"])} · {signal["score"]:.1f}</span>
    <a href="{html.escape(signal["url"])}" target="_blank" rel="noopener">查看原文</a>
  </div>
</article>"""
        )
    return "".join(cards) or '<article class="signal"><h3>暂无信号</h3><p>等待下一次构建。</p></article>'


def _archive_cards(reports: list[dict[str, object]]) -> str:
    cards = []
    for report in reports:
        domain_tags = "".join(f'<span class="tag alt">{html.escape(name)}</span>' for name in list(report["domain_counts"].keys())[:2])
        source_tags = "".join(f'<span class="tag warm">{html.escape(name)}</span>' for name in list(report["source_counts"].keys())[:2])
        publication_tag = f'<span class="tag">{html.escape(report["publication_label"])}</span>'
        cards.append(
            f"""<article class="archive-card" data-domain="{' '.join(report['domain_counts'].keys())}" data-source="{' '.join(report['source_counts'].keys())}">
  <span class="eyebrow">{html.escape(report["date_label"])}</span>
  <h3>{html.escape(report["judgment"])}</h3>
  <p>{html.escape(" ".join(report["executive_summary"]) or report["watchlist"])}</p>
  <div class="archive-meta" style="margin-top:12px;">{domain_tags}{source_tags}{publication_tag}</div>
  <div class="archive-footer">
    <span>{report["total_topics"]} topics · {report["total_items"]} items</span>
    <a href="{html.escape(report["archive_url"])}">打开日报</a>
  </div>
</article>"""
        )
    return "".join(cards)


def _weekly_cards(weeks: list[dict[str, object]]) -> str:
    cards = []
    for week in weeks:
        domain_tags = "".join(
            f'<span class="tag alt">{html.escape(name)}</span>'
            for name in list(week["domain_counts"].keys())[:2]
        )
        cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">{html.escape(week["week_label"])}</span>
  <h3>{html.escape(week["range_label"])}</h3>
  <p>{week["report_count"]} daily brief(s) · {week["total_topics"]} topics · {week["total_items"]} raw items</p>
  <div class="archive-meta" style="margin-top:12px;">{domain_tags}</div>
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
  <h3>{collection["entry_count"]} curated theme(s)</h3>
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
        cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">{html.escape(_format_date(str(item["last_date"])))}</span>
  <h3>{html.escape(item["title"])}</h3>
  <p>{html.escape(item["summary"])}</p>
  <div class="archive-meta" style="margin-top:12px;">
    <span class="tag alt">{html.escape(item["domain_label"])}</span>
    <span class="tag warm">{html.escape(str(item["lifecycle_state"]))}</span>
    <span class="tag">{html.escape(str(item["risk_level"]))}</span>
  </div>
  <p class="subtle" style="margin-top:12px;">{html.escape(str(item["enrichment_summary"]))}</p>
  <div class="archive-footer">
    <span>{item["appearances"]} appearance(s) · {_format_date(str(item["first_date"]))} → {_format_date(str(item["last_date"]))}</span>
    <a href="{html.escape(item["archive_url"])}">打开日报</a>
  </div>
</article>"""
        )
    return "".join(cards) or '<article class="archive-card"><h3>暂无专题主题</h3><p>等待后续日报累积更多信号。</p></article>'


def _build_homepage(report: dict[str, object], reports: list[dict[str, object]]) -> str:
    recent_archives = reports[:6]
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(SITE_TITLE)}</title>
<meta name="description" content="{html.escape(report["judgment"])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{_base_css()}</style>
</head>
<body>
  <div class="site-shell">
    <header class="topbar">
      <a class="brand" href="./"><span class="brand-mark"></span><span>VS_AI</span></a>
      <nav class="nav-links">
        <a href="./archives/">Archives</a>
        <a href="./weekly/">Weekly</a>
        <a href="./special/">Special</a>
        <a href="./feed.json">JSON Feed</a>
        <a href="./rss.xml">RSS</a>
        <a href="https://github.com/wsysgz/VS_AI" target="_blank" rel="noopener">GitHub</a>
      </nav>
    </header>

    <section class="hero">
      <div class="hero-grid">
        <div class="eyebrow">Daily Briefing</div>
        <h1>Briefing For AI Signals.</h1>
        <p class="hero-copy">{html.escape(report["judgment"])}</p>
        <div class="hero-meta">
          <span class="chip">最新更新 {html.escape(report["generated_at"])}</span>
          <span class="chip">{html.escape(report["publication_label"])}</span>
          <a class="chip" href="./archives/">进入归档检索</a>
          <a class="chip" href="./weekly/">进入周报</a>
          <a class="chip" href="./special/">进入专题</a>
          <a class="chip" href="./rss.xml">订阅 RSS</a>
        </div>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">今日面板</h2>
      <div class="stats-grid">
        <article class="stat"><span class="subtle">Raw items</span><strong>{report["total_items"]}</strong></article>
        <article class="stat"><span class="subtle">Topics</span><strong>{report["total_topics"]}</strong></article>
        <article class="stat"><span class="subtle">Domains</span><strong>{len(report["domain_counts"])}</strong></article>
        <article class="stat"><span class="subtle">Sources</span><strong>{len(report["source_counts"])}</strong></article>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">AI Insight</h2>
      <div class="summary-grid">
        {_summary_cards(report)}
      </div>
      <p class="subtle" style="margin-top:16px;">{html.escape(report["watchlist"])}</p>
    </section>

    <section class="section">
      <h2 class="section-title">Theme Signals</h2>
      <div class="signal-grid">
        {_signal_cards(report["top_signals"])}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Search</h2>
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
      <h2 class="section-title">Archive Stream</h2>
      <div class="archive-grid">
        {_archive_cards(recent_archives)}
      </div>
    </section>

    <footer class="footer">
      <p>Public reading site only. Operations diagnostics stay in the private ops dashboard.</p>
    </footer>
  </div>

  <script>
    (async function() {{
      const input = document.getElementById("site-search");
      const results = document.getElementById("search-results");
      const response = await fetch("./search-index.json");
      const payload = await response.json();
      const entries = payload.entries || [];

      function render(list) {{
        if (!list.length) {{
          results.innerHTML = '<div class="search-hit"><h4>暂无结果</h4><p>换一个关键词试试。</p></div>';
          return;
        }}
        results.innerHTML = list.slice(0, 8).map((entry) => {{
          const tags = (entry.tags || []).slice(0, 3).map((tag) => `<span class="tag">${{tag}}</span>`).join("");
          return `
            <article class="search-hit">
              <h4><a href="${{entry.url}}" target="_blank" rel="noopener">${{entry.title}}</a></h4>
              <p>${{entry.summary}}</p>
              <div class="archive-meta" style="margin-top:10px;">
                <span class="tag alt">${{entry.domain}}</span>
                <span class="tag warm">${{entry.source}}</span>
                ${{tags}}
              </div>
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
<title>VS_AI Archives</title>
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
        <a href="../">Home</a>
        <a href="../weekly/">Weekly</a>
        <a href="../special/">Special</a>
        <a href="../feed.json">JSON Feed</a>
        <a href="../rss.xml">RSS</a>
      </nav>
    </header>

    <section class="section">
      <h1 class="section-title">Archives</h1>
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
        <div class="filter-group">
          <button type="button" class="is-active" data-kind="source" data-value="">全部</button>
          {source_buttons}
        </div>
      </div>
    </section>

    <section class="section">
      <div id="archive-grid" class="archive-grid">
        {_archive_cards(reports)}
      </div>
    </section>
  </div>

  <script>
    const archiveCards = [...document.querySelectorAll(".archive-card")];
    const filters = {{ domain: "", source: "" }};
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


def _build_day_page(report: dict[str, object]) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(report["date_label"])} | VS_AI</title>
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
        <a href="../">Archives</a>
        <a href="../../weekly/">Weekly</a>
        <a href="../../special/">Special</a>
        <a href="../../">Home</a>
      </nav>
    </header>

    <section class="section">
      <div class="eyebrow">{html.escape(report["date_label"])}</div>
      <h1 class="section-title" style="font-size:34px;">{html.escape(report["judgment"])}</h1>
      <p class="subtle">{html.escape(" ".join(report["executive_summary"]) or report["watchlist"])}</p>
      <div class="archive-meta" style="margin-top:14px;">
        <span class="tag alt">{report["total_topics"]} topics</span>
        <span class="tag warm">{report["total_items"]} raw items</span>
        <span class="tag">{html.escape(report["publication_label"])}</span>
        <span class="tag">{html.escape(report["generated_at"])}</span>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Briefing Mainlines</h2>
      <div class="summary-grid">
        {_summary_cards(report)}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Deep Reads</h2>
      <div class="summary-grid">
        {_topic_cards(report)}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">All Signals</h2>
      <div class="signal-grid">
        {_signal_cards(report["signals"])}
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
<title>VS_AI Weekly Briefs</title>
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
        <a href="../">Home</a>
        <a href="../archives/">Archives</a>
        <a href="../special/">Special</a>
        <a href="../feed.json">JSON Feed</a>
      </nav>
    </header>

    <section class="section">
      <h1 class="section-title">Weekly Briefs</h1>
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
        daily_cards.append(
            f"""<article class="archive-card">
  <span class="eyebrow">{html.escape(report["date_label"])}</span>
  <h3>{html.escape(report["judgment"])}</h3>
  <p>{html.escape(" ".join(report["executive_summary"]) or report["watchlist"])}</p>
  <div class="archive-footer">
    <span>{report["total_topics"]} topics · {report["total_items"]} items</span>
    <a href="../../archives/{html.escape(report["date"])}/">打开日报</a>
  </div>
</article>"""
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(week["week_label"])} | VS_AI Weekly</title>
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
        <a href="../">Weekly</a>
        <a href="../../archives/">Archives</a>
        <a href="../../special/">Special</a>
        <a href="../../">Home</a>
      </nav>
    </header>

    <section class="section">
      <div class="eyebrow">{html.escape(week["week_label"])}</div>
      <h1 class="section-title" style="font-size:34px;">{html.escape(week["range_label"])}</h1>
      <p class="subtle">{week["report_count"]} daily brief(s) · {week["total_topics"]} topics · {week["total_items"]} raw items</p>
    </section>

    <section class="section">
      <h2 class="section-title">Weekly Stream</h2>
      <div class="archive-grid">
        {"".join(daily_cards)}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Top Signals</h2>
      <div class="signal-grid">
        {_signal_cards(week["top_signals"])}
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
<title>VS_AI Special Briefs</title>
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
        <a href="../">Home</a>
        <a href="../archives/">Archives</a>
        <a href="../weekly/">Weekly</a>
      </nav>
    </header>

    <section class="section">
      <h1 class="section-title">Special Briefs</h1>
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
<title>{html.escape(collection["title"])} | VS_AI Special</title>
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
        <a href="../">Special</a>
        <a href="../../weekly/">Weekly</a>
        <a href="../../archives/">Archives</a>
        <a href="../../">Home</a>
      </nav>
    </header>

    <section class="section">
      <div class="eyebrow">{html.escape(collection["title"])}</div>
      <h1 class="section-title" style="font-size:34px;">{collection["entry_count"]} curated theme(s)</h1>
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
    archives_dist = dist_dir / "archives"
    weekly_dist = dist_dir / "weekly"
    special_dist = dist_dir / "special"

    reports = _collect_reports(reports_dir, archives_dir)
    if not reports:
        raise FileNotFoundError("No report payloads available for pages build")
    weekly_reports = _build_weekly_reports(reports)
    special_collections = _build_special_collections(reports)

    dist_dir.mkdir(parents=True, exist_ok=True)

    if archives_dist.exists():
        shutil.rmtree(archives_dist)
    if weekly_dist.exists():
        shutil.rmtree(weekly_dist)
    if special_dist.exists():
        shutil.rmtree(special_dist)
    for generated_file in ("index.html", "search-index.json", "feed.json", "rss.xml"):
        target = dist_dir / generated_file
        if target.exists():
            target.unlink()
    archives_dist.mkdir(parents=True, exist_ok=True)
    weekly_dist.mkdir(parents=True, exist_ok=True)
    special_dist.mkdir(parents=True, exist_ok=True)

    nojekyll = dist_dir / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.touch()

    latest_report = reports[0]
    search_index = _build_search_index(reports)
    json_feed = _build_json_feed(reports)
    rss_feed = _build_rss(reports)

    _write_text(dist_dir / "index.html", _build_homepage(latest_report, reports))
    _write_text(dist_dir / "search-index.json", json.dumps(search_index, ensure_ascii=False, indent=2))
    _write_text(dist_dir / "feed.json", json.dumps(json_feed, ensure_ascii=False, indent=2))
    _write_text(dist_dir / "rss.xml", rss_feed)
    _write_text(archives_dist / "index.html", _build_archives_index(reports))
    _write_text(weekly_dist / "index.html", _build_weekly_index(weekly_reports))
    _write_text(special_dist / "index.html", _build_special_index(special_collections))

    for report in reports:
        _write_text(archives_dist / str(report["date"]) / "index.html", _build_day_page(report))
    for week in weekly_reports:
        _write_text(weekly_dist / str(week["week_key"]) / "index.html", _build_week_page(week))
    for collection in special_collections:
        _write_text(special_dist / str(collection["slug"]) / "index.html", _build_special_page(collection))

    print(f"[Pages] Site built at {dist_dir}")
    print(f"[Pages] Index: {dist_dir / 'index.html'}")
    print(f"[Pages] Archives: {len(list(archives_dist.rglob('*.html')))} files")
    return dist_dir
