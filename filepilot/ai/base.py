"""AI Provider 抽象基类 — 统一本地/云端/第三方模型接口"""

from abc import ABC, abstractmethod
from typing import Callable


class AIProvider(ABC):
    """AI Provider 统一接口

    所有 AI 引擎（Ollama、OpenAI、Anthropic、Gemini、llama.cpp 等）
    都实现此接口，上层代码无需关心底层协议差异。
    """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """AI 引擎是否可用"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        ...

    @abstractmethod
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
        ...

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """对话接口（默认实现：拼接为 prompt）"""
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"[System] {content}")
            else:
                parts.append(content)
        return self.generate("\n".join(parts), temperature=temperature, max_tokens=max_tokens)

    def embed(self, text: str) -> list[float]:
        """生成嵌入向量（默认实现：返回空）"""
        return []

    def get_available_models(self) -> list[str]:
        """获取可用模型列表（默认实现：返回空）"""
        return []
