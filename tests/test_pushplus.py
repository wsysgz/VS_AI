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


def test_build_pushplus_payload_with_secret_key_signs_token():
    """secret_key 存在时 token 应被签名为 token.signature.timestamp 格式"""
    payload = build_pushplus_payload("mytoken", "AI Daily", "# Summary", secret_key="mysecret")
    signed_token = payload["token"]
    # 签名格式: token.md5(token+secret+timestamp).timestamp
    parts = signed_token.split(".")
    assert len(parts) == 3
    assert parts[0] == "mytoken"
    # timestamp 应该是合理的整数
    ts = int(parts[2])
    assert ts > 1_700_000_000  # 2024年以后的时间戳


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
