import pytest
from auto_report.integrations.feishu import (
    FEISHU_MAX_TEXT_LENGTH,
    build_feishu_card_payload,
    build_feishu_payload,
    send_feishu_notification_with_fallback,
    send_feishu_message,
    split_feishu_text,
)
import json
import requests


def test_build_feishu_payload_has_correct_structure():
    payload = build_feishu_payload("oc_xxx", "Hello world")
    assert payload["receive_id"] == "oc_xxx"
    assert payload["msg_type"] == "text"
    # content must be a JSON string, not a dict
    content = json.loads(payload["content"])
    assert content["text"] == "Hello world"


def test_build_feishu_card_payload_has_correct_structure():
    payload = build_feishu_card_payload("oc_xxx", {"elements": [], "header": {"title": {"content": "Hi"}}})
    assert payload["receive_id"] == "oc_xxx"
    assert payload["msg_type"] == "interactive"
    content = json.loads(payload["content"])
    assert content["header"]["title"]["content"] == "Hi"


def test_split_feishu_text_short_text_returns_single_chunk():
    text = "Short message"
    chunks = split_feishu_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_feishu_text_long_text_splits_at_paragraph():
    # Build a long message with paragraph breaks
    para = "A" * 2000
    text = f"{para}\n\n{para}\n\n{para}"
    chunks = split_feishu_text(text)
    assert len(chunks) > 1
    # Each chunk should be within limits
    for chunk in chunks:
        assert len(chunk) <= FEISHU_MAX_TEXT_LENGTH


def test_split_feishu_text_preserves_all_content():
    original = "X" * (FEISHU_MAX_TEXT_LENGTH * 2 + 100)
    chunks = split_feishu_text(original)
    reconstructed = "".join(chunks)
    assert len(reconstructed) == len(original)


def test_split_feishu_text_empty_string():
    chunks = split_feishu_text("")
    assert chunks == [""]


def test_send_feishu_message_rejects_non_zero_send_code(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    payloads = iter([
        {"code": 0, "tenant_access_token": "token"},
        {"code": 99991663, "msg": "chat not found"},
    ])

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse(next(payloads)))

    with pytest.raises(RuntimeError, match="chat not found"):
        send_feishu_message("app", "secret", "oc_xxx", "text")


def test_send_feishu_notification_with_fallback_uses_text_when_card_send_fails(monkeypatch):
    monkeypatch.setattr(
        "auto_report.integrations.feishu.send_feishu_card_message",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("card failed")),
    )
    monkeypatch.setattr(
        "auto_report.integrations.feishu.send_feishu_messages",
        lambda *args, **kwargs: [{"code": 0, "msg": "ok"}],
    )

    result = send_feishu_notification_with_fallback(
        "app",
        "secret",
        "oc_xxx",
        "fallback text",
        card={"header": {"title": {"content": "card"}}},
    )

    assert result == [{"code": 0, "msg": "ok"}]
