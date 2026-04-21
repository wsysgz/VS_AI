import json
import shutil
from pathlib import Path

from auto_report.models.records import CollectedItem
from auto_report.pipeline.watch_runner import run_watch_checks


def _item(source_id: str, title: str, url: str) -> CollectedItem:
    return CollectedItem(
        source_id=source_id,
        item_id=f"{source_id}:{title}",
        title=title,
        url=url,
        summary="",
        published_at="2026-04-21T00:00:00+00:00",
        collected_at="2026-04-21T00:00:00+00:00",
        tags=[],
        language="en",
        metadata={},
    )


def test_run_watch_checks_initializes_baseline_without_reporting_changes(tmp_path: Path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    governance_dir = tmp_path / "out" / "source-governance"
    governance_dir.mkdir(parents=True)
    (governance_dir / "changedetection-watch-registry.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T18:00:00+08:00",
                "count": 1,
                "summary": {"status_counts": {"active_local": 1}},
                "items": [
                    {
                        "source_id": "cerebras-blog",
                        "watch_target": "https://www.cerebras.ai/blog",
                        "priority_score": 90,
                        "priority_label": "high",
                        "status": "active_local",
                        "note": "",
                        "next_action": "Run local watch checks.",
                        "updated_at": "2026-04-21T18:00:00+08:00",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "auto_report.pipeline.watch_runner._collect_watch_items",
        lambda source: [
            _item("cerebras-blog", "Post A", "https://www.cerebras.ai/blog/post-a"),
            _item("cerebras-blog", "Post B", "https://www.cerebras.ai/blog/post-b"),
        ],
    )

    output_path = run_watch_checks(tmp_path)
    results = json.loads(output_path.read_text(encoding="utf-8"))
    state = json.loads((governance_dir / "watch-run-state.json").read_text(encoding="utf-8"))

    assert results["summary"]["initialized_count"] == 1
    assert results["summary"]["changed_count"] == 0
    assert results["items"][0]["status"] == "initialized"
    assert state["count"] == 1
    assert state["items"][0]["seen_keys"]


def test_run_watch_checks_detects_new_items_after_baseline(tmp_path: Path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    governance_dir = tmp_path / "out" / "source-governance"
    governance_dir.mkdir(parents=True)
    (governance_dir / "changedetection-watch-registry.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T18:00:00+08:00",
                "count": 1,
                "summary": {"status_counts": {"active_local": 1}},
                "items": [
                    {
                        "source_id": "cerebras-blog",
                        "watch_target": "https://www.cerebras.ai/blog",
                        "priority_score": 90,
                        "priority_label": "high",
                        "status": "active_local",
                        "note": "",
                        "next_action": "Run local watch checks.",
                        "updated_at": "2026-04-21T18:00:00+08:00",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (governance_dir / "watch-run-state.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T18:00:00+08:00",
                "count": 1,
                "items": [
                    {
                        "source_id": "cerebras-blog",
                        "seen_keys": ["Post A|https://www.cerebras.ai/blog/post-a"],
                        "last_checked_at": "2026-04-21T18:00:00+08:00",
                        "last_change_at": "",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "auto_report.pipeline.watch_runner._collect_watch_items",
        lambda source: [
            _item("cerebras-blog", "Post A", "https://www.cerebras.ai/blog/post-a"),
            _item("cerebras-blog", "Post B", "https://www.cerebras.ai/blog/post-b"),
        ],
    )

    output_path = run_watch_checks(tmp_path)
    results = json.loads(output_path.read_text(encoding="utf-8"))

    assert results["summary"]["changed_count"] == 1
    assert results["items"][0]["status"] == "changed"
    assert results["items"][0]["new_item_count"] == 1
    assert results["items"][0]["new_items"][0]["title"] == "Post B"


def test_run_watch_checks_marks_registry_item_blocked_on_fetch_error(tmp_path: Path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    governance_dir = tmp_path / "out" / "source-governance"
    governance_dir.mkdir(parents=True)
    registry_path = governance_dir / "changedetection-watch-registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T18:00:00+08:00",
                "count": 1,
                "summary": {"status_counts": {"active_local": 1}},
                "items": [
                    {
                        "source_id": "renesas-blog",
                        "watch_target": "https://www.renesas.com/en/blogs",
                        "priority_score": 90,
                        "priority_label": "high",
                        "status": "active_local",
                        "note": "",
                        "next_action": "Run local watch checks.",
                        "updated_at": "2026-04-21T18:00:00+08:00",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "auto_report.pipeline.watch_runner._collect_watch_items",
        lambda source: (_ for _ in ()).throw(RuntimeError("403 forbidden")),
    )

    run_watch_checks(tmp_path)
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))

    assert registry_payload["summary"]["status_counts"]["blocked"] == 1
    assert registry_payload["items"][0]["status"] == "blocked"
    assert registry_payload["items"][0]["note"] == "403 forbidden"
