from auto_report.integrations.delivery_status import build_channel_result, summarize_delivery_results


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
