"""本地 AI 引擎 — 支持 Ollama / llama.cpp / vLLM / LM Studio"""

import json
import logging
from typing import Callable

import requests

from filepilot.ai.base import AIProvider

logger = logging.getLogger("filepilot.ai.local")


class OllamaProvider(AIProvider):
    """Ollama 本地模型"""

    def __init__(self, model: str = "qwen2.5:7b", api_base: str = "http://localhost:11434"):
        self.model = model
        self.api_base = api_base.rstrip("/")
        self._available = False
        self._check_connection()

    def _check_connection(self) -> bool:
        try:
            resp = requests.get(f"{self.api_base}/api/tags", timeout=5)
            self._available = resp.status_code == 200
        except requests.ConnectionError:
            self._available = False
        return self._available

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def provider_name(self) -> str:
        return "Ollama"

    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2048,
                 stream=False, on_token=None) -> str:
        if not self._available:
            return ""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if stream:
            return self._stream_generate(payload, on_token)
        return self._simple_generate(payload)

    def _simple_generate(self, payload):
        try:
            resp = requests.post(f"{self.api_base}/api/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except requests.RequestException:
            self._available = False
        return ""

    def _stream_generate(self, payload, on_token):
        full = []
        try:
            with requests.post(f"{self.api_base}/api/generate", json=payload, stream=True, timeout=120) as resp:
                for line in resp.iter_lines():
                    if line:
                        try:
                            token = json.loads(line).get("response", "")
                            full.append(token)
                            if on_token:
                                on_token(token)
                        except json.JSONDecodeError:
                            continue
        except requests.RequestException:
            self._available = False
        return "".join(full)

    def chat(self, messages, temperature=0.7, max_tokens=2048) -> str:
        if not self._available:
            return ""
        try:
            resp = requests.post(f"{self.api_base}/api/chat", json={
                "model": self.model, "messages": messages,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            }, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content", "")
        except requests.RequestException:
            self._available = False
        return ""

    def embed(self, text) -> list[float]:
        if not self._available:
            return []
        try:
            resp = requests.post(f"{self.api_base}/api/embeddings",
                                 json={"model": self.model, "prompt": text}, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("embedding", [])
        except requests.RequestException:
            self._available = False
        return []

    def get_available_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.api_base}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except requests.RequestException:
            pass
        return []


class LlamaCppProvider(AIProvider):
    """llama.cpp server / LM Studio / vLLM（OpenAI 兼容接口）"""

    def __init__(self, model: str = "default", api_base: str = "http://localhost:8080"):
        self.model = model
        self.api_base = api_base.rstrip("/")
        self._available = False
        self._check_connection()

    def _check_connection(self) -> bool:
        try:
            resp = requests.get(f"{self.api_base}/v1/models", timeout=5)
            self._available = resp.status_code == 200
        except requests.ConnectionError:
            self._available = False
        return self._available

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def provider_name(self) -> str:
        return "llama.cpp"

    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2048,
                 stream=False, on_token=None) -> str:
        if not self._available:
            return ""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._chat_completions(messages, temperature, max_tokens, stream, on_token)

    def _chat_completions(self, messages, temperature, max_tokens, stream, on_token):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        headers = {"Content-Type": "application/json"}
        try:
            if stream:
                full = []
                with requests.post(f"{self.api_base}/v1/chat/completions",
                                   json=payload, headers=headers, stream=True, timeout=120) as resp:
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
                resp = requests.post(f"{self.api_base}/v1/chat/completions",
                                     json=payload, headers=headers, timeout=120)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except requests.RequestException:
            self._available = False
        return ""

    def chat(self, messages, temperature=0.7, max_tokens=2048) -> str:
        return self._chat_completions(messages, temperature, max_tokens, False, None)

    def embed(self, text) -> list[float]:
        try:
            resp = requests.post(f"{self.api_base}/v1/embeddings",
                                 json={"input": text, "model": self.model}, timeout=30)
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
        except (requests.RequestException, KeyError):
            pass
        return []


# 向后兼容：LocalAI = OllamaProvider
LocalAI = OllamaProvider
