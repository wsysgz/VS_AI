from auto_report.integrations.pushplus import build_pushplus_payload


def test_build_pushplus_payload_defaults_to_markdown():
    payload = build_pushplus_payload("token", "AI Daily", "# Summary")
    assert payload["token"] == "token"
    assert payload["template"] == "markdown"
