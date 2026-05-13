"""本地 AI 引擎 — 通过 Ollama 运行本地模型"""

import json
import subprocess
import threading
from pathlib import Path
from typing import Callable

import requests


class LocalAI:
    """本地 AI 推理引擎

    通过 Ollama API 调用本地运行的 LLM 模型。
    数据不离本机，完全离线可用。
    """

    DEFAULT_MODEL = "qwen2.5:7b"  # 推荐模型
    OLLAMA_API_BASE = "http://localhost:11434"

    def __init__(self, model: str = DEFAULT_MODEL, api_base: str = OLLAMA_API_BASE):
        self.model = model
        self.api_base = api_base
        self._available = False
        self._check_connection()

    def _check_connection(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            resp = requests.get(f"{self.api_base}/api/tags", timeout=5)
            self._available = resp.status_code == 200
        except requests.ConnectionError:
            self._available = False
        return self._available

    @property
    def is_available(self) -> bool:
        """Ollama 服务是否可用"""
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """生成文本

        Args:
            prompt: 输入提示
            system_prompt: 系统提示词
            temperature: 温度参数 (0.0-1.0)
            max_tokens: 最大生成 token 数
            stream: 是否流式输出
            on_token: 流式回调函数

        Returns:
            生成的文本
        """
        if not self._available:
            return ""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": stream,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if stream:
            return self._stream_generate(payload, on_token)
        else:
            return self._simple_generate(payload)

    def _simple_generate(self, payload: dict) -> str:
        """非流式生成"""
        try:
            resp = requests.post(
                f"{self.api_base}/api/generate",
                json=payload,
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
        except requests.RequestException:
            self._available = False
        return ""

    def _stream_generate(
        self,
        payload: dict,
        on_token: Callable[[str], None] | None,
    ) -> str:
        """流式生成"""
        full_response: list[str] = []
        try:
            with requests.post(
                f"{self.api_base}/api/generate",
                json=payload,
                stream=True,
                timeout=120,
            ) as resp:
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            full_response.append(token)
                            if on_token:
                                on_token(token)
                        except json.JSONDecodeError:
                            continue
        except requests.RequestException:
            self._available = False

        return "".join(full_response)

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """对话接口"""
        if not self._available:
            return ""

        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }

        try:
            resp = requests.post(
                f"{self.api_base}/api/chat",
                json=payload,
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except requests.RequestException:
            self._available = False
        return ""

    def embed(self, text: str) -> list[float]:
        """生成文本嵌入向量"""
        if not self._available:
            return []

        try:
            resp = requests.post(
                f"{self.api_base}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json().get("embedding", [])
        except requests.RequestException:
            self._available = False
        return []

    def get_available_models(self) -> list[str]:
        """获取本地可用模型列表"""
        try:
            resp = requests.get(f"{self.api_base}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m["name"] for m in models]
        except requests.RequestException:
            pass
        return []

    def pull_model(self, model: str, progress_callback: Callable[[str], None] | None = None) -> bool:
        """下载模型"""
        try:
            with requests.post(
                f"{self.api_base}/api/pull",
                json={"name": model},
                stream=True,
                timeout=None,
            ) as resp:
                for line in resp.iter_lines():
                    if line and progress_callback:
                        try:
                            data = json.loads(line)
                            status = data.get("status", "")
                            progress_callback(status)
                        except json.JSONDecodeError:
                            continue
                return True
        except requests.RequestException:
            return False
