from auto_report.integrations.telegram import build_telegram_payload


def test_build_telegram_payload_uses_plain_text_message():
    payload = build_telegram_payload("8566057843", "自动情报快报\n详情链接：https://github.com/wsysgz/VS_AI")
    assert payload["chat_id"] == "8566057843"
    assert "自动情报快报" in payload["text"]
    assert payload["disable_web_page_preview"] is True
