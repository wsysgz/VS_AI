from __future__ import annotations


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("/", "-")


def build_review_issue_candidates(payload: dict[str, object], limit: int = 3) -> list[dict[str, object]]:
    signal_lookup: dict[tuple[str, str], dict[str, object]] = {}
    for raw_signal in payload.get("signals", []):
        if not isinstance(raw_signal, dict):
            continue
        key = (
            str(raw_signal.get("title", "")).strip(),
            str(raw_signal.get("url", "")).strip(),
        )
        signal_lookup[key] = raw_signal

    candidates: list[tuple[int, float, dict[str, object]]] = []
    for raw_analysis in payload.get("analyses", []):
        if not isinstance(raw_analysis, dict):
            continue
        title = str(raw_analysis.get("title", "")).strip()
        url = str(raw_analysis.get("url", "")).strip()
        if not title or not url:
            continue

        signal = signal_lookup.get((title, url), {})
        score = float(signal.get("score", 0.0))
        risk_level = str(raw_analysis.get("risk_level", signal.get("risk_level", "low"))).strip() or "low"
        lifecycle_state = str(
            raw_analysis.get("lifecycle_state", signal.get("lifecycle_state", "new"))
        ).strip() or "new"
        support_evidence = raw_analysis.get("support_evidence", [])
        has_external_support = any(
            isinstance(item, dict) and str(item.get("evidence_scope", "")).strip() == "external"
            for item in support_evidence
        )

        priority = 0
        if score >= 3.0:
            priority += 2
        if risk_level == "high":
            priority += 3
        elif risk_level == "medium":
            priority += 2
        if lifecycle_state in {"new", "rising"}:
            priority += 1
        if not has_external_support:
            priority += 1

        if priority < 4:
            continue

        evidence_lines = [
            f"- {item.get('source_type', 'unknown')} | {item.get('title', '')} | {item.get('url', '')}"
            for item in support_evidence[:5]
            if isinstance(item, dict)
        ] or ["- None"]

        body = "\n".join(
            [
                f"Title: {title}",
                f"URL: {url}",
                f"Domain: {raw_analysis.get('primary_domain', signal.get('primary_domain', 'unknown'))}",
                f"Score: {score:.1f}",
                f"Risk level: {risk_level}",
                f"Lifecycle: {lifecycle_state}",
                f"Confidence: {raw_analysis.get('confidence', 'low')}",
                "",
                "Core insight:",
                str(raw_analysis.get("core_insight", "")).strip() or "-",
                "",
                "Primary contradiction:",
                str(raw_analysis.get("primary_contradiction", "")).strip() or "-",
                "",
                "Enrichment summary:",
                str(raw_analysis.get("enrichment", {}).get("summary", "")).strip() or "-",
                "",
                "Support evidence:",
                *evidence_lines,
            ]
        )

        domain = str(raw_analysis.get("primary_domain", signal.get("primary_domain", "unknown"))).strip() or "unknown"
        issue = {
            "title": f"[V7 review] {title}",
            "body": body,
            "labels": [
                "review",
                "high-value",
                f"risk-{_normalize_label(risk_level)}",
                f"domain-{_normalize_label(domain)}",
            ],
            "meta": {
                "title": title,
                "url": url,
                "score": round(score, 1),
                "risk_level": risk_level,
                "lifecycle_state": lifecycle_state,
                "has_external_support": has_external_support,
            },
        }
        candidates.append((priority, score, issue))

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]["title"]))
    return [item[2] for item in candidates[:limit]]
