import pytest
import requests

from auto_report.integrations.pushplus import build_pushplus_payload, send_pushplus


def test_build_pushplus_payload_defaults_to_markdown():
    payload = build_pushplus_payload("token", "AI Daily", "# Summary")
    assert payload["token"] == "token"
    assert payload["template"] == "markdown"


def test_build_pushplus_payload_supports_explicit_channel():
    payload = build_pushplus_payload("token", "AI Daily", "# Summary", channel="clawbot")
    assert payload["template"] == "txt"
    assert payload["channel"] == "clawbot"


def test_build_pushplus_payload_with_secret_key_keeps_plain_token():
    """secret_key 仅用于开放接口校验，不应改写发送接口上的 token"""
    payload = build_pushplus_payload("mytoken", "AI Daily", "# Summary", secret_key="mysecret")
    assert payload["token"] == "mytoken"


def test_build_pushplus_payload_without_secret_key_unchanged():
    """无 secret_key 时保持原 token 不变"""
    payload = build_pushplus_payload("plaintext-token", "Title", "Content")
    assert payload["token"] == "plaintext-token"


def test_send_pushplus_rejects_non_success_code(monkeypatch):
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"code": 500, "msg": "invalid token"}

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(RuntimeError, match="PushPlus send failed"):
        send_pushplus("token", "AI Daily", "Summary")


def test_send_pushplus_marks_clawbot_delivery_as_unverified_without_secret_key(monkeypatch):
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"code": 200, "msg": "执行成功", "data": "short-code"}

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse())

    response = send_pushplus("token", "AI Daily", "Summary", channel="clawbot", template="txt")

    assert response["verification"] == {
        "available": False,
        "reason": "missing_secret_key",
        "note": "ClawBot accepted by API only; final delivery requires active chat context and cannot be verified without PUSHPLUS_SECRETKEY.",
    }


def test_send_pushplus_rejects_inactive_clawbot_when_openapi_verification_is_available(monkeypatch):
    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    post_payloads = iter(
        [
            {"code": 200, "msg": "执行成功", "data": "short-code"},
            {"code": 200, "msg": "请求成功", "data": {"accessKey": "access-key", "expiresIn": 7200}},
        ]
    )

    def fake_post(*args, **kwargs):
        return FakeResponse(next(post_payloads))

    def fake_get(url, *args, **kwargs):
        if url.endswith("/api/open/clawBot/botInfo"):
            return FakeResponse({"code": 200, "msg": "请求成功", "data": {"haveContextToken": 0}})
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="ClawBot is not activated"):
        send_pushplus(
            "token",
            "AI Daily",
            "Summary",
            channel="clawbot",
            template="txt",
            secret_key="secret-key",
        )
