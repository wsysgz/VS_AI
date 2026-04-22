from auto_report.integrations.delivery_status import (
    build_channel_result,
    classify_channel_error,
    channel_response_succeeded,
    describe_channel_response,
    summarize_delivery_results,
)


def test_summarize_delivery_results_keeps_success_and_error_channels():
    results = {
        "pushplus": build_channel_result("pushplus", configured=True, attempted=True, ok=True, detail="code=200"),
        "telegram": build_channel_result("telegram", configured=True, attempted=True, ok=False, detail="timeout"),
        "feishu": build_channel_result("feishu", configured=False, attempted=False, ok=False, detail="missing config"),
    }

    summary = summarize_delivery_results(results)

    assert summary["successful_channels"] == ["pushplus"]
    assert summary["failed_channels"] == ["telegram"]
    assert summary["skipped_channels"] == ["feishu"]


def test_channel_response_helpers_detect_success_and_descriptions():
    assert channel_response_succeeded("pushplus", {"code": 200, "msg": "ok"}) is True
    assert channel_response_succeeded(
        "pushplus",
        {
            "code": 200,
            "msg": "ok",
            "verification": {"available": False, "reason": "openapi_unavailable"},
        },
    ) is True
    assert channel_response_succeeded(
        "pushplus",
        {
            "code": 200,
            "msg": "ok",
            "verification": {"available": True, "delivery": {"status": 2}},
        },
    ) is True
    assert channel_response_succeeded(
        "telegram", [{"ok": True}, {"ok": True}]
    ) is True
    assert channel_response_succeeded(
        "feishu", [{"code": 0, "msg": "success"}]
    ) is True

    assert describe_channel_response("pushplus", {"code": 200, "msg": "ok"}) == "code=200 ok"
    assert describe_channel_response("telegram", [{"ok": True}]) == "1 message(s)"
    assert describe_channel_response(
        "feishu", [{"code": 0, "msg": "success"}]
    ) == "success"


def test_describe_channel_response_includes_clawbot_verification_note():
    detail = describe_channel_response(
        "pushplus",
        {
            "code": 200,
            "msg": "执行成功",
            "verification": {
                "available": False,
                "reason": "missing_secret_key",
                "note": "ClawBot accepted by API only; final delivery requires active chat context and cannot be verified without PUSHPLUS_SECRETKEY.",
            },
        },
    )

    assert "ClawBot accepted by API only" in detail


def test_build_channel_result_preserves_error_type_and_attempted_at():
    result = build_channel_result(
        "telegram",
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
    assert classify_channel_error("telegram", [{"description": "Unauthorized"}], "Unauthorized") == "auth"
    assert classify_channel_error("pushplus", {"msg": "forbidden"}, "forbidden") == "permission"
    assert classify_channel_error("telegram", [{"description": "Bad Request: message is too long"}], "message is too long") == "format"
    assert classify_channel_error("feishu", {"error": "Read timed out"}, "Read timed out") == "network"
    assert classify_channel_error("pushplus", {"msg": "weird"}, "weird") == "unknown"
