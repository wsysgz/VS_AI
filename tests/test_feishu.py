from auto_report.integrations.feishu import (
    FEISHU_MAX_TEXT_LENGTH,
    build_feishu_payload,
    split_feishu_text,
)
import json


def test_build_feishu_payload_has_correct_structure():
    payload = build_feishu_payload("oc_xxx", "Hello world")
    assert payload["receive_id"] == "oc_xxx"
    assert payload["msg_type"] == "text"
    # content must be a JSON string, not a dict
    content = json.loads(payload["content"])
    assert content["text"] == "Hello world"


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
