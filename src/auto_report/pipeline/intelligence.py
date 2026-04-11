from __future__ import annotations

import json
import re
from collections.abc import Callable
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests

from auto_report.models.records import CollectedItem
from auto_report.settings import load_settings
from auto_report.sources.rss import parse_rss_content
from auto_report.sources.websites import extract_listing_items


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
SOURCE_TYPE_ORDER = {"official": 0, "repo": 1, "paper": 2, "community": 3}
SUPPORT_SOURCE_TYPES = {"official", "repo", "paper"}
HIGH_VALUE_ENRICHMENT_MIN_SCORE = 3.0
EXTERNAL_ENRICHMENT_CIRCUIT_FAILURE_LIMIT = 2
SUPPORT_STOPWORDS = {
    "launch",
    "launches",
    "launched",
    "introducing",
    "introduce",
    "introduced",
    "show",
    "hn",
    "new",
    "the",
    "for",
    "with",
    "from",
    "into",
    "and",
}


def _default_external_enrichment_metrics(enabled: bool, max_signals: int) -> dict[str, object]:
    return {
        "enabled": enabled,
        "max_signals": max(0, max_signals),
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "budget_used": 0,
        "success_rate": 0.0,
        "circuit_open": False,
        "reasons": [],
    }


def _append_external_reason(metrics: dict[str, object], reason: str, title: str) -> None:
    metrics.setdefault("reasons", []).append(f"{reason}: {title}")


def _classify_external_failure(exc: Exception) -> str:
    message = str(exc).lower()
    if isinstance(exc, TimeoutError) or "timed out" in message or "timeout" in message:
        return "timeout"
    return "request-error"


def _fetch_text(url: str, timeout: int = 12, headers: dict[str, str] | None = None) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "auto-report/0.1", **(headers or {})},
    )
    response.raise_for_status()
    return response.text


def _coerce_date(value: str) -> str:
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            pass
    return datetime.now().astimezone().date().isoformat()


def _tokenize(text: object) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[\w\u4e00-\u9fff]+", str(text or ""))
        if len(token) >= 2
    }


def _titles_related(left: str, right: str) -> bool:
    left_clean = str(left or "").strip().lower()
    right_clean = str(right or "").strip().lower()
    if not left_clean or not right_clean:
        return False
    if left_clean == right_clean:
        return True
    if left_clean in right_clean or right_clean in left_clean:
        return True

    left_tokens = _tokenize(left_clean)
    right_tokens = _tokenize(right_clean)
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    similarity = overlap / max(len(left_tokens), len(right_tokens))
    return overlap >= 3 and similarity >= 0.5


def _source_type(source_id: str) -> str:
    source = str(source_id or "").strip().lower()
    if not source:
        return "official"
    if source == "hacker-news":
        return "community"
    if source.startswith("arxiv"):
        return "paper"
    if "repo" in source or "github" in source:
        return "repo"
    return "official"


def _support_tokens(text: object) -> set[str]:
    return {
        token
        for token in _tokenize(text)
        if token not in SUPPORT_STOPWORDS
    }


def _collect_support_evidence(signal: dict[str, object], items: list[CollectedItem]) -> list[dict[str, object]]:
    signal_title = str(signal.get("title", "")).strip()
    signal_url = str(signal.get("url", "")).strip()
    signal_tokens = _support_tokens(signal_title)
    candidates: list[tuple[int, int, dict[str, object]]] = []
    seen_urls: set[str] = set()

    for item in items:
        source_type = _source_type(item.source_id)
        if source_type not in SUPPORT_SOURCE_TYPES:
            continue
        if item.url == signal_url or item.url in seen_urls:
            continue

        item_tokens = _support_tokens(item.title)
        overlap = len(signal_tokens & item_tokens)
        if overlap < 2 and not _titles_related(signal_title, item.title):
            continue

        evidence = {
            "source_id": item.source_id,
            "source_type": source_type,
            "title": item.title,
            "url": item.url,
            "summary": item.summary.strip(),
            "evidence_scope": "current-run",
        }
        candidates.append(
            (
                SOURCE_TYPE_ORDER.get(source_type, 99),
                -overlap,
                evidence,
            )
        )
        seen_urls.add(item.url)

    candidates.sort(key=lambda item: (item[0], item[1], item[2]["title"]))
    return [candidate[2] for candidate in candidates[:3]]


def _merge_support_evidence(*buckets: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    for bucket in buckets:
        for raw_item in bucket:
            if not isinstance(raw_item, dict):
                continue
            url = str(raw_item.get("url", "")).strip()
            if not url or url in seen_urls:
                continue
            item = dict(raw_item)
            item["evidence_scope"] = str(item.get("evidence_scope", "external")).strip() or "external"
            merged.append(item)
            seen_urls.add(url)
    return merged[:5]


def _build_enrichment(source_ids: list[str], support_evidence: list[dict[str, object]] | None = None) -> dict[str, object]:
    normalized_source_ids = sorted({str(source_id).strip() for source_id in source_ids if str(source_id).strip()})
    source_types = sorted(
        {_source_type(source_id) for source_id in normalized_source_ids},
        key=lambda item: SOURCE_TYPE_ORDER.get(item, 99),
    )
    support_evidence = support_evidence or []
    verification_flags: list[str] = []
    if len(normalized_source_ids) >= 2:
        verification_flags.append("cross-source")
    if "official" in source_types:
        verification_flags.append("official-source")
    if "repo" in source_types:
        verification_flags.append("repo")
    if "paper" in source_types:
        verification_flags.append("paper")
    if "community" in source_types:
        verification_flags.append("community")
    if support_evidence:
        verification_flags.append("related-support")
    if any(str(item.get("evidence_scope", "")) == "external" for item in support_evidence):
        verification_flags.append("external-support")

    labels = {
        "official": "official",
        "repo": "repo",
        "paper": "paper",
        "community": "community",
    }
    summary_bits = [f"{len(normalized_source_ids)} source(s)"]
    if source_types:
        summary_bits.append(" / ".join(labels[item] for item in source_types))
    if support_evidence:
        summary_bits.append(f"{len(support_evidence)} related support")

    return {
        "cross_source_count": len(normalized_source_ids),
        "source_ids": normalized_source_ids,
        "source_types": source_types,
        "support_evidence": support_evidence,
        "verification_flags": verification_flags,
        "summary": " | ".join(summary_bits),
    }


def _matching_score(signal: dict[str, object], title: str, summary: str = "") -> tuple[int, int]:
    signal_title = str(signal.get("title", "")).strip()
    signal_tokens = _support_tokens(signal_title)
    candidate_tokens = _support_tokens(f"{title} {summary}")
    overlap = len(signal_tokens & candidate_tokens)
    related = _titles_related(signal_title, title)
    return (1 if related else 0, overlap)


def _best_external_evidence(
    signal: dict[str, object],
    candidates: list[dict[str, object]],
    source_type: str,
    limit: int = 1,
) -> list[dict[str, object]]:
    ranked: list[tuple[int, int, dict[str, object]]] = []
    for raw_item in candidates:
        if not isinstance(raw_item, dict):
            continue
        title = str(raw_item.get("title", "")).strip()
        url = str(raw_item.get("url", "")).strip()
        summary = str(raw_item.get("summary", "")).strip()
        if not title or not url:
            continue
        related, overlap = _matching_score(signal, title, summary)
        if related == 0 and overlap < 2:
            continue
        ranked.append(
            (
                -related,
                -overlap,
                {
                    "source_id": str(raw_item.get("source_id", source_type)).strip() or source_type,
                    "source_type": source_type,
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "evidence_scope": "external",
                },
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2]["title"]))
    return [item[2] for item in ranked[:limit]]


def _external_query_terms(signal: dict[str, object], limit: int = 5) -> list[str]:
    title = str(signal.get("title", "")).strip()
    return list(_support_tokens(title))[:limit]


def _fetch_external_official_evidence(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
    settings = load_settings(root_dir)
    domain = str(signal.get("primary_domain", "")).strip()
    candidates: list[dict[str, object]] = []

    for source in settings.sources.get("rss", {}).get("sources", []):
        if not source.get("enabled", False) or str(source.get("category_hint", "")).strip() != domain:
            continue
        source_id = str(source.get("id", "")).strip()
        if _source_type(source_id) != "official":
            continue
        try:
            content = _fetch_text(str(source["url"]))
            items = parse_rss_content(
                source_id=source_id,
                content=content,
                category_hint=domain,
                max_items=min(int(source.get("max_items", 8)), 8),
                source_rules=source,
            )
        except Exception:
            continue
        candidates.extend(
            {
                "source_id": item.source_id,
                "title": item.title,
                "url": item.url,
                "summary": item.summary,
            }
            for item in items
        )

    for source in settings.sources.get("websites", {}).get("sources", []):
        if not source.get("enabled", False) or str(source.get("category_hint", "")).strip() != domain:
            continue
        source_id = str(source.get("id", "")).strip()
        if _source_type(source_id) != "official":
            continue
        try:
            html = _fetch_text(str(source["url"]))
            items = extract_listing_items(source, html)[: min(int(source.get("max_items", 6)), 6)]
        except Exception:
            continue
        candidates.extend(
            {
                "source_id": item.source_id,
                "title": item.title,
                "url": item.url,
                "summary": item.summary,
            }
            for item in items
        )

    return _best_external_evidence(signal, candidates, source_type="official")


def _fetch_external_repo_evidence(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
    settings = load_settings(root_dir)
    terms = _external_query_terms(signal)
    if not terms:
        return []
    headers = {"Accept": "application/vnd.github+json"}
    token = settings.env.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    query = quote_plus(" ".join(terms))
    url = f"https://api.github.com/search/repositories?q={query}&per_page=3&sort=updated&order=desc"
    try:
        payload = requests.get(url, headers=headers, timeout=12).json()
    except Exception:
        return []
    candidates = [
        {
            "source_id": "github-search",
            "title": str(item.get("full_name", "")).strip(),
            "url": str(item.get("html_url", "")).strip(),
            "summary": str(item.get("description", "") or "").strip(),
        }
        for item in payload.get("items", [])
        if isinstance(item, dict)
    ]
    return _best_external_evidence(signal, candidates, source_type="repo")


def _fetch_external_paper_evidence(signal: dict[str, object]) -> list[dict[str, object]]:
    terms = _external_query_terms(signal)
    if not terms:
        return []
    query = quote_plus(" AND ".join(terms[:4]))
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query=all:{query}&start=0&max_results=3&sortBy=relevance&sortOrder=descending"
    )
    try:
        parsed = feedparser.parse(_fetch_text(url))
    except Exception:
        return []

    candidates = [
        {
            "source_id": "arxiv-search",
            "title": str(entry.get("title", "")).strip(),
            "url": str(entry.get("link", "")).strip(),
            "summary": str(entry.get("summary", "")).strip(),
        }
        for entry in getattr(parsed, "entries", [])
    ]
    return _best_external_evidence(signal, candidates, source_type="paper")


def fetch_external_support_evidence(
    root_dir: Path,
    signal: dict[str, object],
    timeout_seconds: int = 12,
) -> list[dict[str, object]]:
    # Keep the external lookup bounded so enrichment cannot dominate the report run.
    original_fetch_text = _fetch_text

    def _bounded_fetch_text(url: str, timeout: int = 12, headers: dict[str, str] | None = None) -> str:
        return original_fetch_text(url, timeout=min(timeout_seconds, timeout), headers=headers)

    globals()["_fetch_text"] = _bounded_fetch_text
    try:
        return _merge_support_evidence(
            _fetch_external_official_evidence(root_dir, signal),
            _fetch_external_repo_evidence(root_dir, signal),
            _fetch_external_paper_evidence(signal),
        )
    finally:
        globals()["_fetch_text"] = original_fetch_text


def _load_history(root_dir: Path) -> list[dict[str, object]]:
    archives_dir = root_dir / "data" / "archives"
    if not archives_dir.exists():
        return []

    history: list[dict[str, object]] = []
    for day_dir in sorted((path for path in archives_dir.iterdir() if path.is_dir()), reverse=True):
        json_files = sorted(day_dir.glob("*-summary.json"))
        if not json_files:
            continue
        payload = json.loads(json_files[-1].read_text(encoding="utf-8"))
        analyses_by_title = {
            str(item.get("title", "")).strip(): item
            for item in payload.get("analyses", [])
            if isinstance(item, dict) and str(item.get("title", "")).strip()
        }
        for raw_signal in payload.get("signals", []):
            if not isinstance(raw_signal, dict):
                continue
            title = str(raw_signal.get("title", "")).strip()
            if not title:
                continue
            matched_analysis = analyses_by_title.get(title, {})
            history.append(
                {
                    "date": day_dir.name,
                    "title": title,
                    "primary_domain": str(
                        raw_signal.get("primary_domain")
                        or matched_analysis.get("primary_domain")
                        or "unknown"
                    ).strip()
                    or "unknown",
                    "score": float(raw_signal.get("score", 0.0)),
                    "source_count": len(raw_signal.get("source_ids", [])) or int(raw_signal.get("evidence_count", 0)),
                    "confidence": str(matched_analysis.get("confidence", "low")).strip() or "low",
                }
            )
    return history


def _match_history(signal: dict[str, object], history: list[dict[str, object]], current_date: str) -> list[dict[str, object]]:
    title = str(signal.get("title", "")).strip()
    domain = str(signal.get("primary_domain", "unknown")).strip() or "unknown"
    matches = [
        item
        for item in history
        if item["date"] != current_date
        and str(item.get("primary_domain", "unknown")) == domain
        and _titles_related(title, str(item.get("title", "")))
    ]
    matches.sort(key=lambda item: str(item["date"]))
    return matches


def _build_memory(signal: dict[str, object], history_matches: list[dict[str, object]], current_date: str) -> dict[str, object]:
    seen_dates = [str(item["date"]) for item in history_matches]
    previous = history_matches[-1] if history_matches else {}
    first_seen = seen_dates[0] if seen_dates else current_date
    unique_dates = sorted({*seen_dates, current_date})
    return {
        "days_seen": len(unique_dates),
        "first_seen": first_seen,
        "last_seen": current_date,
        "previous_score": round(float(previous.get("score", 0.0)), 1) if previous else 0.0,
        "previous_confidence": str(previous.get("confidence", "")).strip(),
        "seen_dates": unique_dates,
    }


def _pick_lifecycle_state(
    signal: dict[str, object],
    confidence: str,
    enrichment: dict[str, object],
    memory: dict[str, object],
) -> str:
    days_seen = int(memory.get("days_seen", 1))
    current_score = float(signal.get("score", 0.0))
    previous_score = float(memory.get("previous_score", 0.0))
    cross_source_count = int(enrichment.get("cross_source_count", 0))
    source_types = set(enrichment.get("source_types", []))

    if days_seen <= 1:
        return "new"
    if (
        cross_source_count >= 2
        and ("official" in source_types or "repo" in source_types or "paper" in source_types)
    ) or (days_seen >= 2 and confidence == "high"):
        return "verified"
    if previous_score and current_score + 0.25 < previous_score:
        return "fading"
    return "rising"


def _pick_signal_risk(
    signal: dict[str, object],
    confidence: str,
    lifecycle_state: str,
    enrichment: dict[str, object],
) -> str:
    score = float(signal.get("score", 0.0))
    cross_source_count = int(enrichment.get("cross_source_count", 0))
    support_evidence = enrichment.get("support_evidence", [])

    if lifecycle_state == "verified":
        return "low"
    if support_evidence and confidence == "low" and score >= 3.0:
        return "medium"
    if confidence == "low" and score >= 3.0 and cross_source_count <= 1:
        return "high"
    if lifecycle_state == "fading" and score >= 2.0:
        return "medium"
    if confidence in {"low", "medium"} and cross_source_count <= 1 and score >= 2.2:
        return "medium"
    return "low"


def _merge_signal_intelligence(
    root_dir: Path,
    signal: dict[str, object],
    history: list[dict[str, object]],
    items: list[CollectedItem],
    current_date: str,
    confidence: str,
    diagnostics: list[str],
    external_support_evidence: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    matches = _match_history(signal, history, current_date=current_date)
    support_evidence = _collect_support_evidence(signal, items)
    merged_support = _merge_support_evidence(support_evidence, external_support_evidence or [])
    enrichment = _build_enrichment(
        [str(item) for item in signal.get("source_ids", [])],
        support_evidence=merged_support,
    )
    memory = _build_memory(signal, matches, current_date=current_date)
    lifecycle_state = _pick_lifecycle_state(signal, confidence, enrichment, memory)
    risk_level = _pick_signal_risk(signal, confidence, lifecycle_state, enrichment)

    enriched_signal = dict(signal)
    enriched_signal["enrichment"] = enrichment
    enriched_signal["memory"] = memory
    enriched_signal["lifecycle_state"] = lifecycle_state
    enriched_signal["risk_level"] = risk_level
    return enriched_signal


def _max_risk_level(*levels: str) -> str:
    return max(levels or ("low",), key=lambda item: RISK_ORDER.get(item, -1))


def _report_risk_level(signals: list[dict[str, object]], diagnostics: list[str]) -> str:
    top_signals = sorted(signals, key=lambda item: float(item.get("score", 0.0)), reverse=True)[:3]
    if any(str(item.get("risk_level", "low")) == "high" for item in top_signals):
        return "high"

    failed_diagnostics = [
        message
        for message in diagnostics
        if "failed:" in str(message).lower() or "timed out" in str(message).lower()
    ]
    if any(str(item.get("risk_level", "low")) == "medium" for item in top_signals) or failed_diagnostics:
        return "medium"
    return "low"


def apply_intelligence_layer(
    root_dir: Path,
    signals: list[dict[str, object]],
    analyses: list[dict[str, object]],
    diagnostics: list[str],
    items: list[CollectedItem] | None = None,
    generated_at: str = "",
    external_enrichment_fetcher: Callable[[Path, dict[str, object]], list[dict[str, object]]] | None = None,
    external_enrichment_max_signals: int = 2,
) -> dict[str, object]:
    history = _load_history(root_dir)
    current_date = _coerce_date(generated_at)
    items = items or []
    analyses_by_title = {
        str(item.get("title", "")).strip(): item
        for item in analyses
        if str(item.get("title", "")).strip()
    }

    enriched_signals: list[dict[str, object]] = []
    signal_index: dict[str, dict[str, object]] = {}
    external_metrics = _default_external_enrichment_metrics(
        enabled=external_enrichment_fetcher is not None,
        max_signals=external_enrichment_max_signals,
    )
    consecutive_external_failures = 0
    for signal in signals:
        title = str(signal.get("title", "")).strip()
        confidence = str(analyses_by_title.get(title, {}).get("confidence", "low")).strip() or "low"
        external_support_evidence: list[dict[str, object]] = []
        score = float(signal.get("score", 0.0))
        if external_enrichment_fetcher:
            if score < HIGH_VALUE_ENRICHMENT_MIN_SCORE:
                external_metrics["skipped"] = int(external_metrics.get("skipped", 0)) + 1
                _append_external_reason(external_metrics, "below-threshold", title)
            elif bool(external_metrics.get("circuit_open", False)):
                external_metrics["skipped"] = int(external_metrics.get("skipped", 0)) + 1
                _append_external_reason(external_metrics, "circuit-open", title)
            elif int(external_metrics.get("attempted", 0)) >= int(external_metrics.get("max_signals", 0)):
                external_metrics["skipped"] = int(external_metrics.get("skipped", 0)) + 1
                _append_external_reason(external_metrics, "budget-exhausted", title)
            else:
                external_metrics["attempted"] = int(external_metrics.get("attempted", 0)) + 1
                external_metrics["budget_used"] = int(external_metrics.get("budget_used", 0)) + 1
                try:
                    external_support_evidence = external_enrichment_fetcher(root_dir, signal)
                except Exception as exc:
                    failure_reason = _classify_external_failure(exc)
                    external_metrics["failed"] = int(external_metrics.get("failed", 0)) + 1
                    _append_external_reason(external_metrics, failure_reason, title)
                    diagnostics.append(
                        f"External enrichment unavailable: {signal.get('title', 'unknown')} -> {exc}"
                    )
                    consecutive_external_failures += 1
                else:
                    if external_support_evidence:
                        external_metrics["succeeded"] = int(external_metrics.get("succeeded", 0)) + 1
                        consecutive_external_failures = 0
                    else:
                        external_metrics["failed"] = int(external_metrics.get("failed", 0)) + 1
                        _append_external_reason(external_metrics, "empty-result", title)
                        consecutive_external_failures += 1

                if consecutive_external_failures >= EXTERNAL_ENRICHMENT_CIRCUIT_FAILURE_LIMIT:
                    external_metrics["circuit_open"] = True

        enriched_signal = _merge_signal_intelligence(
            root_dir,
            signal,
            history,
            items=items,
            current_date=current_date,
            confidence=confidence,
            diagnostics=diagnostics,
            external_support_evidence=external_support_evidence,
        )
        enriched_signals.append(enriched_signal)
        if title:
            signal_index[title] = enriched_signal

    attempted = int(external_metrics.get("attempted", 0))
    succeeded = int(external_metrics.get("succeeded", 0))
    external_metrics["success_rate"] = round((succeeded / attempted), 2) if attempted else 0.0

    enriched_analyses: list[dict[str, object]] = []
    for analysis in analyses:
        enriched_analysis = dict(analysis)
        title = str(analysis.get("title", "")).strip()
        signal = signal_index.get(title)
        if signal:
            enriched_analysis["enrichment"] = signal["enrichment"]
            enriched_analysis["memory"] = signal["memory"]
            enriched_analysis["lifecycle_state"] = signal["lifecycle_state"]
            enriched_analysis["risk_level"] = signal["risk_level"]
            enriched_analysis["support_evidence"] = signal["enrichment"].get("support_evidence", [])
        else:
            enrichment = _build_enrichment([])
            memory = _build_memory({}, [], current_date=current_date)
            enriched_analysis["enrichment"] = enrichment
            enriched_analysis["memory"] = memory
            enriched_analysis["lifecycle_state"] = "new"
            enriched_analysis["risk_level"] = "low"
            enriched_analysis["support_evidence"] = []
        enriched_analyses.append(enriched_analysis)

    lifecycle_counter = Counter(str(item.get("lifecycle_state", "new")) for item in enriched_signals)
    mainline_memory = [
        {
            "title": str(item.get("title", "")).strip(),
            "url": str(item.get("url", "")).strip(),
            "primary_domain": str(item.get("primary_domain", "unknown")).strip() or "unknown",
            "lifecycle_state": str(item.get("lifecycle_state", "new")).strip() or "new",
            "risk_level": str(item.get("risk_level", "low")).strip() or "low",
            "score": round(float(item.get("score", 0.0)), 1),
            "days_seen": int(item.get("memory", {}).get("days_seen", 1)),
            "first_seen": str(item.get("memory", {}).get("first_seen", current_date)),
            "last_seen": str(item.get("memory", {}).get("last_seen", current_date)),
            "enrichment_summary": str(item.get("enrichment", {}).get("summary", "")).strip(),
        }
        for item in sorted(
            enriched_signals,
            key=lambda raw: (
                -int(raw.get("memory", {}).get("days_seen", 1)),
                -float(raw.get("score", 0.0)),
            ),
        )[:5]
    ]

    return {
        "signals": enriched_signals,
        "analyses": enriched_analyses,
        "mainline_memory": mainline_memory,
        "lifecycle_summary": {
            "new": lifecycle_counter.get("new", 0),
            "rising": lifecycle_counter.get("rising", 0),
            "verified": lifecycle_counter.get("verified", 0),
            "fading": lifecycle_counter.get("fading", 0),
        },
        "risk_level": _report_risk_level(enriched_signals, diagnostics),
        "external_enrichment": external_metrics,
    }
