"""Phase 4 可观测性测试：StageTimer / _to_relative_paths / build_run_status 增强"""

import time
from pathlib import Path

from auto_report.app import StageTimer
from auto_report.pipeline.run_once import (
    _to_relative_paths,
    build_run_status,
)


# ─── StageTimer ──────────────────────────────

def test_stage_timer_measures_elapsed_time():
    """StageTimer 应正确记录经过时间"""
    with StageTimer("test") as t:
        time.sleep(0.05)
    assert t.elapsed >= 0.04  # 允许 0.01 误差
    assert t.name == "test"


def test_stage_timer_default_zero():
    """未使用时 elapsed 应为 0"""
    timer = StageTimer("unused")
    assert timer.start == 0
    assert timer.elapsed == 0


def test_stage_timer_returns_self_on_enter():
    """__enter__ 应返回 self，支持 as 语法"""
    with StageTimer("ctx") as t:
        assert t is not None
        assert isinstance(t, StageTimer)


# ─── _to_relative_paths ──────────────────────

def test_to_relative_converts_absolute():
    """绝对路径应转换为相对路径"""
    root = Path("D:/project")
    files = [
        "D:/project/data/reports/latest-summary.md",
        "D:/project/data/state/run-status.json",
    ]
    result = _to_relative_paths(files, root)
    assert result == [
        "data/reports/latest-summary.md",
        "data/state/run-status.json",
    ]


def test_to_relative_keeps_non_root():
    """非根目录路径应保持不变（只做正斜杠转换）"""
    root = Path("D:/project")
    files = ["C:/other/file.txt"]
    result = _to_relative_paths(files, root)
    assert result == ["C:/other/file.txt"]


def test_to_relative_handles_backslash():
    """Windows 反斜杠路径应统一转为正斜杠"""
    root = Path(r"D:\project")
    files = [r"D:\project\data\reports\test.html"]
    result = _to_relative_paths(files, root)
    assert result == ["data/reports/test.html"]


def test_to_relative_empty_list():
    """空列表应原样返回"""
    assert _to_relative_paths([], Path("/tmp")) == []


# ─── build_run_status 增强 ───────────────────

def test_build_run_status_includes_timings():
    """timings 字段应被正确序列化，并自动计算 total_elapsed"""
    status = build_run_status(
        generated_files=["data/reports/test.md"],
        pushed=False,
        timings={"collection": 5.2, "rendering": 0.3},
    )
    assert status["timings"]["collection"] == 5.2
    assert status["timings"]["rendering"] == 0.3
    assert status["total_elapsed"] == 5.5


def test_build_run_status_without_timings():
    """不传 timings 时不应有 timings 和 total_elapsed 字段"""
    status = build_run_status(generated_files=["test.md"], pushed=False)
    assert "timings" not in status or status.get("timings") is None
    assert "total_elapsed" not in status


def test_build_run_status_with_error():
    """error 字段应被正确记录"""
    status = build_run_status(
        generated_files=["test.md"],
        pushed=False,
        error="Telegram API timeout",
    )
    assert status["error"] == "Telegram API timeout"


def test_build_run_status_preserves_existing_fields():
    """增强字段不应破坏原有字段"""
    status = build_run_status(
        generated_files=["data/test.md"],
        pushed=True,
        push_channel="clawbot",
        stage_status={"analysis": "ok"},
        source_stats={"collected_items": 42, "report_topics": 10},
        timings={"total": 120.5},
    )
    assert status["pushed"] is True
    assert status["push_channel"] == "clawbot"
    assert status["stage_status"]["analysis"] == "ok"
    assert status["source_stats"]["collected_items"] == 42
    assert status["source_stats"]["report_topics"] == 10
    assert status["total_elapsed"] == 120.5
