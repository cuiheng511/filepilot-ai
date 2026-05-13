"""Cloud AI Engine — Supports OpenAI / Anthropic / Google Gemini / DeepSeek"""

import json
import logging
from typing import Callable

import requests

from filepilot.ai.base import AIProvider

logger = logging.getLogger("filepilot.ai.cloud")


class OpenAIProvider(AIProvider):
    """OpenAI and compatible APIs (DeepSeek, Moonshot, etc.)"""

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini",
                 api_base: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self._available = bool(api_key)

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def configure(self, api_key: str, model: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        if model:
            self.model = model
        if api_base:
            self.api_base = api_base.rstrip("/")
        self._available = bool(api_key)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2048,
                 stream=False, on_token=None) -> str:
        if not self._available:
            return ""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._chat(messages, temperature, max_tokens, stream, on_token)

    def _chat(self, messages, temperature, max_tokens, stream, on_token):
        payload = {
            "model": self.model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens, "stream": stream,
        }
        try:
            if stream:
                full = []
                with requests.post(f"{self.api_base}/chat/completions",
                                   headers=self._headers(), json=payload, stream=True, timeout=120) as resp:
                    for line in resp.iter_lines():
                        if line:
                            line = line.decode("utf-8", errors="replace")
                            if line.startswith("data: ") and line != "data: [DONE]":
                                try:
                                    delta = json.loads(line[6:])["choices"][0].get("delta", {})
                                    token = delta.get("content", "")
                                    if token:
                                        full.append(token)
                                        if on_token:
                                            on_token(token)
                                except (json.JSONDecodeError, KeyError):
                                    continue
                return "".join(full)
            else:
                resp = requests.post(f"{self.api_base}/chat/completions",
                                     headers=self._headers(), json=payload, timeout=60)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except requests.RequestException:
            self._available = False
        return ""

    def chat(self, messages, temperature=0.7, max_tokens=2048) -> str:
        return self._chat(messages, temperature, max_tokens, False, None)

    def embed(self, text, model: str | None = None) -> list[float]:
        if not self._available:
            return []
        try:
            resp = requests.post(f"{self.api_base}/embeddings", headers=self._headers(),
                                 json={"input": text, "model": model or "text-embedding-3-small"}, timeout=30)
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
        except (requests.RequestException, KeyError):
            pass
        return []


class AnthropicProvider(AIProvider):
    """Anthropic Claude"""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514",
                 api_base: str = "https://api.anthropic.com"):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self._available = bool(api_key)

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def provider_name(self) -> str:
        return "Anthropic"

    def configure(self, api_key: str, model: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        if model:
            self.model = model
        if api_base:
            self.api_base = api_base.rstrip("/")
        self._available = bool(api_key)

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2048,
                 stream=False, on_token=None) -> str:
        if not self._available:
            return ""
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            if stream:
                full = []
                with requests.post(f"{self.api_base}/v1/messages",
                                   headers=self._headers(), json=payload, stream=True, timeout=120) as resp:
                    for line in resp.iter_lines():
                        if line:
                            line = line.decode("utf-8", errors="replace")
                            if line.startswith("data: "):
                                try:
                                    event = json.loads(line[6:])
                                    if event.get("type") == "content_block_delta":
                                        token = event.get("delta", {}).get("text", "")
                                        if token:
                                            full.append(token)
                                            if on_token:
                                                on_token(token)
                                except json.JSONDecodeError:
                                    continue
                return "".join(full)
            else:
                resp = requests.post(f"{self.api_base}/v1/messages",
                                     headers=self._headers(), json=payload, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    return "".join(b.get("text", "") for b in data.get("content", []))
        except requests.RequestException:
            self._available = False
        return ""

    def chat(self, messages, temperature=0.7, max_tokens=2048) -> str:
        if not self._available:
            return ""
        # Anthropic uses 'system' parameter instead of system role in messages
        system = ""
        user_messages = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            else:
                user_messages.append(m)
        if not user_messages:
            user_messages = [{"role": "user", "content": ""}]
        payload = {
            "model": self.model, "max_tokens": max_tokens, "temperature": temperature,
            "messages": user_messages, "stream": False,
        }
        if system:
            payload["system"] = system
        try:
            resp = requests.post(f"{self.api_base}/v1/messages",
                                 headers=self._headers(), json=payload, timeout=60)
            if resp.status_code == 200:
                return "".join(b.get("text", "") for b in resp.json().get("content", []))
        except requests.RequestException:
            self._available = False
        return ""


# Backward compatibility alias
CloudAI = OpenAIProvider
