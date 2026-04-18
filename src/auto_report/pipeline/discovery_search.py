from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from auto_report.integrations.llm_client import call_llm, get_llm_metrics, reset_llm_metrics


def load_keywords(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def build_discovery_prompt(keyword: str) -> str:
    return "\n\n".join(
        [
            "你是来源探索助手。基于给定关键词，整理可能的官方来源、feed 候选、RSSHub 候选或 changedetection 候选。",
            "只输出一个 JSON 对象。",
            '输出字段必须包含：{"summary":"...","candidates":[{"title":"...","url":"...","classification":"official-site|official-feed|rsshub-candidate|changedetection-candidate|ignore","confidence":"low|medium|high","feed_candidate":"...","rsshub_candidate":"...","changedetection_candidate":"...","next_action":"..."}]}',
            f"关键词：{keyword}",
        ]
    )


def parse_discovery_response(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Discovery response must be a JSON object")

    summary = str(payload.get("summary", "")).strip()
    raw_candidates = payload.get("candidates", [])
    candidates = raw_candidates if isinstance(raw_candidates, list) else []
    normalized_candidates: list[dict[str, str]] = []
    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        normalized_candidates.append(
            {
                "title": str(raw.get("title", "")).strip(),
                "url": str(raw.get("url", "")).strip(),
                "classification": str(raw.get("classification", "ignore")).strip() or "ignore",
                "confidence": str(raw.get("confidence", "low")).strip() or "low",
                "feed_candidate": str(raw.get("feed_candidate", "")).strip(),
                "rsshub_candidate": str(raw.get("rsshub_candidate", "")).strip(),
                "changedetection_candidate": str(raw.get("changedetection_candidate", "")).strip(),
                "next_action": str(raw.get("next_action", "")).strip(),
            }
        )

    return {
        "summary": summary,
        "candidates": normalized_candidates,
    }


def _render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Discovery Search Helper",
        "",
        f"- Generated at: {payload.get('generated_at', '-')}",
        f"- Provider: {payload.get('provider', '-')}",
        f"- Model: {payload.get('model', '-')}",
        f"- Keywords path: {payload.get('keywords_path', '-')}",
        f"- Keyword count: {payload.get('keyword_count', 0)}",
        "",
    ]

    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []

    for item in items:
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                f"## {item.get('keyword', '-')}",
                "",
                str(item.get("summary", "")).strip() or "-",
                "",
                "| title | classification | confidence | url | next_action |",
                "|---|---|---|---|---|",
            ]
        )
        candidates = item.get("candidates", [])
        if isinstance(candidates, list) and candidates:
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                lines.append(
                    f"| {candidate.get('title', '')} | {candidate.get('classification', '')} | {candidate.get('confidence', '')} | {candidate.get('url', '')} | {candidate.get('next_action', '')} |"
                )
        else:
            lines.append("| - | - | - | - | - |")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_discovery_search_artifact(root_dir: Path, keywords_path: Path) -> Path:
    load_dotenv(root_dir / ".env", override=False)
    keywords = load_keywords(keywords_path)
    reset_llm_metrics()

    items: list[dict[str, object]] = []
    for keyword in keywords:
        prompt = build_discovery_prompt(keyword)
        parsed = parse_discovery_response(call_llm(prompt, stage="search"))
        items.append(
            {
                "keyword": keyword,
                "summary": parsed["summary"],
                "candidates": parsed["candidates"],
            }
        )

    metrics = get_llm_metrics()
    output_dir = root_dir / "out" / "discovery-search"
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": metrics.get("stage_breakdown", {}).get("search", {}).get("provider", metrics.get("provider", "")),
        "model": metrics.get("stage_breakdown", {}).get("search", {}).get("model", metrics.get("model", "")),
        "keywords_path": str(keywords_path),
        "keyword_count": len(keywords),
        "items": items,
    }

    json_path = output_dir / "discovery-search.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_path = output_dir / "discovery-search.md"
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")

    return json_path
