from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from auto_report.pipeline.prompt_loader import load_prompt_registry


REQUIRED_KEYS = {
    "summary": {
        "one_line_core",
        "executive_summary",
        "key_points",
        "key_insights",
        "limitations",
        "actions",
    },
    "forecast": {
        "best_case",
        "worst_case",
        "most_likely_case",
        "key_variables",
        "forecast_conclusion",
        "confidence",
    },
    "domain_briefs": {
        "title",
        "one_line_core",
        "executive_summary",
        "signals",
    },
}


def _normalize_payload(content: object) -> tuple[dict[str, object], bool]:
    if isinstance(content, dict):
        return content, True
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed, True
        except json.JSONDecodeError:
            return {}, False
    return {}, False


def _is_non_empty(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _tokens(value: object) -> set[str]:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return {token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", text) if len(token) >= 2}


def _metric_bundle(stage: str, reference: dict[str, object], candidate: object) -> dict[str, float]:
    normalized, json_valid = _normalize_payload(candidate)
    required = REQUIRED_KEYS.get(stage, set(reference.keys()))
    present = sum(1 for key in required if key in normalized)
    non_empty = sum(1 for key in required if _is_non_empty(normalized.get(key)))
    ref_tokens = _tokens(reference)
    cand_tokens = _tokens(normalized)
    keyword_recall = len(ref_tokens & cand_tokens) / len(ref_tokens) if ref_tokens else 0.0
    required_fields_score = present / len(required) if required else 1.0
    non_empty_fields_score = non_empty / len(required) if required else 1.0
    json_valid_score = 1.0 if json_valid else 0.0
    overall = round((json_valid_score + required_fields_score + non_empty_fields_score + keyword_recall) / 4, 4)
    return {
        "json_valid_score": round(json_valid_score, 4),
        "required_fields_score": round(required_fields_score, 4),
        "non_empty_fields_score": round(non_empty_fields_score, 4),
        "keyword_recall": round(keyword_recall, 4),
        "overall_score": overall,
    }


def _average_metric_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {}
    keys = rows[0].keys()
    return {
        f"{key}_avg": round(sum(row[key] for row in rows) / len(rows), 4)
        for key in keys
    }


def evaluate_prompt_dataset(root_dir: Path, dataset_path: Path) -> Path:
    registry = load_prompt_registry(root_dir)
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset_meta = payload.get("meta", {})
    if not isinstance(dataset_meta, dict):
        dataset_meta = {}
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("Prompt evaluation dataset must contain a 'cases' list")

    prompt_lookup: dict[str, dict[str, object]] = {}
    for entries in registry.values():
        for entry in entries:
            prompt_lookup[str(entry["id"])] = entry

    case_results: list[dict[str, object]] = []
    grouped_metrics: dict[tuple[str, str, str, str], list[dict[str, float]]] = defaultdict(list)

    for raw_case in cases:
        stage = str(raw_case.get("stage", "")).strip()
        reference = raw_case.get("reference", {})
        outputs = raw_case.get("outputs", [])
        evaluations: list[dict[str, object]] = []
        for raw_output in outputs:
            prompt_id = str(raw_output.get("prompt_id", "")).strip() or f"{stage}-unknown"
            version = str(raw_output.get("version", prompt_lookup.get(prompt_id, {}).get("version", "unknown"))).strip()
            model = str(raw_output.get("model", "offline-dataset")).strip()
            metrics = _metric_bundle(stage, reference if isinstance(reference, dict) else {}, raw_output.get("content"))
            prompt_meta = prompt_lookup.get(prompt_id, {})
            evaluation = {
                "prompt_id": prompt_id,
                "version": version,
                "stage": stage,
                "model": model,
                "tags": prompt_meta.get("tags", []),
                "metrics": metrics,
            }
            evaluations.append(evaluation)
            grouped_metrics[(stage, prompt_id, version, model)].append(metrics)

        case_results.append(
            {
                "case_id": str(raw_case.get("id", "")).strip() or f"{stage}-case",
                "stage": stage,
                "evaluations": evaluations,
            }
        )

    leaderboard: list[dict[str, object]] = []
    for (stage, prompt_id, version, model), rows in grouped_metrics.items():
        prompt_meta = prompt_lookup.get(prompt_id, {})
        leaderboard.append(
            {
                "stage": stage,
                "prompt_id": prompt_id,
                "version": version,
                "model": model,
                "tags": prompt_meta.get("tags", []),
                "case_count": len(rows),
                "metrics": _average_metric_rows(rows),
            }
        )

    leaderboard.sort(
        key=lambda item: (
            -float(item["metrics"].get("overall_score_avg", 0.0)),
            item["stage"],
            item["prompt_id"],
        )
    )

    result_payload = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "dataset_path": str(dataset_path),
        "dataset_meta": dataset_meta,
        "summary": {
            "case_count": len(case_results),
            "evaluation_count": sum(len(case["evaluations"]) for case in case_results),
            "stage_count": len({case["stage"] for case in case_results}),
        },
        "leaderboard": leaderboard,
        "cases": case_results,
    }

    out_dir = root_dir / "out" / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"prompt-eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PromptEval] Wrote results to {output_path}")
    return output_path
