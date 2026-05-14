"""Tests for Local AI Providers (OllamaProvider, LlamaCppProvider)"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from filepilot.ai.local_ai import OllamaProvider, LlamaCppProvider, LocalAI


class TestOllamaProvider:
    @patch("filepilot.ai.local_ai.requests.get")
    def test_init_defaults(self, mock_get):
        """Default initialization with connection check"""
        mock_get.side_effect = requests.exceptions.ConnectionError("No Ollama")
        provider = OllamaProvider()
        assert provider.model == "qwen2.5:7b"
        assert provider.api_base == "http://localhost:11434"
        assert provider.provider_name == "Ollama"
        # No Ollama running in CI, so should be unavailable
        assert provider.is_available is False

    @patch("filepilot.ai.local_ai.requests.get")
    def test_custom_config(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("No Ollama")
        provider = OllamaProvider(model="llama3:8b", api_base="http://192.168.1.100:11434")
        assert provider.model == "llama3:8b"
        assert provider.api_base == "http://192.168.1.100:11434"

    @patch("filepilot.ai.local_ai.requests.get")
    def test_strips_trailing_slash(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("No Ollama")
        provider = OllamaProvider(api_base="http://localhost:11434/")
        assert provider.api_base == "http://localhost:11434"

    @patch("filepilot.ai.local_ai.requests.get")
    def test_generate_returns_empty_when_not_available(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("No Ollama")
        provider = OllamaProvider()
        assert provider.is_available is False
        result = provider.generate("hello")
        assert result == ""

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_generate_success(self, mock_get, mock_post):
        # Make connection check pass
        mock_get.return_value.status_code = 200

        # Mock generate response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Hello from Ollama!"}
        mock_post.return_value = mock_resp

        provider = OllamaProvider()
        assert provider.is_available is True
        result = provider.generate("Say hello")
        assert result == "Hello from Ollama!"

    @patch("filepilot.ai.local_ai.requests.get")
    def test_connection_check_fails(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Ollama not running")
        provider = OllamaProvider()
        assert provider.is_available is False

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_generate_with_system_prompt(self, mock_get, mock_post):
        mock_get.return_value.status_code = 200
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Summary"}
        mock_post.return_value = mock_resp

        provider = OllamaProvider()
        provider.generate("content", system_prompt="Be concise")
        payload = mock_post.call_args[1]["json"]
        assert payload["system"] == "Be concise"

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_generate_request_failure_sets_unavailable(self, mock_get, mock_post):
        mock_get.return_value.status_code = 200
        mock_post.side_effect = requests.exceptions.ConnectionError("Lost connection")

        provider = OllamaProvider()
        assert provider.is_available is True
        result = provider.generate("hello")
        assert result == ""
        # Should mark as unavailable after failure
        assert provider.is_available is False

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_chat_success(self, mock_get, mock_post):
        mock_get.return_value.status_code = 200
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": "Chat response"}}
        mock_post.return_value = mock_resp

        provider = OllamaProvider()
        result = provider.chat([{"role": "user", "content": "Hi"}])
        assert result == "Chat response"

    @patch("filepilot.ai.local_ai.requests.get")
    def test_chat_returns_empty_when_unavailable(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("No Ollama")
        provider = OllamaProvider()
        assert provider.is_available is False
        result = provider.chat([{"role": "user", "content": "Hi"}])
        assert result == ""

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_embed_success(self, mock_get, mock_post):
        mock_get.return_value.status_code = 200
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_post.return_value = mock_resp

        provider = OllamaProvider()
        result = provider.embed("hello")
        assert result == [0.1, 0.2, 0.3]

    @patch("filepilot.ai.local_ai.requests.get")
    def test_embed_returns_empty_when_unavailable(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("No Ollama")
        provider = OllamaProvider()
        result = provider.embed("hello")
        assert result == []

    @patch("filepilot.ai.local_ai.requests.get")
    def test_get_available_models(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "llama3:8b"}, {"name": "qwen2.5:7b"}]
        }
        mock_get.return_value = mock_resp

        provider = OllamaProvider()
        models = provider.get_available_models()
        assert models == ["llama3:8b", "qwen2.5:7b"]

    @patch("filepilot.ai.local_ai.requests.get")
    def test_get_available_models_on_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        provider = OllamaProvider()
        models = provider.get_available_models()
        assert models == []


class TestLlamaCppProvider:
    def test_init_defaults(self):
        provider = LlamaCppProvider()
        assert provider.model == "default"
        assert provider.api_base == "http://localhost:8080"
        assert provider.provider_name == "llama.cpp"
        assert provider.is_available is False

    def test_strips_trailing_slash(self):
        provider = LlamaCppProvider(api_base="http://localhost:8080/")
        assert provider.api_base == "http://localhost:8080"

    def test_generate_returns_empty_when_not_available(self):
        provider = LlamaCppProvider()
        result = provider.generate("hello")
        assert result == ""

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_generate_success(self, mock_get, mock_post):
        mock_get.return_value.status_code = 200
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello from llama.cpp!"}}]
        }
        mock_post.return_value = mock_resp

        provider = LlamaCppProvider()
        result = provider.generate("Say hello")
        assert result == "Hello from llama.cpp!"

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_generate_request_failure_sets_unavailable(self, mock_get, mock_post):
        mock_get.return_value.status_code = 200
        mock_post.side_effect = requests.exceptions.ConnectionError("Lost connection")

        provider = LlamaCppProvider()
        assert provider.is_available is True
        result = provider.generate("hello")
        assert result == ""
        assert provider.is_available is False

    @patch("filepilot.ai.local_ai.requests.post")
    @patch("filepilot.ai.local_ai.requests.get")
    def test_embed_success(self, mock_get, mock_post):
        mock_get.return_value.status_code = 200
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.4, 0.5, 0.6]}]
        }
        mock_post.return_value = mock_resp

        provider = LlamaCppProvider()
        result = provider.embed("hello")
        assert result == [0.4, 0.5, 0.6]


class TestLocalAICompat:
    def test_localai_is_ollama_alias(self):
        assert LocalAI is OllamaProvider
