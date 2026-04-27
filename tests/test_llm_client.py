"""通用 LLM 客户端测试 — 多模型支持架构"""

import os
from unittest.mock import MagicMock, patch

import pytest

from auto_report.integrations.llm_client import (
    _PROVIDER_DEFAULTS,
    _resolve_backup_provider_config,
    _resolve_provider_config,
    _resolve_stage_budget,
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
            assert config["model"] == "deepseek-v4-flash"

    def test_deepseek_stage_defaults_use_pro_for_key_stages(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _resolve_provider_config(stage="analysis")["model"] == "deepseek-v4-pro"
            assert _resolve_provider_config(stage="summary")["model"] == "deepseek-v4-pro"
            assert _resolve_provider_config(stage="forecast")["model"] == "deepseek-v4-pro"
            assert _resolve_provider_config(stage="prefilter")["model"] == "deepseek-v4-flash"

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
                "AI_MODEL": "deepseek-v4-flash",
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

    def test_helper_stage_specific_provider_override(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-v4-flash",
                "PREFILTER_AI_PROVIDER": "minimax_svips",
                "PREFILTER_AI_BASE_URL": "https://api.svips.org/v1",
                "PREFILTER_AI_MODEL": "MiniMax-M2.7",
                "AI_API_KEY": "generic-key",
                "DEEPSEEK_API_KEY": "deepseek-key",
            },
            clear=False,
        ):
            config = _resolve_provider_config(stage="prefilter")
            assert config["provider"] == "minimax_svips"
            assert config["base_url"] == "https://api.svips.org/v1"
            assert config["model"] == "MiniMax-M2.7"
            assert config["api_key"] == "generic-key"

    def test_litellm_proxy_provider_defaults(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "litellm_proxy",
                "AI_BASE_URL": "",
                "AI_MODEL": "",
                "LITELLM_MASTER_KEY": "sk-litellm",
            },
            clear=False,
        ):
            config = _resolve_provider_config()
            assert config["provider"] == "litellm_proxy"
            assert config["base_url"] == "http://127.0.0.1:4000"
            assert config["model"] == "vs-ai-default"
            assert config["api_key"] == "sk-litellm"
            assert config["api_key_env"] == "LITELLM_MASTER_KEY"

    def test_stage_specific_litellm_proxy_override(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-v4-flash",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "SUMMARY_AI_PROVIDER": "litellm_proxy",
                "SUMMARY_AI_BASE_URL": "",
                "SUMMARY_AI_MODEL": "vs-ai-summary",
                "SUMMARY_LITELLM_MASTER_KEY": "sk-summary-litellm",
            },
            clear=False,
        ):
            config = _resolve_provider_config(stage="summary")
            assert config["provider"] == "litellm_proxy"
            assert config["base_url"] == "http://127.0.0.1:4000"
            assert config["model"] == "vs-ai-summary"
            assert config["api_key"] == "sk-summary-litellm"
            assert config["api_key_env"] == "SUMMARY_LITELLM_MASTER_KEY"

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
                "ANALYSIS_AI_MODEL": "deepseek-v4-pro",
                "ANALYSIS_DEEPSEEK_API_KEY": "analysis-key",
            },
            clear=False,
        ):
            assert is_llm_enabled() is True

    def test_is_llm_enabled_when_only_helper_stage_key_exists(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "",
                "AI_BASE_URL": "",
                "AI_MODEL": "",
                "AI_API_KEY": "",
                "DEEPSEEK_API_KEY": "",
                "OPENAI_API_KEY": "",
                "PREFILTER_AI_PROVIDER": "minimax_svips",
                "PREFILTER_AI_BASE_URL": "https://api.svips.org/v1",
                "PREFILTER_AI_MODEL": "MiniMax-M2.7",
                "PREFILTER_AI_API_KEY": "prefilter-key",
            },
            clear=False,
        ):
            assert is_llm_enabled() is True

    def test_ai_disable_llm_forces_local_validation_off(self):
        with patch.dict(
            os.environ,
            {
                "AI_DISABLE_LLM": "true",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "ANALYSIS_DEEPSEEK_API_KEY": "analysis-key",
            },
            clear=False,
        ):
            assert is_llm_enabled() is False

    def test_ai_disable_llm_marks_metrics_disabled(self):
        with patch.dict(
            os.environ,
            {
                "AI_DISABLE_LLM": "true",
                "DEEPSEEK_API_KEY": "deepseek-key",
            },
            clear=False,
        ):
            reset_llm_metrics()
            metrics = get_llm_metrics()
            assert metrics["provider"] == "disabled"
            assert metrics["model"] == ""
            assert metrics["calls"] == 0

    def test_global_backup_provider_resolution(self):
        with patch.dict(
            os.environ,
            {
                "BACKUP_AI_PROVIDER": "openai",
                "BACKUP_AI_BASE_URL": "",
                "BACKUP_AI_MODEL": "",
                "BACKUP_AI_API_KEY": "backup-openai-key",
            },
            clear=False,
        ):
            config = _resolve_backup_provider_config("analysis")
            assert config is not None
            assert config["provider"] == "openai"
            assert "openai.com" in config["base_url"]
            assert config["api_key"] == "backup-openai-key"

    def test_stage_specific_backup_provider_resolution(self):
        with patch.dict(
            os.environ,
            {
                "SUMMARY_BACKUP_AI_PROVIDER": "litellm_proxy",
                "SUMMARY_BACKUP_AI_BASE_URL": "",
                "SUMMARY_BACKUP_AI_MODEL": "vs-ai-summary-backup",
                "SUMMARY_BACKUP_AI_API_KEY": "summary-backup-key",
            },
            clear=False,
        ):
            config = _resolve_backup_provider_config("summary")
            assert config is not None
            assert config["provider"] == "litellm_proxy"
            assert config["base_url"] == "http://127.0.0.1:4000"
            assert config["model"] == "vs-ai-summary-backup"
            assert config["api_key"] == "summary-backup-key"

    def test_global_stage_budget_resolution(self):
        with patch.dict(
            os.environ,
            {
                "AI_MAX_STAGE_LATENCY_SECONDS": "12.5",
                "AI_MAX_STAGE_TOTAL_TOKENS": "5000",
            },
            clear=False,
        ):
            budget = _resolve_stage_budget("analysis")
            assert budget["max_latency_seconds"] == 12.5
            assert budget["max_total_tokens"] == 5000

    def test_stage_specific_budget_resolution(self):
        with patch.dict(
            os.environ,
            {
                "AI_MAX_STAGE_LATENCY_SECONDS": "12.5",
                "AI_MAX_STAGE_TOTAL_TOKENS": "5000",
                "SUMMARY_AI_MAX_LATENCY_SECONDS": "9.0",
                "SUMMARY_AI_MAX_TOTAL_TOKENS": "2500",
            },
            clear=False,
        ):
            budget = _resolve_stage_budget("summary")
            assert budget["max_latency_seconds"] == 9.0
            assert budget["max_total_tokens"] == 2500


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
                "AI_MODEL": "deepseek-v4-flash",
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
    @patch("auto_report.integrations.llm_client.time.sleep", return_value=None)
    def test_stage_uses_backup_provider_after_primary_failure(self, _mock_sleep, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-chat",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "BACKUP_AI_PROVIDER": "openai",
                "BACKUP_AI_BASE_URL": "",
                "BACKUP_AI_MODEL": "gpt-4o-mini",
                "BACKUP_AI_API_KEY": "backup-openai-key",
            },
            clear=False,
        ):
            import requests.exceptions

            success_resp = MagicMock()
            success_resp.json.return_value = {
                "choices": [{"message": {"content": "backup works"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15},
            }
            success_resp.raise_for_status = MagicMock()
            success_resp.status_code = 200

            mock_session.post.side_effect = [
                requests.exceptions.ConnectionError("primary down"),
                requests.exceptions.ConnectionError("primary still down"),
                requests.exceptions.ConnectionError("primary exhausted"),
                success_resp,
            ]

            reset_llm_metrics()
            result = call_llm("use backup", stage="analysis")

            assert result == "backup works"
            assert mock_session.post.call_args_list[0].args[0] == "https://api.deepseek.com/chat/completions"
            assert mock_session.post.call_args_list[-1].args[0] == "https://api.openai.com/v1/chat/completions"
            metrics = get_llm_metrics()
            assert metrics["stage_breakdown"]["analysis"]["attempts"] == 2
            assert metrics["stage_breakdown"]["analysis"]["backup_used"] is True
            assert metrics["stage_breakdown"]["analysis"]["final_provider"] == "openai"

    @patch("auto_report.integrations.llm_client._session")
    def test_stage_uses_backup_provider_after_latency_guardrail(self, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-chat",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "BACKUP_AI_PROVIDER": "openai",
                "BACKUP_AI_BASE_URL": "",
                "BACKUP_AI_MODEL": "gpt-4o-mini",
                "BACKUP_AI_API_KEY": "backup-openai-key",
                "ANALYSIS_AI_MAX_LATENCY_SECONDS": "0.01",
            },
            clear=False,
        ):
            first = MagicMock()
            first.json.return_value = {
                "choices": [{"message": {"content": "primary too slow"}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
            }
            first.raise_for_status = MagicMock()
            first.status_code = 200

            second = MagicMock()
            second.json.return_value = {
                "choices": [{"message": {"content": "backup fast enough"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9},
            }
            second.raise_for_status = MagicMock()
            second.status_code = 200

            mock_session.post.side_effect = [first, second]

            with patch("auto_report.integrations.llm_client.time.perf_counter", side_effect=[0.0, 0.5, 1.0, 1.005]):
                reset_llm_metrics()
                result = call_llm("latency guardrail", stage="analysis")

            assert result == "backup fast enough"
            metrics = get_llm_metrics()
            stage = metrics["stage_breakdown"]["analysis"]
            assert stage["backup_used"] is True
            assert stage["guardrail_triggered"] is True
            assert stage["guardrail_reason"] == "latency_exceeded"

    @patch("auto_report.integrations.llm_client._session")
    def test_stage_uses_backup_provider_after_token_guardrail(self, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-chat",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "BACKUP_AI_PROVIDER": "openai",
                "BACKUP_AI_BASE_URL": "",
                "BACKUP_AI_MODEL": "gpt-4o-mini",
                "BACKUP_AI_API_KEY": "backup-openai-key",
                "ANALYSIS_AI_MAX_TOTAL_TOKENS": "10",
            },
            clear=False,
        ):
            first = MagicMock()
            first.json.return_value = {
                "choices": [{"message": {"content": "primary too expensive"}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 5, "total_tokens": 13},
            }
            first.raise_for_status = MagicMock()
            first.status_code = 200

            second = MagicMock()
            second.json.return_value = {
                "choices": [{"message": {"content": "backup acceptable"}}],
                "usage": {"prompt_tokens": 6, "completion_tokens": 3, "total_tokens": 9},
            }
            second.raise_for_status = MagicMock()
            second.status_code = 200

            mock_session.post.side_effect = [first, second]

            reset_llm_metrics()
            result = call_llm("token guardrail", stage="analysis")

            assert result == "backup acceptable"
            metrics = get_llm_metrics()
            stage = metrics["stage_breakdown"]["analysis"]
            assert stage["backup_used"] is True
            assert stage["guardrail_triggered"] is True
            assert stage["guardrail_reason"] == "token_exceeded"

    @patch("auto_report.integrations.llm_client._session")
    @patch("auto_report.integrations.llm_client.time.sleep", return_value=None)
    def test_stage_raises_after_primary_and_backup_fail(self, _mock_sleep, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "deepseek",
                "AI_BASE_URL": "https://api.deepseek.com",
                "AI_MODEL": "deepseek-chat",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "BACKUP_AI_PROVIDER": "openai",
                "BACKUP_AI_BASE_URL": "",
                "BACKUP_AI_MODEL": "gpt-4o-mini",
                "BACKUP_AI_API_KEY": "backup-openai-key",
            },
            clear=False,
        ):
            import requests.exceptions

            mock_session.post.side_effect = [
                requests.exceptions.Timeout("primary timeout 1"),
                requests.exceptions.Timeout("primary timeout 2"),
                requests.exceptions.Timeout("primary timeout 3"),
                requests.exceptions.ConnectionError("backup down 1"),
                requests.exceptions.ConnectionError("backup down 2"),
                requests.exceptions.ConnectionError("backup down 3"),
            ]

            reset_llm_metrics()
            with pytest.raises(RuntimeError):
                call_llm("both fail", stage="analysis")

            metrics = get_llm_metrics()
            stage = metrics["stage_breakdown"]["analysis"]
            assert stage["attempts"] == 2
            assert stage["backup_used"] is True

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

    @patch("auto_report.integrations.llm_client._session")
    def test_litellm_proxy_call_uses_master_key_and_alias_model(self, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "litellm_proxy",
                "AI_BASE_URL": "",
                "AI_MODEL": "vs-ai-analysis",
                "LITELLM_MASTER_KEY": "sk-litellm",
            },
            clear=False,
        ):
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "gateway works"}}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_session.post.return_value = mock_resp

            reset_llm_metrics()
            result = call_llm("route through gateway")

            assert result == "gateway works"
            assert mock_session.post.call_args.args[0] == "http://127.0.0.1:4000/chat/completions"
            assert mock_session.post.call_args.kwargs["headers"]["Authorization"] == "Bearer sk-litellm"
            assert mock_session.post.call_args.kwargs["json"]["model"] == "vs-ai-analysis"
            metrics = get_llm_metrics()
            assert metrics["provider"] == "litellm_proxy"
            assert metrics["model"] == "vs-ai-analysis"

    @patch("auto_report.integrations.llm_client._session")
    def test_same_provider_different_models_keep_provider_but_mix_model(self, mock_session):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "litellm_proxy",
                "AI_BASE_URL": "",
                "AI_MODEL": "vs-ai-analysis",
                "LITELLM_MASTER_KEY": "sk-litellm",
                "SUMMARY_AI_PROVIDER": "litellm_proxy",
                "SUMMARY_AI_BASE_URL": "",
                "SUMMARY_AI_MODEL": "vs-ai-summary",
                "SUMMARY_LITELLM_MASTER_KEY": "sk-litellm",
            },
            clear=False,
        ):
            first = MagicMock()
            first.json.return_value = {
                "choices": [{"message": {"content": "analysis works"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
            }
            first.raise_for_status = MagicMock()

            second = MagicMock()
            second.json.return_value = {
                "choices": [{"message": {"content": "summary works"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
            }
            second.raise_for_status = MagicMock()

            mock_session.post.side_effect = [first, second]

            reset_llm_metrics()
            assert call_llm("analysis pass", stage="analysis") == "analysis works"
            assert call_llm("summary pass", stage="summary") == "summary works"

            metrics = get_llm_metrics()
            assert metrics["provider"] == "litellm_proxy"
            assert metrics["model"] == "mixed"
            assert metrics["stage_breakdown"]["analysis"]["model"] == "vs-ai-analysis"
            assert metrics["stage_breakdown"]["summary"]["model"] == "vs-ai-summary"

    @patch("auto_report.integrations.llm_client.finish_generation_trace")
    @patch("auto_report.integrations.llm_client.start_generation_trace")
    @patch("auto_report.integrations.llm_client._session")
    def test_call_llm_emits_tracing_hooks(self, mock_session, mock_start_generation, mock_finish_generation):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "litellm_proxy",
                "AI_BASE_URL": "",
                "AI_MODEL": "vs-ai-analysis",
                "LITELLM_MASTER_KEY": "sk-litellm",
            },
            clear=False,
        ):
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "traced response"}}],
                "usage": {"prompt_tokens": 9, "completion_tokens": 3, "total_tokens": 12},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_resp.status_code = 200
            mock_session.post.return_value = mock_resp
            mock_start_generation.return_value = {"observation_id": "gen-1"}

            result = call_llm("trace me", stage="analysis")

            assert result == "traced response"
            mock_start_generation.assert_called_once()
            mock_finish_generation.assert_called_once()
            finish_kwargs = mock_finish_generation.call_args.kwargs
            assert finish_kwargs["usage_details"]["prompt_tokens"] == 9
            assert finish_kwargs["metadata"]["stage"] == "analysis"
            assert finish_kwargs["output_text"] == "traced response"


class TestBackwardCompatibility:
    def test_summarize_alias_exists(self):
        """向后兼容别名存在且指向同一个函数"""
        from auto_report.integrations.llm_client import summarize_with_deepseek
        assert summarize_with_deepseek is call_llm
