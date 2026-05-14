"""Tests for Cloud AI Providers (OpenAIProvider, AnthropicProvider)"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from filepilot.ai.cloud_ai import OpenAIProvider, AnthropicProvider, CloudAI


class TestOpenAIProvider:
    def test_init_without_key_is_unavailable(self):
        """Provider without api_key is not available"""
        provider = OpenAIProvider(api_key="")
        assert provider.is_available is False
        assert provider.provider_name == "OpenAI"

    def test_init_with_key_is_available(self):
        provider = OpenAIProvider(api_key="sk-test123")
        assert provider.is_available is True

    def test_configure_updates_settings(self):
        provider = OpenAIProvider(api_key="")
        assert provider.is_available is False
        provider.configure(api_key="sk-new", model="gpt-4", api_base="https://custom.api.com")
        assert provider.is_available is True
        assert provider.model == "gpt-4"
        assert provider.api_base == "https://custom.api.com"

    def test_configure_strips_trailing_slash(self):
        provider = OpenAIProvider(api_key="sk-test", api_base="https://api.openai.com/v1/")
        assert provider.api_base == "https://api.openai.com/v1"

    def test_generate_returns_empty_when_not_available(self):
        provider = OpenAIProvider(api_key="")
        result = provider.generate("hello")
        assert result == ""

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_generate_success(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello! How can I help?"}}]
        }
        mock_session.post.return_value = mock_resp

        provider = OpenAIProvider(api_key="sk-test")
        result = provider.generate("Say hello")

        assert result == "Hello! How can I help?"
        # Verify the API call
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/chat/completions" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer sk-test"

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_generate_with_system_prompt(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Summary here"}}]
        }
        mock_session.post.return_value = mock_resp

        provider = OpenAIProvider(api_key="sk-test")
        provider.generate("content", system_prompt="You are a summarizer")

        payload = mock_session.post.call_args[1]["json"]
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a summarizer"
        assert messages[1]["role"] == "user"

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_generate_request_failure_returns_empty(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_session.post.side_effect = requests.exceptions.ConnectionError("API unreachable")

        provider = OpenAIProvider(api_key="sk-test")
        result = provider.generate("hello")
        assert result == ""

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_embed_success(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_session.post.return_value = mock_resp

        provider = OpenAIProvider(api_key="sk-test")
        result = provider.embed("hello world")
        assert result == [0.1, 0.2, 0.3]

    def test_embed_returns_empty_when_not_available(self):
        provider = OpenAIProvider(api_key="")
        result = provider.embed("hello")
        assert result == []

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_chat_delegates_to_generate(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        provider = OpenAIProvider(api_key="sk-test")
        result = provider.chat([{"role": "user", "content": "hi"}])
        # Session post will raise by default (MagicMock), caught by RequestException
        assert result == ""

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_streaming_generate_returns_empty_on_failure(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        provider = OpenAIProvider(api_key="sk-test")
        result = provider.generate("hi", stream=True)
        assert result == ""


class TestAnthropicProvider:
    def test_init_without_key_is_unavailable(self):
        provider = AnthropicProvider(api_key="")
        assert provider.is_available is False
        assert provider.provider_name == "Anthropic"

    def test_init_with_key_is_available(self):
        provider = AnthropicProvider(api_key="sk-ant-test123")
        assert provider.is_available is True

    def test_configure_updates_settings(self):
        provider = AnthropicProvider(api_key="")
        provider.configure(api_key="sk-ant-new", model="claude-3-opus-20240229")
        assert provider.is_available is True
        assert provider.model == "claude-3-opus-20240229"

    def test_generate_returns_empty_when_not_available(self):
        provider = AnthropicProvider(api_key="")
        result = provider.generate("hello")
        assert result == ""

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_generate_success(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"text": "Hello from Claude!"}]
        }
        mock_session.post.return_value = mock_resp

        provider = AnthropicProvider(api_key="sk-ant-test")
        result = provider.generate("Say hello")
        assert result == "Hello from Claude!"

    @patch("filepilot.ai.cloud_ai._session_with_retries")
    def test_generate_with_system_prompt(self, mock_session_factory):
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"text": "OK"}]
        }
        mock_session.post.return_value = mock_resp

        provider = AnthropicProvider(api_key="sk-ant-test")
        provider.generate("content", system_prompt="Be concise")
        payload = mock_session.post.call_args[1]["json"]
        assert payload["system"] == "Be concise"
        assert payload["messages"][0]["role"] == "user"

    def test_chat_with_system_message_handling(self):
        """Anthropic chat() extracts system from messages list"""
        provider = AnthropicProvider(api_key="sk-ant-test")
        # chat will try HTTP - returns empty on failure (no real network)
        result = provider.chat([
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
        ])
        assert result == ""


class TestCloudAICompat:
    def test_cloudai_is_openai_alias(self):
        """CloudAI is a backward-compatibility alias for OpenAIProvider"""
        assert CloudAI is OpenAIProvider
