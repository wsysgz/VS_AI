from auto_report.integrations.delivery_status import (
    build_channel_result,
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
