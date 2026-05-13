"""云端 AI 引擎 — 通过 OpenAI API 调用云端模型"""

import json
from pathlib import Path
from typing import Callable

import requests


class CloudAI:
    """云端 AI 推理引擎

    支持 OpenAI API 兼容接口，可切换不同服务商。
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_API_BASE = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        api_base: str = DEFAULT_API_BASE,
    ):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self._available = bool(api_key)

    @property
    def is_available(self) -> bool:
        return self._available

    def configure(self, api_key: str, model: str | None = None, api_base: str | None = None):
        """配置 API 参数"""
        self.api_key = api_key
        if model:
            self.model = model
        if api_base:
            self.api_base = api_base.rstrip("/")
        self._available = bool(api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """生成文本"""
        if not self._available:
            return ""

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if stream:
            return self._stream_chat(payload, on_token)
        else:
            return self._simple_chat(payload)

    def _simple_chat(self, payload: dict) -> str:
        """非流式对话"""
        try:
            resp = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except requests.RequestException:
            pass
        return ""

    def _stream_chat(self, payload: dict, on_token: Callable[[str], None] | None) -> str:
        """流式对话"""
        full_response: list[str] = []
        try:
            with requests.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
                stream=True,
                timeout=120,
            ) as resp:
                for line in resp.iter_lines():
                    if line:
                        line = line.decode("utf-8", errors="replace")
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    full_response.append(token)
                                    if on_token:
                                        on_token(token)
                            except json.JSONDecodeError:
                                continue
        except requests.RequestException:
            pass

        return "".join(full_response)

    def embed(self, text: str, model: str | None = None) -> list[float]:
        """生成文本嵌入向量"""
        if not self._available:
            return []

        try:
            resp = requests.post(
                f"{self.api_base}/embeddings",
                headers=self._headers(),
                json={
                    "input": text,
                    "model": model or "text-embedding-3-small",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
        except requests.RequestException:
            pass
        return []
