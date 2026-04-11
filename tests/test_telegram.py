import pytest
import requests

from auto_report.integrations.telegram import (
    build_telegram_payload,
    send_telegram_message,
    send_telegram_messages,
    split_telegram_text,
)


def test_build_telegram_payload_uses_plain_text_message():
    payload = build_telegram_payload("8566057843", "自动情报快报\n详情链接：https://github.com/wsysgz/VS_AI")
    assert payload["chat_id"] == "8566057843"
    assert "自动情报快报" in payload["text"]
    assert payload["disable_web_page_preview"] is True


def test_split_telegram_text_splits_long_messages_without_losing_content():
    text = (
        "# 自动情报快报\n\n"
        + ("A" * 2050)
        + "\n\n"
        + ("B" * 2050)
        + "\n\n详情链接：\nhttps://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md"
    )

    chunks = split_telegram_text(text, max_length=4096)

    assert len(chunks) == 2
    assert all(len(chunk) <= 4096 for chunk in chunks)
    assert "".join(chunks) == text
    assert chunks[-1].endswith("latest-summary.md")


def test_send_telegram_messages_posts_each_chunk(monkeypatch):
    captured: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"ok": True}

    def fake_post(url: str, json: dict[str, object], timeout: int) -> FakeResponse:
        captured.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    responses = send_telegram_messages("telegram-token", "8566057843", "甲" * 4100)

    assert len(captured) == 2
    assert len(responses) == 2
    assert all(entry["url"] == "https://api.telegram.org/bottelegram-token/sendMessage" for entry in captured)
    assert all(len(str(entry["json"]["text"])) <= 4096 for entry in captured)


def test_send_telegram_message_rejects_non_ok_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": False, "description": "chat not found"}

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(RuntimeError, match="chat not found"):
        send_telegram_message("token", "chat", "text")
