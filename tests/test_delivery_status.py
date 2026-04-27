from auto_report.integrations.delivery_status import (
    build_channel_result,
    classify_channel_error,
    channel_response_succeeded,
    describe_channel_response,
    summarize_delivery_results,
)


def test_summarize_delivery_results_keeps_success_and_error_channels():
    results = {
        "feishu": build_channel_result("feishu", configured=True, attempted=True, ok=True, detail="success"),
        "feishu_backup": build_channel_result("feishu_backup", configured=True, attempted=True, ok=False, detail="timeout"),
        "feishu_dry_run": build_channel_result("feishu_dry_run", configured=True, attempted=False, ok=False, detail="configured"),
    }

    summary = summarize_delivery_results(results)

    assert summary["successful_channels"] == ["feishu"]
    assert summary["failed_channels"] == ["feishu_backup"]
    assert summary["skipped_channels"] == ["feishu_dry_run"]


def test_channel_response_helpers_detect_success_and_descriptions():
    assert channel_response_succeeded(
        "feishu", [{"code": 0, "msg": "success"}]
    ) is True
    assert channel_response_succeeded(
        "feishu", [{"code": 0, "msg": "success"}, {"code": 999, "msg": "fallback failed"}]
    ) is False

    assert describe_channel_response(
        "feishu", [{"code": 0, "msg": "success"}]
    ) == "success"


def test_build_channel_result_preserves_error_type_and_attempted_at():
    result = build_channel_result(
        "feishu",
        configured=True,
        attempted=True,
        ok=False,
        detail="Read timed out",
        error_type="network",
        attempted_at="2026-04-11T07:01:00+08:00",
    )

    assert result["status"] == "error"
    assert result["error_type"] == "network"
    assert result["attempted_at"] == "2026-04-11T07:01:00+08:00"


def test_build_channel_result_preserves_delivery_kind():
    result = build_channel_result(
        "feishu",
        configured=True,
        attempted=True,
        ok=True,
        detail="success",
        delivery_kind="card_success",
    )

    assert result["delivery_kind"] == "card_success"


def test_classify_channel_error_uses_delivery_categories():
    assert classify_channel_error("feishu", [{"description": "Unauthorized"}], "Unauthorized") == "auth"
    assert classify_channel_error("feishu", {"msg": "forbidden"}, "forbidden") == "permission"
    assert classify_channel_error("feishu", [{"description": "Bad Request: message is too long"}], "message is too long") == "format"
    assert classify_channel_error("feishu", {"error": "Read timed out"}, "Read timed out") == "network"
    assert classify_channel_error("feishu", {"msg": "weird"}, "weird") == "unknown"
