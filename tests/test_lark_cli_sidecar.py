from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from auto_report.integrations.lark_cli import (
    SIDE_CAR_STATE_PATH,
    pull_feishu_ops_status,
    sync_feishu_ops_desk,
    sync_feishu_workspace,
)
from auto_report.settings import load_settings


def _write_reviewed_report(root_dir: Path) -> None:
    reports_dir = root_dir / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "latest-summary-reviewed.md").write_text(
        "# VS_AI reviewed report\n\n- key change\n- key risk\n",
        encoding="utf-8",
    )


def _write_governance_artifact(root_dir: Path) -> None:
    artifact_path = root_dir / "out" / "source-governance" / "source-governance.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T14:00:00+08:00",
                "source_governance": {
                    "summary": {
                        "manual_review_count": 1,
                        "rsshub_candidate_count": 2,
                        "changedetection_candidate_count": 3,
                        "replacement_candidate_count": 4,
                    },
                    "priority_queue": [
                        {
                            "source_id": "anthropic-news",
                            "candidate_kind": "changedetection_watch",
                            "priority_label": "high",
                            "priority_score": 90,
                            "next_action": "Create a changedetection watch.",
                            "replacement_target": "rsshub-or-feed",
                            "url": "https://www.anthropic.com/news",
                        },
                        {
                            "source_id": "nxp-edge-ai",
                            "candidate_kind": "manual_replace",
                            "priority_label": "high",
                            "priority_score": 80,
                            "next_action": "Review this source and replace it.",
                            "replacement_target": "stable-nxp-listing",
                            "url": "https://www.nxp.com/company/about-nxp/smarter-world-blog",
                        },
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_run_status(root_dir: Path) -> None:
    state_dir = root_dir / "data" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-22T08:01:33+08:00",
                "publication_mode": "auto",
                "risk_level": "medium",
                "delivery_results": {
                    "channels": {
                        "feishu": {"status": "ok"},
                        "pushplus": {"status": "ok"},
                        "telegram": {"status": "ok"},
                    }
                },
                "push_response": {
                    "feishu": {
                        "ok": True,
                        "messages_sent": 1,
                        "message_ids": ["om_1"],
                    }
                },
                "review": {"reviewer": "", "review_note": ""},
                "tracing": {"enabled": False},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_lead_review_status(root_dir: Path) -> None:
    path = root_dir / "out" / "review-queue" / "source-lead-review-status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-22T08:00:00+08:00",
                "count": 1,
                "items": [
                    {
                        "lead_key": "lead-1",
                        "keyword": "Qualcomm on-device AI",
                        "title": "Qualcomm OnQ Blog",
                        "bucket": "official_feed_leads",
                        "priority_score": 121,
                        "priority_label": "high",
                        "status": "pending",
                        "note": "",
                        "updated_at": "",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_candidate_updates(root_dir: Path) -> None:
    path = root_dir / "out" / "review-queue" / "candidate-updates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-22T08:00:00+08:00",
                "count": 1,
                "summary": {"source_update_count": 1, "watch_update_count": 0},
                "updates": [
                    {
                        "update_key": "source_update|qualcomm-onq|official_feed",
                        "source_id": "qualcomm-onq",
                        "update_type": "source_update",
                        "summary": "Switch Qualcomm OnQ to validated feed",
                        "apply_ready": True,
                        "blocking_reason": "",
                        "validation_mode": "safe",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_delivery_audit_review(root_dir: Path) -> None:
    path = root_dir / "data" / "state" / "delivery-audit-review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-22T08:00:00+08:00",
                "items": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _settings_for(tmp_path: Path, monkeypatch) -> object:
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.setenv("LARK_CLI_PATH", "D:\\AI\\Feishu\\feushu_cli\\lark-cli.exe")
    monkeypatch.setenv("LARK_CLI_PROFILE", "vs_ai")
    return load_settings(tmp_path)


def _opsdesk_tmp_dir() -> Path:
    base_dir = Path.cwd() / "output"
    base_dir.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="codex-opsdesk-", dir=base_dir))


def test_sync_feishu_workspace_creates_resources_and_persists_state(tmp_path, monkeypatch):
    _write_reviewed_report(tmp_path)
    _write_governance_artifact(tmp_path)
    settings = _settings_for(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check, cwd=None, encoding=None, errors=None):
        calls.append(command)
        joined = " ".join(command)
        if "docs +create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"document": {"document_id": "doc_1", "url": "https://doc/1"}}), stderr="")
        if "sheets +create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"spreadsheet": {"spreadsheet_token": "sheet_1", "url": "https://sheet/1"}}), stderr="")
        if "sheets +info" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"sheets": [{"sheet_id": "sheetA"}]}), stderr="")
        if "task +tasklist-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"tasklist": {"guid": "tl_1", "url": "https://tasklist/1"}}), stderr="")
        if "task +create" in joined:
            source_id = "anthropic-news" if "anthropic-news" in joined else "nxp-edge-ai"
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"task": {"guid": f"task_{source_id}", "url": f"https://task/{source_id}"}}), stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("auto_report.integrations.lark_cli.subprocess.run", fake_run)

    result = sync_feishu_workspace(tmp_path, settings, publication_mode="reviewed")

    assert result["report_doc"]["doc_token"] == "doc_1"
    assert result["governance_sheet"]["spreadsheet_token"] == "sheet_1"
    assert result["governance_sheet"]["sheet_id"] == "sheetA"
    assert result["governance_tasks"]["tasklist_id"] == "tl_1"
    assert set(result["governance_tasks"]["tasks_by_source"]) == {"anthropic-news", "nxp-edge-ai"}
    assert any("docs +create" in " ".join(command) for command in calls)
    assert any("sheets +create" in " ".join(command) for command in calls)
    assert any("task +tasklist-create" in " ".join(command) for command in calls)

    state = json.loads((tmp_path / SIDE_CAR_STATE_PATH).read_text(encoding="utf-8"))
    assert state["report_doc"]["doc_token"] == "doc_1"
    assert state["governance_sheet"]["sheet_id"] == "sheetA"
    assert state["governance_tasks"]["tasklist_id"] == "tl_1"


def test_sync_feishu_workspace_updates_existing_resources(tmp_path, monkeypatch):
    _write_reviewed_report(tmp_path)
    _write_governance_artifact(tmp_path)
    settings = _settings_for(tmp_path, monkeypatch)
    state_path = tmp_path / SIDE_CAR_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "report_doc": {"doc_token": "doc_existing", "url": "https://doc/existing"},
                "governance_sheet": {
                    "spreadsheet_token": "sheet_existing",
                    "sheet_id": "sheetABC",
                    "url": "https://sheet/existing",
                },
                "governance_tasks": {
                    "tasklist_id": "tl_existing",
                    "url": "https://tasklist/existing",
                    "tasks_by_source": {
                        "anthropic-news": {"task_id": "task_existing", "url": "https://task/existing"}
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check, cwd=None, encoding=None, errors=None):
        calls.append(command)
        joined = " ".join(command)
        if "docs +update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"document": {"document_id": "doc_existing", "url": "https://doc/existing"}}), stderr="")
        if "sheets +write" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"updatedRange": "sheetABC!A1:G3"}), stderr="")
        if "task +update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"task": {"guid": "task_existing", "url": "https://task/existing"}}), stderr="")
        if "task +create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"task": {"guid": "task_nxp-edge-ai", "url": "https://task/nxp-edge-ai"}}), stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("auto_report.integrations.lark_cli.subprocess.run", fake_run)

    result = sync_feishu_workspace(tmp_path, settings, publication_mode="reviewed")

    assert result["report_doc"]["doc_token"] == "doc_existing"
    assert result["governance_sheet"]["sheet_id"] == "sheetABC"
    assert result["governance_tasks"]["tasks_by_source"]["anthropic-news"]["task_id"] == "task_existing"
    assert result["governance_tasks"]["tasks_by_source"]["nxp-edge-ai"]["task_id"] == "task_nxp-edge-ai"
    assert any("docs +update" in " ".join(command) for command in calls)
    assert any("sheets +write" in " ".join(command) for command in calls)
    assert any("task +update" in " ".join(command) for command in calls)


def test_sync_feishu_ops_desk_creates_base_tables_and_dashboard(monkeypatch):
    tmp_path = _opsdesk_tmp_dir()
    _write_governance_artifact(tmp_path)
    _write_lead_review_status(tmp_path)
    _write_candidate_updates(tmp_path)
    _write_run_status(tmp_path)
    _write_delivery_audit_review(tmp_path)
    settings = _settings_for(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check, cwd=None, encoding=None, errors=None):
        calls.append(command)
        joined = " ".join(command)
        if "base +base-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"base": {"app_token": "base_1", "url": "https://base/1"}}), stderr="")
        if "base +table-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"items": []}), stderr="")
        if "base +table-update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"table": {"table_id": "tbl_any"}}), stderr="")
        if "base +table-create" in joined:
            if "Governance Main" in joined:
                table_id = "tbl_governance"
            elif "审批协作" in joined:
                table_id = "tbl_leads"
            elif "交付验收" in joined:
                table_id = "tbl_delivery"
            else:
                table_id = "tbl_updates"
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"table": {"table_id": table_id, "name": table_id}}), stderr="")
        if "base +field-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"data": {"fields": []}}), stderr="")
        if "base +field-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"field": {"field_id": "fld_1"}}), stderr="")
        if "base +field-update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"field": {"field_id": "fld_1"}}), stderr="")
        if "base +record-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"items": []}), stderr="")
        if "base +record-upsert" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"record": {"record_id": f"rec_{len(calls)}"}}), stderr="")
        if "base +view-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"data": {"views": []}}), stderr="")
        if "base +view-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"view": {"view_id": f"vew_{len(calls)}"}}), stderr="")
        if "base +view-set-visible-fields" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")
        if "base +view-set-filter" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")
        if "base +dashboard-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"items": []}), stderr="")
        if "base +dashboard-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"dashboard": {"dashboard_id": "dsh_1", "url": "https://dashboard/1"}}), stderr="")
        if "base +dashboard-block-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"items": []}), stderr="")
        if "base +dashboard-block-delete" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")
        if "base +dashboard-block-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"block": {"block_id": f"blk_{len(calls)}"}}), stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("auto_report.integrations.lark_cli.subprocess.run", fake_run)

    result = sync_feishu_ops_desk(tmp_path, settings)

    assert result["base"]["app_token"] == "base_1"
    assert result["dashboard"]["dashboard_id"] == "dsh_1"
    assert set(result["tables"]) == {
        "governance_main",
        "lead_review",
        "delivery_audit",
        "candidate_updates",
    }
    state = json.loads((tmp_path / SIDE_CAR_STATE_PATH).read_text(encoding="utf-8"))
    assert state["ops_desk"]["base"]["app_token"] == "base_1"
    assert any("base +base-create" in " ".join(command) for command in calls)
    assert any("base +table-create" in " ".join(command) for command in calls)
    assert any("base +dashboard-create" in " ".join(command) for command in calls)


def test_pull_feishu_ops_status_updates_repo_json_files(monkeypatch):
    tmp_path = _opsdesk_tmp_dir()
    _write_governance_artifact(tmp_path)
    _write_lead_review_status(tmp_path)
    _write_candidate_updates(tmp_path)
    _write_run_status(tmp_path)
    _write_delivery_audit_review(tmp_path)
    settings = _settings_for(tmp_path, monkeypatch)
    state_path = tmp_path / SIDE_CAR_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "ops_desk": {
                    "base": {"app_token": "base_1", "url": "https://base/1"},
                    "tables": {
                        "lead_review": {"table_id": "tbl_leads", "name": "Lead Review"},
                        "delivery_audit": {"table_id": "tbl_delivery", "name": "Delivery Audit"},
                    },
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    def fake_run(command, capture_output, text, check, cwd=None, encoding=None, errors=None):
        joined = " ".join(command)
        if "base +record-list" in joined and "tbl_leads" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "data": {
                            "data": [
                                ["NO.001", "lead-1", "approved", "checked in Feishu"],
                            ],
                            "fields": ["ID", "lead_key", "status", "note"],
                            "record_id_list": ["rec_1"],
                        }
                    }
                ),
                stderr="",
            )
        if "base +record-list" in joined and "tbl_delivery" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "data": {
                            "data": [
                                ["NO.001", "2026-04-22T08:01:33+08:00", "true", "false", "looks good"],
                            ],
                            "fields": ["ID", "generated_at", "card_verified", "fallback_observed", "delivery_note"],
                            "record_id_list": ["rec_2"],
                        }
                    }
                ),
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("auto_report.integrations.lark_cli.subprocess.run", fake_run)

    result = pull_feishu_ops_status(tmp_path, settings)

    lead_payload = json.loads((tmp_path / "out" / "review-queue" / "source-lead-review-status.json").read_text(encoding="utf-8"))
    lead = lead_payload["items"][0]
    assert lead["status"] == "approved"
    assert lead["note"] == "checked in Feishu"

    delivery_payload = json.loads((tmp_path / "data" / "state" / "delivery-audit-review.json").read_text(encoding="utf-8"))
    delivery = delivery_payload["items"][0]
    assert delivery["card_verified"] is True
    assert delivery["fallback_observed"] is False
    assert delivery["delivery_note"] == "looks good"
    assert result["lead_review"]["updated_count"] == 1
    assert result["delivery_audit"]["updated_count"] == 1


def test_sync_feishu_ops_desk_cleans_up_legacy_english_resources(monkeypatch):
    tmp_path = _opsdesk_tmp_dir()
    _write_governance_artifact(tmp_path)
    _write_lead_review_status(tmp_path)
    _write_candidate_updates(tmp_path)
    _write_run_status(tmp_path)
    _write_delivery_audit_review(tmp_path)
    settings = _settings_for(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check, cwd=None, encoding=None, errors=None):
        calls.append(command)
        joined = " ".join(command)
        if "base +table-list" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "data": {
                            "tables": [
                                {"id": "tbl_old1", "name": "Lead Review"},
                                {"id": "tbl_old2", "name": "Delivery Audit"},
                                {"id": "tbl_old3", "name": "Candidate Updates"},
                                {"id": "tbl_old4", "name": "数据表"},
                            ]
                        }
                    }
                ),
                stderr="",
            )
        if "base +dashboard-list" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"data": {"items": [{"dashboard_id": "dsh_old", "name": "VS_AI Ops Desk"}]}}),
                stderr="",
            )
        if "base +base-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"base": {"app_token": "base_1", "url": "https://base/1"}}), stderr="")
        if "base +table-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"table": {"table_id": f"tbl_{len(calls)}"}}), stderr="")
        if "base +field-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"data": {"fields": []}}), stderr="")
        if "base +field-create" in joined or "base +field-update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"field": {"field_id": "fld_1"}}), stderr="")
        if "base +record-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"items": []}), stderr="")
        if "base +record-upsert" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"record": {"record_id": f"rec_{len(calls)}"}}), stderr="")
        if "base +view-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"data": {"views": []}}), stderr="")
        if "base +view-create" in joined or "base +view-set-visible-fields" in joined or "base +view-set-filter" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")
        if "base +dashboard-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"dashboard": {"dashboard_id": "dsh_new", "url": "https://dashboard/1"}}), stderr="")
        if "base +dashboard-block-list" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"items": []}), stderr="")
        if "base +dashboard-block-create" in joined or "base +dashboard-block-delete" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")
        if "base +table-delete" in joined or "base +dashboard-delete" in joined or "base +dashboard-update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True}), stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("auto_report.integrations.lark_cli.subprocess.run", fake_run)

    sync_feishu_ops_desk(tmp_path, settings)

    assert any(("base +table-delete" in " ".join(command) or "base +table-update" in " ".join(command)) and "tbl_old1" in " ".join(command) for command in calls)
    assert any(("base +table-delete" in " ".join(command) or "base +table-update" in " ".join(command)) and "tbl_old4" in " ".join(command) for command in calls)
    assert any(("base +dashboard-delete" in " ".join(command) or "base +dashboard-update" in " ".join(command)) and "dsh_old" in " ".join(command) for command in calls)
