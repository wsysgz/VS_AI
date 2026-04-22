from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from auto_report.outputs.source_governance import build_source_governance_artifact


SIDE_CAR_STATE_PATH = Path("data") / "state" / "feishu-sidecar.json"
DELIVERY_AUDIT_REVIEW_PATH = Path("data") / "state" / "delivery-audit-review.json"
OPS_DESK_SNAPSHOT_PATH = Path("out") / "feishu-ops" / "latest-sync.json"
OPS_DESK_BASE_NAME = "VS_AI Ops Desk"
OPS_DESK_DASHBOARD_NAME = "VS_AI 今日运营台"
DASHBOARD_LAYOUT_VERSION = 2
OPS_DESK_LEGACY_TABLE_NAMES = {"Lead Review", "Delivery Audit", "Candidate Updates", "数据表"}
OPS_DESK_LEGACY_DASHBOARD_NAMES = {"VS_AI Ops Desk"}
OPS_DESK_LEGACY_TABLE_RENAMES = {
    "Lead Review": "旧版审批协作（停用）",
    "Delivery Audit": "旧版交付验收（停用）",
    "Candidate Updates": "旧版待应用变更（停用）",
    "数据表": "默认空表（停用）",
}
OPS_DESK_LEGACY_DASHBOARD_RENAMES = {
    "VS_AI Ops Desk": "旧版运营台（停用）",
}
LEAD_REVIEW_STATUS_DISPLAY = {
    "pending": "待审批",
    "approved": "已批准",
    "rejected": "已拒绝",
    "deferred": "已延后",
}
LEAD_REVIEW_STATUS_REPO = {value: key for key, value in LEAD_REVIEW_STATUS_DISPLAY.items()}
OPS_DESK_TABLE_SPECS = {
    "governance_main": {
        "name": "治理总表",
        "key_field": "source_id",
        "fields": [
            "source_id",
            "priority_label",
            "watch_status",
            "priority_score",
            "candidate_kind",
            "next_action",
            "replacement_target",
            "stability_tier",
            "watch_strategy",
            "automation_ready",
            "category_hint",
            "url",
            "updated_at",
        ],
        "field_labels": {
            "source_id": "来源 ID",
            "priority_label": "优先级",
            "watch_status": "监控状态",
            "priority_score": "优先分",
            "candidate_kind": "候选类型",
            "next_action": "下一步动作",
            "replacement_target": "替代目标",
            "stability_tier": "稳定层级",
            "watch_strategy": "监控策略",
            "automation_ready": "自动化准备",
            "category_hint": "领域",
            "url": "链接",
            "updated_at": "更新时间",
        },
        "views": [
            {"name": "高优先级来源", "fields": ["source_id", "priority_label", "watch_status", "candidate_kind", "next_action", "replacement_target", "updated_at"], "filter": ("priority_label", "==", "high")},
            {"name": "阻塞来源", "fields": ["source_id", "watch_status", "next_action", "replacement_target", "updated_at"], "filter": ("watch_status", "==", "blocked")},
            {"name": "人工复核来源", "fields": ["source_id", "candidate_kind", "next_action", "replacement_target", "updated_at"], "filter": ("candidate_kind", "==", "manual_replace")},
            {"name": "候选替换来源", "fields": ["source_id", "candidate_kind", "replacement_target", "next_action", "updated_at"], "filter": None},
        ],
        "writable_fields": set(),
    },
    "lead_review": {
        "name": "审批协作",
        "key_field": "lead_key",
        "fields": [
            "title",
            "status",
            "note",
            "priority_label",
            "keyword",
            "bucket",
            "updated_at",
            "lead_key",
            "priority_score",
        ],
        "field_labels": {
            "title": "标题",
            "status": "状态",
            "note": "备注",
            "priority_label": "优先级",
            "keyword": "关键词",
            "bucket": "来源桶",
            "updated_at": "更新时间",
            "lead_key": "线索键",
            "priority_score": "优先分",
        },
        "views": [
            {"name": "待审批", "fields": ["title", "status", "note", "priority_label", "keyword", "bucket", "updated_at", "lead_key"], "filter": ("status", "==", "待审批")},
            {"name": "已批准", "fields": ["title", "status", "note", "priority_label", "keyword", "updated_at"], "filter": ("status", "==", "已批准")},
            {"name": "已延后", "fields": ["title", "status", "note", "priority_label", "keyword", "updated_at"], "filter": ("status", "==", "已延后")},
            {"name": "最近更新", "fields": ["title", "status", "note", "priority_label", "keyword", "bucket", "updated_at", "lead_key"], "filter": None},
        ],
        "field_types": {
            "status": {
                "type": "select",
                "options": [{"name": value} for value in LEAD_REVIEW_STATUS_DISPLAY.values()],
            }
        },
        "writable_fields": {"status", "note"},
    },
    "delivery_audit": {
        "name": "交付验收",
        "key_field": "generated_at",
        "fields": [
            "generated_at",
            "publication_mode",
            "feishu_status",
            "card_verified",
            "fallback_observed",
            "delivery_note",
            "risk_level",
            "feishu_message_id",
            "trace_url",
            "pushplus_status",
            "telegram_status",
            "reviewer",
        ],
        "field_labels": {
            "generated_at": "生成时间",
            "publication_mode": "发布轨",
            "feishu_status": "飞书状态",
            "card_verified": "卡片已确认",
            "fallback_observed": "发现回退",
            "delivery_note": "验收备注",
            "risk_level": "风险等级",
            "feishu_message_id": "飞书消息 ID",
            "trace_url": "Trace 链接",
            "pushplus_status": "PushPlus 状态",
            "telegram_status": "Telegram 状态",
            "reviewer": "审核人",
        },
        "views": [
            {"name": "待验收", "fields": ["generated_at", "publication_mode", "feishu_status", "card_verified", "fallback_observed", "delivery_note", "risk_level"], "filter": ("card_verified", "!=", "true")},
            {"name": "最近交付", "fields": ["generated_at", "publication_mode", "feishu_status", "card_verified", "fallback_observed", "delivery_note", "risk_level"], "filter": None},
            {"name": "发现回退", "fields": ["generated_at", "publication_mode", "feishu_status", "fallback_observed", "delivery_note", "risk_level"], "filter": ("fallback_observed", "==", "true")},
            {"name": "已确认卡片", "fields": ["generated_at", "publication_mode", "feishu_status", "card_verified", "delivery_note", "risk_level"], "filter": ("card_verified", "==", "true")},
        ],
        "field_types": {
            "card_verified": {"type": "checkbox"},
            "fallback_observed": {"type": "checkbox"},
        },
        "writable_fields": {"card_verified", "fallback_observed", "delivery_note"},
    },
    "candidate_updates": {
        "name": "待应用变更",
        "key_field": "update_key",
        "fields": [
            "source_id",
            "summary",
            "update_type",
            "apply_ready",
            "blocking_reason",
            "validation_mode",
            "generated_at",
            "update_key",
        ],
        "field_labels": {
            "source_id": "来源 ID",
            "summary": "变更摘要",
            "update_type": "变更类型",
            "apply_ready": "可应用",
            "blocking_reason": "阻塞原因",
            "validation_mode": "校验模式",
            "generated_at": "生成时间",
            "update_key": "变更键",
        },
        "views": [
            {"name": "待应用变更", "fields": ["source_id", "summary", "update_type", "apply_ready", "blocking_reason", "validation_mode", "generated_at"], "filter": None},
            {"name": "可应用", "fields": ["source_id", "summary", "update_type", "apply_ready", "validation_mode", "generated_at"], "filter": ("apply_ready", "==", "true")},
            {"name": "有阻塞", "fields": ["source_id", "summary", "blocking_reason", "validation_mode", "generated_at"], "filter": ("blocking_reason", "!=", "")},
            {"name": "仅查看", "fields": ["source_id", "summary", "update_type", "apply_ready", "blocking_reason", "validation_mode", "generated_at"], "filter": None},
        ],
        "writable_fields": set(),
    },
}


def _normalize_publication_mode(publication_mode: str) -> str:
    return "reviewed" if str(publication_mode).strip().lower() == "reviewed" else "auto"


def _summary_track_stem(publication_mode: str) -> str:
    return f"latest-summary-{_normalize_publication_mode(publication_mode)}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sidecar_state_file(root_dir: Path) -> Path:
    return root_dir / SIDE_CAR_STATE_PATH


def _load_sidecar_state(root_dir: Path) -> dict[str, Any]:
    return _load_json(_sidecar_state_file(root_dir))


def _save_sidecar_state(root_dir: Path, state: dict[str, Any]) -> None:
    state_path = _sidecar_state_file(root_dir)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _delivery_audit_review_file(root_dir: Path) -> Path:
    return root_dir / DELIVERY_AUDIT_REVIEW_PATH


def _load_delivery_audit_review(root_dir: Path) -> dict[str, Any]:
    path = _delivery_audit_review_file(root_dir)
    payload = _load_json(path)
    if payload:
        return payload
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "items": [],
    }


def _save_ops_desk_snapshot(root_dir: Path, payload: dict[str, Any], sync_state: dict[str, Any]) -> None:
    snapshot_path = root_dir / OPS_DESK_SNAPSHOT_PATH
    _save_json(
        snapshot_path,
        _json_safe(
            {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "payload": payload,
            "sync_state": sync_state,
            }
        ),
    )


def _run_lark_cli(settings, args: list[str], root_dir: Path | None = None) -> object:
    executable = str(settings.env.get("LARK_CLI_PATH", "")).strip() or "lark-cli"
    profile = str(settings.env.get("LARK_CLI_PROFILE", "")).strip()
    command = [executable]
    if profile:
        command.extend(["--profile", profile])
    command.extend(args)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            cwd=str(root_dir) if root_dir else None,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(detail or f"lark-cli failed: {' '.join(command)}") from exc
    stdout = (completed.stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw_output": stdout}


def _find_first_string(payload: object, candidate_keys: set[str]) -> str:
    if isinstance(payload, dict):
        for key in candidate_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in payload.values():
            found = _find_first_string(value, candidate_keys)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_first_string(item, candidate_keys)
            if found:
                return found
    return ""


def _read_report_markdown(root_dir: Path, publication_mode: str) -> tuple[Path, str]:
    reports_dir = root_dir / "data" / "reports"
    track_path = reports_dir / f"{_summary_track_stem(publication_mode)}.md"
    fallback_path = reports_dir / "latest-summary.md"
    report_path = track_path if track_path.exists() else fallback_path
    return report_path, report_path.read_text(encoding="utf-8")


def _report_generated_at(root_dir: Path) -> str:
    status = _load_json(root_dir / "data" / "state" / "run-status.json")
    generated_at = str(status.get("generated_at", "")).strip()
    return generated_at or datetime.now().astimezone().isoformat(timespec="seconds")


def _build_report_doc_title(root_dir: Path, publication_mode: str) -> str:
    generated_at = _report_generated_at(root_dir)
    date_part = generated_at[:10] if generated_at else datetime.now().date().isoformat()
    mode_label = "人工复核版" if _normalize_publication_mode(publication_mode) == "reviewed" else "自动版"
    return f"VS_AI 飞书日报 | {mode_label} | {date_part}"


def _write_markdown_tempfile(root_dir: Path, content: str) -> str:
    temp_path = root_dir / "data" / "state" / "feishu-sidecar-report.tmp.md"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(content, encoding="utf-8")
    return f".\\{temp_path.relative_to(root_dir)}"


def _excel_column_name(index: int) -> str:
    value = index
    result = ""
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def _governance_sheet_values(governance_payload: dict[str, Any]) -> list[list[object]]:
    priority_queue = governance_payload.get("source_governance", {}).get("priority_queue", [])
    headers = [
        "source_id",
        "priority_label",
        "priority_score",
        "candidate_kind",
        "next_action",
        "replacement_target",
        "url",
    ]
    rows = [headers]
    for item in priority_queue:
        if not isinstance(item, dict):
            continue
        rows.append(
            [
                str(item.get("source_id", "")),
                str(item.get("priority_label", "")),
                int(item.get("priority_score", 0) or 0),
                str(item.get("candidate_kind", "")),
                str(item.get("next_action", "")),
                str(item.get("replacement_target", "")),
                str(item.get("url", "")),
            ]
        )
    return rows


def _governance_task_description(item: dict[str, Any]) -> str:
    lines = [
        f"source_id: {item.get('source_id', '')}",
        f"priority: {item.get('priority_label', '')} ({item.get('priority_score', 0)})",
        f"candidate_kind: {item.get('candidate_kind', '')}",
        f"next_action: {item.get('next_action', '')}",
        f"replacement_target: {item.get('replacement_target', '')}",
        f"url: {item.get('url', '')}",
    ]
    return "\n".join(lines)


def _load_governance_payload(root_dir: Path) -> dict[str, Any]:
    artifact_path = root_dir / "out" / "source-governance" / "source-governance.json"
    payload = _load_json(artifact_path)
    if payload:
        return payload
    return _load_json(build_source_governance_artifact(root_dir))


def _coerce_cell_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _build_governance_main_table(governance_payload: dict[str, Any]) -> dict[str, Any]:
    items = governance_payload.get("source_governance", {}).get("priority_queue", [])
    watch_lookup: dict[str, str] = {}
    registry_items = governance_payload.get("changedetection_watch_registry", {}).get("items", [])
    if isinstance(registry_items, list):
        for item in registry_items:
            if isinstance(item, dict):
                source_id = _coerce_cell_value(item.get("source_id", ""))
                if source_id:
                    watch_lookup[source_id] = _coerce_cell_value(item.get("status", ""))
    records: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = _coerce_cell_value(item.get("source_id", ""))
        records.append(
            {
                "source_id": source_id,
                "priority_label": _coerce_cell_value(item.get("priority_label", "")),
                "watch_status": watch_lookup.get(source_id, ""),
                "priority_score": _coerce_cell_value(item.get("priority_score", "")),
                "candidate_kind": _coerce_cell_value(item.get("candidate_kind", "")),
                "next_action": _coerce_cell_value(item.get("next_action", "")),
                "replacement_target": _coerce_cell_value(item.get("replacement_target", "")),
                "stability_tier": _coerce_cell_value(item.get("stability_tier", "")),
                "watch_strategy": _coerce_cell_value(item.get("watch_strategy", "")),
                "automation_ready": _coerce_cell_value(item.get("automation_ready", "")),
                "category_hint": _coerce_cell_value(item.get("category_hint", "")),
                "url": _coerce_cell_value(item.get("url", "")),
                "updated_at": _coerce_cell_value(governance_payload.get("generated_at", "")),
            }
        )
    return {
        **OPS_DESK_TABLE_SPECS["governance_main"],
        "records": records,
    }


def _build_lead_review_table(review_payload: dict[str, Any]) -> dict[str, Any]:
    items = review_payload.get("items", [])
    records: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record = {field: _coerce_cell_value(item.get(field, "")) for field in OPS_DESK_TABLE_SPECS["lead_review"]["fields"]}
        record["status"] = LEAD_REVIEW_STATUS_DISPLAY.get(record["status"], record["status"])
        records.append(record)
    return {
        **OPS_DESK_TABLE_SPECS["lead_review"],
        "records": records,
    }


def _build_candidate_updates_table(candidate_payload: dict[str, Any]) -> dict[str, Any]:
    generated_at = candidate_payload.get("generated_at", "")
    items = candidate_payload.get("updates", [])
    records: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "update_key": _coerce_cell_value(item.get("update_key", "")),
                "source_id": _coerce_cell_value(item.get("source_id", "")),
                "update_type": _coerce_cell_value(item.get("update_type", "")),
                "summary": _coerce_cell_value(item.get("summary", "")),
                "apply_ready": _coerce_cell_value(item.get("apply_ready", "")),
                "blocking_reason": _coerce_cell_value(item.get("blocking_reason", "")),
                "validation_mode": _coerce_cell_value(item.get("validation_mode", "")),
                "generated_at": _coerce_cell_value(item.get("generated_at", generated_at)),
            }
        )
    return {
        **OPS_DESK_TABLE_SPECS["candidate_updates"],
        "records": records,
    }


def _build_delivery_audit_table(run_status_payload: dict[str, Any], review_payload: dict[str, Any]) -> dict[str, Any]:
    generated_at = _coerce_cell_value(run_status_payload.get("generated_at", ""))
    review_items = review_payload.get("items", [])
    review_item = {}
    if isinstance(review_items, list):
        for item in review_items:
            if isinstance(item, dict) and _coerce_cell_value(item.get("generated_at", "")) == generated_at:
                review_item = item
                break
    channels = run_status_payload.get("delivery_results", {}).get("channels", {})
    feishu_summary = run_status_payload.get("push_response", {}).get("feishu", {})
    reviewer = run_status_payload.get("review", {}).get("reviewer", "")
    message_ids = feishu_summary.get("message_ids", []) if isinstance(feishu_summary, dict) else []
    record = {
        "generated_at": generated_at,
        "publication_mode": _coerce_cell_value(run_status_payload.get("publication_mode", "")),
        "risk_level": _coerce_cell_value(run_status_payload.get("risk_level", "")),
        "feishu_status": _coerce_cell_value(channels.get("feishu", {}).get("status", "")),
        "feishu_message_id": _coerce_cell_value(message_ids[0] if isinstance(message_ids, list) and message_ids else ""),
        "pushplus_status": _coerce_cell_value(channels.get("pushplus", {}).get("status", "")),
        "telegram_status": _coerce_cell_value(channels.get("telegram", {}).get("status", "")),
        "card_verified": _coerce_cell_value(review_item.get("card_verified", "")),
        "fallback_observed": _coerce_cell_value(review_item.get("fallback_observed", "")),
        "delivery_note": _coerce_cell_value(review_item.get("delivery_note", "")),
        "reviewer": _coerce_cell_value(reviewer),
        "trace_url": _coerce_cell_value(run_status_payload.get("tracing", {}).get("trace_url", "")),
    }
    return {
        **OPS_DESK_TABLE_SPECS["delivery_audit"],
        "records": [record] if generated_at else [],
    }


def _build_ops_desk_payload(root_dir: Path) -> dict[str, Any]:
    governance_payload = _load_governance_payload(root_dir)
    lead_review_payload = _load_json(root_dir / "out" / "review-queue" / "source-lead-review-status.json")
    candidate_updates_payload = _load_json(root_dir / "out" / "review-queue" / "candidate-updates.json")
    run_status_payload = _load_json(root_dir / "data" / "state" / "run-status.json")
    delivery_review_payload = _load_delivery_audit_review(root_dir)
    return {
        "governance_main": _build_governance_main_table(governance_payload),
        "lead_review": _build_lead_review_table(lead_review_payload),
        "delivery_audit": _build_delivery_audit_table(run_status_payload, delivery_review_payload),
        "candidate_updates": _build_candidate_updates_table(candidate_updates_payload),
    }


def _display_field_name(table_payload: dict[str, Any], internal_name: str) -> str:
    labels = table_payload.get("field_labels", {})
    if isinstance(labels, dict):
        return _coerce_cell_value(labels.get(internal_name, internal_name))
    return internal_name


def _internal_field_name(table_payload: dict[str, Any], display_name: str) -> str:
    labels = table_payload.get("field_labels", {})
    if isinstance(labels, dict):
        for internal, display in labels.items():
            if _coerce_cell_value(display) == display_name:
                return internal
    return display_name


def _to_display_record(table_payload: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return {
        _display_field_name(table_payload, key): value
        for key, value in record.items()
    }


def _resolve_actual_field_name_map(table_payload: dict[str, Any], field_meta: dict[str, dict[str, str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for internal_name in table_payload.get("fields", []):
        display_name = _display_field_name(table_payload, internal_name)
        if display_name in field_meta:
            mapping[internal_name] = display_name
        elif internal_name in field_meta:
            mapping[internal_name] = internal_name
        else:
            mapping[internal_name] = display_name
    return mapping


def _desired_field_payload(table_payload: dict[str, Any], internal_name: str, current_type: str = "text") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": _display_field_name(table_payload, internal_name),
        "type": current_type or "text",
    }
    field_types = table_payload.get("field_types", {})
    if isinstance(field_types, dict) and internal_name in field_types and isinstance(field_types[internal_name], dict):
        payload.update(field_types[internal_name])
    return payload


def _payload_items(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        data = payload.get("data")
        if isinstance(data, dict):
            return _payload_items(data)
        for value in payload.values():
            if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
                return [item for item in value if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _extract_record_fields(item: dict[str, Any]) -> dict[str, Any]:
    fields = item.get("fields")
    if isinstance(fields, dict):
        return fields
    return item


def _list_base_tables(settings, base_token: str) -> dict[str, dict[str, Any]]:
    response = _run_lark_cli(settings, ["base", "+table-list", "--base-token", base_token])
    tables: dict[str, dict[str, Any]] = {}
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            raw_tables = data.get("tables")
            if isinstance(raw_tables, list):
                for item in raw_tables:
                    if not isinstance(item, dict):
                        continue
                    name = _coerce_cell_value(item.get("name", ""))
                    if not name:
                        continue
                    tables[name] = {
                        "table_id": _coerce_cell_value(item.get("table_id", item.get("id", ""))),
                        "name": name,
                    }
                return tables
    for item in _payload_items(response):
        name = _coerce_cell_value(item.get("name", ""))
        if not name:
            continue
        tables[name] = {
            "table_id": _coerce_cell_value(item.get("table_id", item.get("id", ""))),
            "name": name,
        }
    return tables


def _list_table_fields(settings, base_token: str, table_id: str) -> dict[str, dict[str, str]]:
    response = _run_lark_cli(settings, ["base", "+field-list", "--base-token", base_token, "--table-id", table_id])
    names: dict[str, dict[str, str]] = {}
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            fields = data.get("fields")
            if isinstance(fields, list):
                for item in fields:
                    if not isinstance(item, dict):
                        continue
                    name = _coerce_cell_value(item.get("name", item.get("field_name", "")))
                    field_id = _coerce_cell_value(item.get("id", item.get("field_id", "")))
                    field_type = _coerce_cell_value(item.get("type", "text")) or "text"
                    if name:
                        names[name] = {"id": field_id, "type": field_type}
                return names
    for item in _payload_items(response):
        name = _coerce_cell_value(item.get("name", item.get("field_name", "")))
        field_id = _coerce_cell_value(item.get("id", item.get("field_id", "")))
        field_type = _coerce_cell_value(item.get("type", "text")) or "text"
        if name:
            names[name] = {"id": field_id, "type": field_type}
    return names


def _list_table_records(settings, base_token: str, table_id: str) -> list[dict[str, Any]]:
    response = _run_lark_cli(settings, ["base", "+record-list", "--base-token", base_token, "--table-id", table_id])
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            rows = data.get("data")
            field_names = data.get("fields")
            record_ids = data.get("record_id_list")
            if isinstance(rows, list) and isinstance(field_names, list) and isinstance(record_ids, list):
                items: list[dict[str, Any]] = []
                for idx, row in enumerate(rows):
                    if not isinstance(row, list):
                        continue
                    fields = {
                        _coerce_cell_value(field_names[i]): row[i]
                        for i in range(min(len(field_names), len(row)))
                    }
                    items.append(
                        {
                            "record_id": _coerce_cell_value(record_ids[idx] if idx < len(record_ids) else ""),
                            "fields": fields,
                        }
                    )
                return items
    return _payload_items(response)


def _list_dashboards(settings, base_token: str) -> dict[str, dict[str, Any]]:
    response = _run_lark_cli(settings, ["base", "+dashboard-list", "--base-token", base_token])
    dashboards: dict[str, dict[str, Any]] = {}
    for item in _payload_items(response):
        name = _coerce_cell_value(item.get("name", ""))
        if not name:
            continue
        dashboards[name] = {
            "dashboard_id": _coerce_cell_value(item.get("dashboard_id", item.get("id", ""))),
            "url": _coerce_cell_value(item.get("url", "")),
            "name": name,
        }
    return dashboards


def _cleanup_legacy_ops_desk_resources(settings, base_token: str, table_state: dict[str, Any], dashboard_meta: dict[str, Any]) -> None:
    current_table_ids = {
        _coerce_cell_value(meta.get("table_id", ""))
        for meta in table_state.values()
        if isinstance(meta, dict)
    }
    listed_tables = _list_base_tables(settings, base_token)
    for name, meta in listed_tables.items():
        table_id = _coerce_cell_value(meta.get("table_id", ""))
        if not table_id or table_id in current_table_ids:
            continue
        if name in OPS_DESK_LEGACY_TABLE_NAMES:
            try:
                _run_lark_cli(
                    settings,
                    [
                        "base",
                        "+table-delete",
                        "--base-token",
                        base_token,
                        "--table-id",
                        table_id,
                        "--yes",
                    ],
                )
            except RuntimeError:
                _run_lark_cli(
                    settings,
                    [
                        "base",
                        "+table-update",
                        "--base-token",
                        base_token,
                        "--table-id",
                        table_id,
                        "--name",
                        OPS_DESK_LEGACY_TABLE_RENAMES.get(name, f"旧版{name}（停用）"),
                    ],
                )

    current_dashboard_id = _coerce_cell_value(dashboard_meta.get("dashboard_id", ""))
    listed_dashboards = _list_dashboards(settings, base_token)
    for name, meta in listed_dashboards.items():
        dashboard_id = _coerce_cell_value(meta.get("dashboard_id", ""))
        if not dashboard_id or dashboard_id == current_dashboard_id:
            continue
        if name in OPS_DESK_LEGACY_DASHBOARD_NAMES:
            try:
                _run_lark_cli(
                    settings,
                    [
                        "base",
                        "+dashboard-delete",
                        "--base-token",
                        base_token,
                        "--dashboard-id",
                        dashboard_id,
                        "--yes",
                    ],
                )
            except RuntimeError:
                _run_lark_cli(
                    settings,
                    [
                        "base",
                        "+dashboard-update",
                        "--base-token",
                        base_token,
                        "--dashboard-id",
                        dashboard_id,
                        "--name",
                        OPS_DESK_LEGACY_DASHBOARD_RENAMES.get(name, f"旧版{name}（停用）"),
                    ],
                )


def _list_views(settings, base_token: str, table_id: str) -> dict[str, dict[str, Any]]:
    response = _run_lark_cli(settings, ["base", "+view-list", "--base-token", base_token, "--table-id", table_id])
    views: dict[str, dict[str, Any]] = {}
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            raw_views = data.get("views")
            if isinstance(raw_views, list):
                for item in raw_views:
                    if not isinstance(item, dict):
                        continue
                    name = _coerce_cell_value(item.get("name", ""))
                    if name:
                        views[name] = {
                            "view_id": _coerce_cell_value(item.get("id", item.get("view_id", ""))),
                            "name": name,
                        }
                return views
    for item in _payload_items(response):
        name = _coerce_cell_value(item.get("name", ""))
        if name:
            views[name] = {
                "view_id": _coerce_cell_value(item.get("id", item.get("view_id", ""))),
                "name": name,
            }
    return views


def _list_dashboard_blocks(settings, base_token: str, dashboard_id: str) -> list[dict[str, Any]]:
    response = _run_lark_cli(settings, ["base", "+dashboard-block-list", "--base-token", base_token, "--dashboard-id", dashboard_id])
    blocks: list[dict[str, Any]] = []
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            raw_items = data.get("items")
            if isinstance(raw_items, list):
                return [item for item in raw_items if isinstance(item, dict)]
    return _payload_items(response)


def _apply_view_visible_fields(settings, base_token: str, table_id: str, view_name: str, field_ids: list[str]) -> None:
    _run_lark_cli(
        settings,
        [
            "base",
            "+view-set-visible-fields",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--view-id",
            view_name,
            "--json",
            json.dumps({"visible_fields": field_ids}, ensure_ascii=False),
        ],
    )


def _apply_view_filter(settings, base_token: str, table_id: str, view_name: str, field_id: str, operator: str, value: str) -> None:
    _run_lark_cli(
        settings,
        [
            "base",
            "+view-set-filter",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--view-id",
            view_name,
            "--json",
            json.dumps({"logic": "and", "conditions": [[field_id, operator, value]]}, ensure_ascii=False),
        ],
    )


def _ensure_ops_desk_views(settings, base_token: str, table_meta: dict[str, Any], table_payload: dict[str, Any]) -> list[dict[str, Any]]:
    existing = _list_views(settings, base_token, table_meta["table_id"])
    if "Grid View" in existing and "全部记录" not in existing:
        try:
            _run_lark_cli(
                settings,
                [
                    "base",
                    "+view-rename",
                    "--base-token",
                    base_token,
                    "--table-id",
                    table_meta["table_id"],
                    "--view-id",
                    "Grid View",
                    "--name",
                    "全部记录",
                ],
            )
        except RuntimeError:
            pass
        existing = _list_views(settings, base_token, table_meta["table_id"])
    field_meta = _list_table_fields(settings, base_token, table_meta["table_id"])
    views: list[dict[str, Any]] = []
    for spec in table_payload.get("views", []):
        view_name = _coerce_cell_value(spec.get("name", ""))
        if not view_name:
            continue
        if view_name not in existing:
            response = _run_lark_cli(
                settings,
                [
                    "base",
                    "+view-create",
                    "--base-token",
                    base_token,
                    "--table-id",
                    table_meta["table_id"],
                    "--json",
                    json.dumps({"name": view_name, "type": "grid"}, ensure_ascii=False),
                ],
            )
            view_id = _find_first_string(response, {"id", "view_id"})
            existing[view_name] = {"view_id": view_id, "name": view_name}
        field_ids = []
        for internal_name in spec.get("fields", []):
            display_name = _display_field_name(table_payload, internal_name)
            field_info = field_meta.get(display_name) or field_meta.get(internal_name)
            if field_info:
                field_ids.append(str(field_info["id"]))
        if field_ids:
            try:
                _apply_view_visible_fields(settings, base_token, table_meta["table_id"], view_name, field_ids)
            except RuntimeError:
                pass
        filter_spec = spec.get("filter")
        if isinstance(filter_spec, tuple) and len(filter_spec) == 3:
            internal_name, operator, value = filter_spec
            display_name = _display_field_name(table_payload, str(internal_name))
            field_info = field_meta.get(display_name) or field_meta.get(str(internal_name))
            if field_info:
                try:
                    _apply_view_filter(settings, base_token, table_meta["table_id"], view_name, str(field_info["id"]), str(operator), str(value))
                except RuntimeError:
                    pass
        views.append(existing[view_name])
    return views


def _ensure_ops_desk_base(root_dir: Path, settings, ops_state: dict[str, Any]) -> dict[str, Any]:
    existing = ops_state.get("base", {}) if isinstance(ops_state.get("base"), dict) else {}
    app_token = _coerce_cell_value(existing.get("app_token", ""))
    if app_token:
        return existing
    response = _run_lark_cli(
        settings,
        [
            "base",
            "+base-create",
            "--name",
            OPS_DESK_BASE_NAME,
            "--time-zone",
            str(settings.env.get("AUTO_TIMEZONE", "Asia/Shanghai")),
        ],
        root_dir=root_dir,
    )
    return {
        "app_token": _find_first_string(response, {"app_token", "base_token", "token", "id"}),
        "url": _find_first_string(response, {"url"}),
        "name": OPS_DESK_BASE_NAME,
    }


def _ensure_ops_desk_table(settings, base_token: str, table_state: dict[str, Any], table_key: str, table_payload: dict[str, Any]) -> dict[str, Any]:
    existing = table_state.get(table_key, {}) if isinstance(table_state.get(table_key), dict) else {}
    table_id = _coerce_cell_value(existing.get("table_id", ""))
    table_name = table_payload["name"]
    if not table_id:
        listed = _list_base_tables(settings, base_token)
        table_id = _coerce_cell_value(listed.get(table_name, {}).get("table_id", ""))
    if not table_id:
        response = _run_lark_cli(
            settings,
            ["base", "+table-create", "--base-token", base_token, "--name", table_name],
        )
        table_id = _find_first_string(response, {"table_id", "id"})
    else:
        _run_lark_cli(
            settings,
            ["base", "+table-update", "--base-token", base_token, "--table-id", table_id, "--name", table_name],
        )

    field_names = _list_table_fields(settings, base_token, table_id)
    for field_name in table_payload["fields"]:
        display_name = _display_field_name(table_payload, field_name)
        field_info = field_names.get(field_name) or field_names.get(display_name)
        if field_info:
            try:
                _run_lark_cli(
                    settings,
                    [
                        "base",
                        "+field-update",
                        "--base-token",
                        base_token,
                        "--table-id",
                        table_id,
                        "--field-id",
                        str(field_info["id"]),
                        "--json",
                        json.dumps(_desired_field_payload(table_payload, field_name, field_info.get("type", "text")), ensure_ascii=False),
                    ],
                )
            except RuntimeError:
                pass
            continue
        _run_lark_cli(
            settings,
            [
                "base",
                "+field-create",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--json",
                json.dumps(_desired_field_payload(table_payload, field_name, "text"), ensure_ascii=False),
            ],
        )

    field_name_map = _resolve_actual_field_name_map(table_payload, _list_table_fields(settings, base_token, table_id))

    return {
        "table_id": table_id,
        "name": table_name,
        "key_field": table_payload["key_field"],
        "field_name_map": field_name_map,
        "record_ids": dict(existing.get("record_ids", {})) if isinstance(existing.get("record_ids"), dict) else {},
    }


def _sync_ops_desk_records(settings, base_token: str, table_meta: dict[str, Any], table_payload: dict[str, Any]) -> dict[str, str]:
    key_field = table_meta["key_field"]
    field_name_map = table_meta.get("field_name_map", {}) if isinstance(table_meta.get("field_name_map"), dict) else {}
    record_ids = dict(table_meta.get("record_ids", {})) if isinstance(table_meta.get("record_ids"), dict) else {}
    existing_records = _list_table_records(settings, base_token, table_meta["table_id"])
    duplicate_record_ids: list[str] = []
    for item in existing_records:
        fields = {
            _internal_field_name(table_payload, key): value
            for key, value in _extract_record_fields(item).items()
        }
        key = _coerce_cell_value(fields.get(key_field, ""))
        record_id = _coerce_cell_value(item.get("record_id", item.get("id", "")))
        if not key:
            continue
        if key in record_ids and record_id and record_ids[key] != record_id:
            duplicate_record_ids.append(record_id)
            continue
        if record_id:
            record_ids[key] = record_id

    for record_id in duplicate_record_ids:
        _run_lark_cli(
            settings,
            [
                "base",
                "+record-delete",
                "--base-token",
                base_token,
                "--table-id",
                table_meta["table_id"],
                "--record-id",
                record_id,
                "--yes",
            ],
        )

    for record in table_payload["records"]:
        key = _coerce_cell_value(record.get(key_field, ""))
        if not key:
            continue
        actual_record = {
            _coerce_cell_value(field_name_map.get(internal_name, _display_field_name(table_payload, internal_name))): value
            for internal_name, value in record.items()
        }
        args = [
            "base",
            "+record-upsert",
            "--base-token",
            base_token,
            "--table-id",
            table_meta["table_id"],
            "--json",
            json.dumps(actual_record, ensure_ascii=False),
        ]
        if key in record_ids and record_ids[key]:
            args.extend(["--record-id", record_ids[key]])
        response = _run_lark_cli(settings, args)
        record_id = _find_first_string(response, {"record_id", "id"}) or record_ids.get(key, "")
        if record_id:
            record_ids[key] = record_id
    return record_ids


def _ensure_ops_desk_dashboard(settings, base_token: str, ops_state: dict[str, Any], table_state: dict[str, Any]) -> dict[str, Any]:
    existing = ops_state.get("dashboard", {}) if isinstance(ops_state.get("dashboard"), dict) else {}
    dashboard_id = _coerce_cell_value(existing.get("dashboard_id", ""))
    dashboard_url = _coerce_cell_value(existing.get("url", ""))
    initialized_version = int(existing.get("layout_version", 0) or 0)
    if not dashboard_id:
        dashboards = _list_dashboards(settings, base_token)
        dashboard = dashboards.get(OPS_DESK_DASHBOARD_NAME, {})
        dashboard_id = _coerce_cell_value(dashboard.get("dashboard_id", ""))
        dashboard_url = _coerce_cell_value(dashboard.get("url", ""))
    if not dashboard_id:
        response = _run_lark_cli(
            settings,
            ["base", "+dashboard-create", "--base-token", base_token, "--name", OPS_DESK_DASHBOARD_NAME],
        )
        dashboard_id = _find_first_string(response, {"dashboard_id", "id"})
        dashboard_url = _find_first_string(response, {"url"})

    if dashboard_id and initialized_version < DASHBOARD_LAYOUT_VERSION:
        rebuild_allowed = True
        for block in _list_dashboard_blocks(settings, base_token, dashboard_id):
            block_id = _coerce_cell_value(block.get("block_id", block.get("id", "")))
            if not block_id:
                continue
            try:
                _run_lark_cli(
                    settings,
                    [
                        "base",
                        "+dashboard-block-delete",
                        "--base-token",
                        base_token,
                        "--dashboard-id",
                        dashboard_id,
                        "--block-id",
                        block_id,
                        "--yes",
                    ],
                )
            except RuntimeError:
                rebuild_allowed = False
                break
        if rebuild_allowed:
            _run_lark_cli(
                settings,
                [
                    "base",
                    "+dashboard-block-create",
                    "--base-token",
                    base_token,
                    "--dashboard-id",
                    dashboard_id,
                    "--type",
                    "text",
                    "--name",
                    "首页说明",
                    "--data-config",
                    json.dumps({"text": "VS_AI 今日运营台\n先看状态，再进入处理\n常用入口：待审批、待验收、阻塞来源、待应用变更"}, ensure_ascii=False),
                ],
            )
            for table_key, label in (
                ("delivery_audit", "飞书交付"),
                ("governance_main", "来源治理"),
                ("lead_review", "审批协作"),
                ("candidate_updates", "待应用变更"),
            ):
                _run_lark_cli(
                    settings,
                    [
                        "base",
                        "+dashboard-block-create",
                        "--base-token",
                        base_token,
                        "--dashboard-id",
                        dashboard_id,
                        "--type",
                        "statistics",
                        "--name",
                        label,
                        "--data-config",
                        json.dumps({"table_name": table_state[table_key]["name"], "count_all": True}, ensure_ascii=False),
                        "--no-validate",
                    ],
                )
            _run_lark_cli(
                settings,
                [
                    "base",
                    "+dashboard-block-create",
                    "--base-token",
                    base_token,
                    "--dashboard-id",
                    dashboard_id,
                    "--type",
                    "text",
                    "--name",
                    "今日操作建议",
                    "--data-config",
                    json.dumps({"text": "1. 先看【飞书交付】\n2. 再看【审批协作】中的待审批\n3. 如有异常，再看【来源治理】的阻塞来源"}, ensure_ascii=False),
                ],
            )

    return {
        "dashboard_id": dashboard_id,
        "url": dashboard_url,
        "name": OPS_DESK_DASHBOARD_NAME,
        "layout_version": DASHBOARD_LAYOUT_VERSION,
    }


def _sync_report_doc(root_dir: Path, settings, state: dict[str, Any], publication_mode: str) -> dict[str, Any]:
    report_path, markdown = _read_report_markdown(root_dir, publication_mode)
    title = _build_report_doc_title(root_dir, publication_mode)
    existing = state.get("report_doc", {})
    doc_ref = str(existing.get("doc_token", "")).strip() or str(existing.get("url", "")).strip()
    markdown_file = _write_markdown_tempfile(root_dir, markdown)
    try:
        if doc_ref:
            response = _run_lark_cli(
                settings,
                [
                    "docs",
                    "+update",
                    "--doc",
                    doc_ref,
                    "--mode",
                    "overwrite",
                    "--new-title",
                    title,
                    "--markdown",
                    f"@{markdown_file}",
                ],
                root_dir=root_dir,
            )
        else:
            response = _run_lark_cli(
                settings,
                [
                    "docs",
                    "+create",
                    "--title",
                    title,
                    "--wiki-space",
                    str(settings.env.get("FEISHU_DOC_WIKI_SPACE", "my_library")),
                    "--markdown",
                    f"@{markdown_file}",
                ],
                root_dir=root_dir,
            )
    finally:
        (root_dir / markdown_file.lstrip(".\\")).unlink(missing_ok=True)

    resolved_url = _find_first_string(response, {"url", "document_url", "doc_url"}) or str(existing.get("url", "")).strip()
    resolved_token = _find_first_string(response, {"document_id", "doc_token", "token"}) or resolved_url or doc_ref
    return {
        "doc_token": resolved_token,
        "url": resolved_url,
        "title": title,
        "publication_mode": _normalize_publication_mode(publication_mode),
        "report_path": str(report_path.relative_to(root_dir)),
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def _resolve_sheet_id(root_dir: Path, settings, spreadsheet_token: str, current_sheet_id: str) -> str:
    if current_sheet_id:
        return current_sheet_id
    response = _run_lark_cli(
        settings,
        [
            "sheets",
            "+info",
            "--spreadsheet-token",
            spreadsheet_token,
        ],
        root_dir=root_dir,
    )
    return _find_first_string(response, {"sheet_id", "sheetId"})


def _sync_governance_sheet(root_dir: Path, settings, state: dict[str, Any], governance_payload: dict[str, Any]) -> dict[str, Any]:
    rows = _governance_sheet_values(governance_payload)
    headers = rows[0]
    data_rows = rows[1:]
    existing = state.get("governance_sheet", {})
    spreadsheet_token = str(existing.get("spreadsheet_token", "")).strip()
    sheet_id = str(existing.get("sheet_id", "")).strip()
    title = f"VS_AI 来源治理队列 | {_report_generated_at(root_dir)[:10]}"

    if not spreadsheet_token:
        response = _run_lark_cli(
            settings,
            [
                "sheets",
                "+create",
                "--title",
                title,
                "--headers",
                json.dumps(headers, ensure_ascii=False),
                "--data",
                json.dumps(data_rows, ensure_ascii=False),
            ],
        )
        spreadsheet_token = _find_first_string(response, {"spreadsheet_token", "token"})
        sheet_id = _resolve_sheet_id(root_dir, settings, spreadsheet_token, sheet_id)
        url = _find_first_string(response, {"url", "spreadsheet_url"})
    else:
        sheet_id = _resolve_sheet_id(root_dir, settings, spreadsheet_token, sheet_id)
        final_column = _excel_column_name(len(headers))
        final_row = max(len(rows), 1)
        _run_lark_cli(
            settings,
            [
                "sheets",
                "+write",
                "--spreadsheet-token",
                spreadsheet_token,
                "--range",
                f"{sheet_id}!A1:{final_column}{final_row}",
                "--values",
                json.dumps(rows, ensure_ascii=False),
            ],
            root_dir=root_dir,
        )
        url = str(existing.get("url", "")).strip()

    return {
        "spreadsheet_token": spreadsheet_token,
        "sheet_id": sheet_id,
        "url": url,
        "row_count": len(rows),
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def _sync_governance_tasks(root_dir: Path, settings, state: dict[str, Any], governance_payload: dict[str, Any]) -> dict[str, Any]:
    existing = state.get("governance_tasks", {})
    tasklist_id = str(existing.get("tasklist_id", "")).strip()
    tasklist_url = str(existing.get("url", "")).strip()
    tasks_by_source = dict(existing.get("tasks_by_source", {}))
    priority_queue = governance_payload.get("source_governance", {}).get("priority_queue", [])
    task_limit = int(settings.env.get("FEISHU_GOVERNANCE_TASK_LIMIT", "10") or "10")
    selected_items = [item for item in priority_queue if isinstance(item, dict)][:task_limit]

    if not tasklist_id:
        response = _run_lark_cli(
            settings,
            [
                "task",
                "+tasklist-create",
                "--name",
                "VS_AI Source Governance",
            ],
            root_dir=root_dir,
        )
        tasklist_id = _find_first_string(response, {"tasklist_guid", "tasklist_id", "guid", "id"})
        tasklist_url = _find_first_string(response, {"url", "tasklist_url"})

    synced: dict[str, Any] = {}
    for item in selected_items:
        source_id = str(item.get("source_id", "")).strip()
        if not source_id:
            continue
        summary = f"[{item.get('priority_label', 'pending')}] {source_id}"
        description = _governance_task_description(item)
        current = tasks_by_source.get(source_id, {}) if isinstance(tasks_by_source.get(source_id), dict) else {}
        task_id = str(current.get("task_id", "")).strip()
        task_url = str(current.get("url", "")).strip()
        if task_id:
            response = _run_lark_cli(
                settings,
                [
                    "task",
                    "+update",
                    "--task-id",
                    task_id,
                    "--summary",
                    summary,
                    "--description",
                    description,
                ],
                root_dir=root_dir,
            )
        else:
            response = _run_lark_cli(
                settings,
                [
                    "task",
                    "+create",
                    "--tasklist-id",
                    tasklist_id,
                    "--summary",
                    summary,
                    "--description",
                    description,
                    "--idempotency-key",
                    f"vs-ai-governance-{source_id}",
                ],
                root_dir=root_dir,
            )
        task_id = _find_first_string(response, {"task_guid", "task_id", "guid", "id"}) or task_id
        task_url = _find_first_string(response, {"url", "task_url"}) or task_url
        synced[source_id] = {
            "task_id": task_id,
            "url": task_url,
            "summary": summary,
        }

    return {
        "tasklist_id": tasklist_id,
        "url": tasklist_url,
        "tasks_by_source": synced,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def _read_ops_desk_rows(settings, base_token: str, table_meta: dict[str, Any]) -> list[dict[str, Any]]:
    if not base_token or not table_meta.get("table_id"):
        return []
    return _list_table_records(settings, base_token, str(table_meta["table_id"]))


def _write_back_lead_review_status(root_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    path = root_dir / "out" / "review-queue" / "source-lead-review-status.json"
    payload = _load_json(path)
    items = payload.get("items", [])
    updated_count = 0
    if not isinstance(items, list):
        items = []
    index = {
        _coerce_cell_value(item.get("lead_key", "")): item
        for item in items
        if isinstance(item, dict) and _coerce_cell_value(item.get("lead_key", ""))
    }
    allowed_status = {"pending", "approved", "rejected", "deferred"}
    for record in records:
        fields = _extract_record_fields(record)
        lead_key = _coerce_cell_value(fields.get("lead_key", ""))
        if not lead_key or lead_key not in index:
            continue
        raw_status = _coerce_cell_value(fields.get("status", "")).strip()
        next_status = LEAD_REVIEW_STATUS_REPO.get(raw_status, raw_status.lower())
        if next_status not in allowed_status:
            continue
        next_note = _coerce_cell_value(fields.get("note", ""))
        item = index[lead_key]
        changed = False
        if _coerce_cell_value(item.get("status", "")) != next_status:
            item["status"] = next_status
            changed = True
        if _coerce_cell_value(item.get("note", "")) != next_note:
            item["note"] = next_note
            changed = True
        if changed:
            item["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            updated_count += 1
    payload["items"] = items
    if updated_count:
        payload["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        _save_json(path, payload)
    return {"updated_count": updated_count, "path": str(path.relative_to(root_dir))}


def _parse_bool_cell(value: object) -> bool | None:
    text = _coerce_cell_value(value).strip().lower()
    if not text:
        return None
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _write_back_delivery_audit_review(root_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _load_delivery_audit_review(root_dir)
    path = _delivery_audit_review_file(root_dir)
    path_exists = path.exists()
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
    index = {
        _coerce_cell_value(item.get("generated_at", "")): item
        for item in items
        if isinstance(item, dict) and _coerce_cell_value(item.get("generated_at", ""))
    }
    updated_count = 0
    for record in records:
        fields = _extract_record_fields(record)
        generated_at = _coerce_cell_value(fields.get("generated_at", ""))
        if not generated_at:
            continue
        entry = index.setdefault(generated_at, {"generated_at": generated_at})
        if entry not in items:
            items.append(entry)
        changed = False
        for key in ("card_verified", "fallback_observed"):
            parsed = _parse_bool_cell(fields.get(key, ""))
            if parsed is None:
                continue
            if entry.get(key) is not parsed:
                entry[key] = parsed
                changed = True
        note = _coerce_cell_value(fields.get("delivery_note", ""))
        if note and _coerce_cell_value(entry.get("delivery_note", "")) != note:
            entry["delivery_note"] = note
            changed = True
        if changed:
            entry["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            updated_count += 1
    payload["items"] = items
    if updated_count:
        payload["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        _save_json(path, payload)
    elif not path_exists:
        _save_json(path, payload)
    return {
        "updated_count": updated_count,
        "path": str(path.relative_to(root_dir)),
    }


def sync_feishu_ops_desk(root_dir: Path, settings) -> dict[str, Any]:
    state = _load_sidecar_state(root_dir)
    ops_state = dict(state.get("ops_desk", {})) if isinstance(state.get("ops_desk"), dict) else {}
    payload = _build_ops_desk_payload(root_dir)
    base_meta = _ensure_ops_desk_base(root_dir, settings, ops_state)
    table_state: dict[str, Any] = {}
    existing_tables = ops_state.get("tables", {}) if isinstance(ops_state.get("tables"), dict) else {}
    state["ops_desk"] = {
        "base": base_meta,
        "tables": {},
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    _save_sidecar_state(root_dir, state)
    for table_key, table_payload in payload.items():
        table_meta = _ensure_ops_desk_table(settings, base_meta["app_token"], existing_tables, table_key, table_payload)
        table_meta["record_ids"] = _sync_ops_desk_records(settings, base_meta["app_token"], table_meta, table_payload)
        table_meta["views"] = _ensure_ops_desk_views(settings, base_meta["app_token"], table_meta, table_payload)
        table_state[table_key] = table_meta
        state["ops_desk"] = {
            "base": base_meta,
            "tables": table_state,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        _save_sidecar_state(root_dir, state)
    dashboard_meta = _ensure_ops_desk_dashboard(settings, base_meta["app_token"], ops_state, table_state)
    _cleanup_legacy_ops_desk_resources(settings, base_meta["app_token"], table_state, dashboard_meta)
    result = {
        "base": base_meta,
        "tables": table_state,
        "dashboard": dashboard_meta,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    state["ops_desk"] = result
    _save_sidecar_state(root_dir, state)
    _save_ops_desk_snapshot(root_dir, payload, result)
    return result


def pull_feishu_ops_status(root_dir: Path, settings) -> dict[str, Any]:
    state = _load_sidecar_state(root_dir)
    ops_state = state.get("ops_desk", {}) if isinstance(state.get("ops_desk"), dict) else {}
    base_meta = ops_state.get("base", {}) if isinstance(ops_state.get("base"), dict) else {}
    tables = ops_state.get("tables", {}) if isinstance(ops_state.get("tables"), dict) else {}
    base_token = _coerce_cell_value(base_meta.get("app_token", ""))
    lead_rows = _read_ops_desk_rows(settings, base_token, tables.get("lead_review", {}))
    delivery_rows = _read_ops_desk_rows(settings, base_token, tables.get("delivery_audit", {}))
    result = {
        "lead_review": _write_back_lead_review_status(root_dir, lead_rows),
        "delivery_audit": _write_back_delivery_audit_review(root_dir, delivery_rows),
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    state["ops_desk"] = {
        **ops_state,
        "last_pull": result,
    }
    _save_sidecar_state(root_dir, state)
    return result


def sync_feishu_workspace(root_dir: Path, settings, publication_mode: str = "reviewed") -> dict[str, Any]:
    state = _load_sidecar_state(root_dir)
    governance_payload = _load_governance_payload(root_dir)
    updated_state = {
        "report_doc": _sync_report_doc(root_dir, settings, state, publication_mode),
    }
    updated_state["governance_sheet"] = _sync_governance_sheet(root_dir, settings, state, governance_payload)
    updated_state["governance_tasks"] = _sync_governance_tasks(root_dir, settings, state, governance_payload)
    updated_state["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    _save_sidecar_state(root_dir, updated_state)
    return updated_state
