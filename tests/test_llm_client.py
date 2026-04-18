"""通用 LLM 客户端测试 — 多模型支持架构"""

import os
from unittest.mock import MagicMock, patch

import pytest

from auto_report.integrations.llm_client import (
    _PROVIDER_DEFAULTS,
    _resolve_provider_config,
    build_llm_payload,
    call_llm,
    get_llm_metrics,
    is_llm_enabled,
    reset_llm_metrics,
)


class TestProviderConfigResolution:
    def test_deepseek_default(self):
        """默认 provider 是 deepseek"""
        with patch.dict(os.environ, {}, clear=True):
            config = _resolve_provider_config()
            assert config["provider"] == "deepseek"
            assert "deepseek.com" in config["base_url"]
            assert config["model"] == "deepseek-chat"

    def test_openai_provider(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "openai", "AI_BASE_URL": "", "AI_MODEL": ""}, clear=False):
            config = _resolve_provider_config()
            assert config["provider"] == "openai"
            assert "openai.com" in config["base_url"]

    def test_env_override_base_url(self):
        with patch.dict(os.environ, {"AI_BASE_URL": "https://custom.api/v1"}, clear=False):
            config = _resolve_provider_config()
            assert config["base_url"] == "https://custom.api/v1"

    def test_env_override_model(self):
        with patch.dict(os.environ, {"AI_MODEL": "gpt-4o"}, clear=False):
            payload = build_llm_payload("test")
            assert payload["model"] == "gpt-4o"

    def test_temperature_default(self):
        with patch.dict(os.environ, {}, clear=True):
            payload = build_llm_payload("test")
            assert payload["temperature"] == 0.2

    def test_temperature_custom(self):
        with patch.dict(os.environ, {"AI_TEMPERATURE": "0.7"}, clear=False):
            payload = build_llm_payload("test")
            assert payload["temperature"] == 0.7

    def test_unknown_provider_falls_back_to_manual(self):
        """未知 provider 需要手动配置所有参数"""
        # 不设 AI_PROVIDER，只设 AI_BASE_URL 和 AI_MODEL
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "my-custom",
                "AI_BASE_URL": "https://my-api.example.com",
                "AI_MODEL": "my-model-v1",
                "DEEPSEEK_API_KEY": "dummy-key",  # fallback key
            },
            clear=False,
        ):
            config = _resolve_provider_config()
            assert config["provider"] == "my-custom"
            assert config["base_url"] == "https://my-api.example.com"

    def test_unknown_provider_uses_generic_ai_api_key(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "my-custom",
                "AI_BASE_URL": "https://my-api.example.com",
                "AI_MODEL": "my-model-v1",
                "AI_API_KEY": "generic-key",
                "DEEPSEEK_API_KEY": "",
                "OPENAI_API_KEY": "",
            },
            clear=False,
        ):
            config = _resolve_provider_config()
            assert config["api_key"] == "generic-key"
            assert config["api_key_env"] == "AI_API_KEY"

    def test_stage_specific_provider_override(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-chat",
                "SUMMARY_AI_PROVIDER": "minimax_svips",
                "SUMMARY_AI_BASE_URL": "https://api.svips.org/v1",
                "SUMMARY_AI_MODEL": "MiniMax-M2.7",
                "AI_API_KEY": "generic-key",
                "DEEPSEEK_API_KEY": "deepseek-key",
            },
            clear=False,
        ):
            config = _resolve_provider_config(stage="summary")
            assert config["provider"] == "minimax_svips"
            assert config["base_url"] == "https://api.svips.org/v1"
            assert config["model"] == "MiniMax-M2.7"
            assert config["api_key"] == "generic-key"

    def test_is_llm_enabled_when_only_stage_specific_generic_key_exists(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "",
                "AI_BASE_URL": "",
                "AI_MODEL": "",
                "AI_API_KEY": "",
                "DEEPSEEK_API_KEY": "",
                "OPENAI_API_KEY": "",
                "SUMMARY_AI_PROVIDER": "minimax_svips",
                "SUMMARY_AI_BASE_URL": "https://api.svips.org/v1",
                "SUMMARY_AI_MODEL": "MiniMax-M2.7",
                "SUMMARY_AI_API_KEY": "summary-key",
            },
            clear=False,
        ):
            assert is_llm_enabled() is True

    def test_is_llm_enabled_when_only_stage_specific_provider_key_exists(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "",
                "AI_BASE_URL": "",
                "AI_MODEL": "",
                "AI_API_KEY": "",
                "DEEPSEEK_API_KEY": "",
                "OPENAI_API_KEY": "",
                "ANALYSIS_AI_PROVIDER": "deepseek",
                "ANALYSIS_AI_BASE_URL": "https://api.deepseek.com",
                "ANALYSIS_AI_MODEL": "deepseek-chat",
                "ANALYSIS_DEEPSEEK_API_KEY": "analysis-key",
            },
            clear=False,
        ):
            assert is_llm_enabled() is True


class TestBuildPayload:
    def test_basic_structure(self):
        payload = build_llm_payload("Analyze this topic")
        assert "model" in payload
        assert "messages" in payload
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "Analyze this topic"

    def test_stage_specific_model_is_used(self):
        with patch.dict(
            os.environ,
            {
                "AI_MODEL": "deepseek-chat",
                "SUMMARY_AI_MODEL": "MiniMax-M2.7",
            },
            clear=False,
        ):
            payload = build_llm_payload("test", stage="summary")
            assert payload["model"] == "MiniMax-M2.7"


class TestCallLlm:
    @patch("auto_report.integrations.llm_client._session")
    def test_successful_call(self, mock_session):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "AI is evolving fast"}}]
            }
            mock_resp.raise_for_status = MagicMock()
            mock_session.post.return_value = mock_resp

            result = call_llm("What's happening in AI?")
            assert result == "AI is evolving fast"

    @patch("auto_report.integrations.llm_client._session")
    def test_api_key_missing_raises(self, mock_session):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "", "OPENAI_API_KEY": ""}, clear=False):
            with pytest.raises(RuntimeError, match="API key not configured"):
                call_llm("test")

    @patch("auto_report.integrations.llm_client._session")
    def test_retry_on_timeout_then_success(self, mock_session):
        """第一次超时，第二次成功"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            import requests.exceptions
            success_resp = MagicMock()
            success_resp.json.return_value = {
                "choices": [{"message": {"content": "finally works"}}]
            }
            success_resp.raise_for_status = MagicMock()

            mock_session.post.side_effect = [
                requests.exceptions.Timeout("timeout"),  # 第一次：超时异常
                success_resp,                            # 第二次：成功
            ]

            result = call_llm("retry me")
            assert result == "finally works"
            assert mock_session.post.call_count == 2

    @patch("auto_report.integrations.llm_client._session")
    def test_custom_provider_uses_generic_ai_api_key(self, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "my-custom",
                "AI_BASE_URL": "https://my-api.example.com",
                "AI_MODEL": "my-model-v1",
                "AI_API_KEY": "generic-key",
                "DEEPSEEK_API_KEY": "",
                "OPENAI_API_KEY": "",
            },
            clear=False,
        ):
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "custom provider works"}}]
            }
            mock_resp.raise_for_status = MagicMock()
            mock_session.post.return_value = mock_resp

            result = call_llm("test")

            assert result == "custom provider works"
            headers = mock_session.post.call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer generic-key"

    @patch("auto_report.integrations.llm_client._session")
    def test_stage_specific_call_uses_stage_provider_and_tracks_metrics(self, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-chat",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "SUMMARY_AI_PROVIDER": "minimax_svips",
                "SUMMARY_AI_BASE_URL": "https://api.svips.org/v1",
                "SUMMARY_AI_MODEL": "MiniMax-M2.7",
                "AI_API_KEY": "generic-key",
            },
            clear=False,
        ):
            reset_llm_metrics()
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "summary works"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_session.post.return_value = mock_resp

            result = call_llm("summarize this", stage="summary")

            assert result == "summary works"
            assert mock_session.post.call_args.args[0] == "https://api.svips.org/v1/chat/completions"
            headers = mock_session.post.call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer generic-key"
            payload = mock_session.post.call_args.kwargs["json"]
            assert payload["model"] == "MiniMax-M2.7"
            metrics = get_llm_metrics()
            assert metrics["provider"] == "minimax_svips"
            assert metrics["model"] == "MiniMax-M2.7"
            assert metrics["stage_breakdown"]["summary"]["provider"] == "minimax_svips"
            assert metrics["stage_breakdown"]["summary"]["token_usage"]["total"] == 15


class TestBackwardCompatibility:
    def test_summarize_alias_exists(self):
        """向后兼容别名存在且指向同一个函数"""
        from auto_report.integrations.llm_client import summarize_with_deepseek
        assert summarize_with_deepseek is call_llm
