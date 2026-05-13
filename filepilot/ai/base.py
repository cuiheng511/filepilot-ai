"""AI Provider Abstract Base Class — unified interface for local/cloud/third-party models"""

from abc import ABC, abstractmethod
from collections.abc import Callable


class AIProvider(ABC):
    """AI Provider unified interface

    All AI engines (Ollama, OpenAI, Anthropic, Gemini, llama.cpp, etc.)
    implement this interface; upper-level code doesn't need to care about
    underlying protocol differences.
    """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the AI engine is available"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name"""
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
        """Generate text"""
        ...

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Chat interface (default implementation: concatenate into prompt)"""
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
        """Generate embedding vectors (default implementation: returns empty)"""
        return []

    def get_available_models(self) -> list[str]:
        """Get available models list (default implementation: returns empty)"""
        return []
