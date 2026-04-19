from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from auto_report.outputs.source_governance import build_source_governance_artifact


SIDE_CAR_STATE_PATH = Path("data") / "state" / "feishu-sidecar.json"


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
