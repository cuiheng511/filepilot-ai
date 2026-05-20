"""Embedding cache for semantic search"""

import hashlib
import json
import logging
import math
from pathlib import Path
from typing import cast

logger = logging.getLogger("filepilot.embeddings")

_embedding_provider: object | None = None
_embedding_provider_key: tuple[str, str, str, str] | None = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors (pure Python, no numpy)."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_embedding_provider():
    """Create the active AI provider configured by user settings."""
    from filepilot.ai.cloud_ai import AnthropicProvider, OpenAIProvider
    from filepilot.ai.local_ai import LlamaCppProvider, OllamaProvider
    from filepilot.core.config import load

    settings = load()
    provider = settings.get("ai_provider", "ollama")
    model = settings.get("ai_model", "qwen2.5:7b")
    api_base = settings.get("ai_api_base", "http://localhost:11434")
    api_key = settings.get("ai_api_key", "")
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest() if api_key else ""
    provider_key = (provider, model, api_base, api_key_hash)

    provider_map = {
        "ollama": lambda: OllamaProvider(model=model, api_base=api_base),
        "llamacpp": lambda: LlamaCppProvider(model=model, api_base=api_base),
        "openai": lambda: OpenAIProvider(api_key=api_key, model=model, api_base=api_base),
        "custom": lambda: OpenAIProvider(api_key=api_key, model=model, api_base=api_base),
        "anthropic": lambda: AnthropicProvider(api_key=api_key, model=model, api_base=api_base),
    }
    global _embedding_provider, _embedding_provider_key
    if provider == "anthropic":
        _embedding_provider = None
        _embedding_provider_key = provider_key
        return None
    if _embedding_provider is not None and _embedding_provider_key == provider_key:
        return _embedding_provider
    ai = provider_map.get(provider, provider_map["ollama"])()
    _embedding_provider = ai
    _embedding_provider_key = provider_key
    return ai


def embed_text(text: str, max_chars: int = 2000) -> list[float]:
    """Embed text using the configured AI provider.

    Returns empty list if no embedding-capable provider is available.
    """
    ai = get_embedding_provider()
    if ai is None:
        return []
    try:
        return cast("list[float]", ai.embed(text[:max_chars]))
    except Exception:
        logger.exception("Failed to embed text")
        return []


class EmbeddingCache:
    """Persistent embedding cache stored as JSON.

    Maps file path -> embedding vector for fast semantic search.
    """

    def __init__(self, cache_dir: str | Path = "~/.filepilot"):
        self.cache_path = Path(cache_dir).expanduser() / "embeddings.json"
        self._data: dict[str, list[float]] = {}
        self._load()

    def _load(self) -> None:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                logger.warning("Failed to load embedding cache, starting fresh")
                self._data = {}

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f)
        tmp.replace(self.cache_path)

    def get(self, path: str) -> list[float] | None:
        return self._data.get(path)

    def put(self, path: str, embedding: list[float]) -> None:
        self._data[path] = embedding

    def remove(self, path: str) -> None:
        self._data.pop(path, None)

    def clear(self) -> None:
        self._data.clear()

    def search(
        self,
        query_embedding: list[float],
        candidates: list[dict],
        min_score: float = 0.0,
    ) -> list[dict]:
        """Re-rank candidates by cosine similarity against query embedding.

        Each candidate dict gets a ``semantic_score`` key (0–1).
        Candidates without a cached embedding fall back to their Whoosh score.
        """
        if not query_embedding:
            return candidates

        for r in candidates:
            path = r.get("path", "")
            cached = self.get(path)
            if cached:
                r["semantic_score"] = cosine_similarity(query_embedding, cached)
            else:
                r["semantic_score"] = r.get("score", 0) / 100.0

        scored = [r for r in candidates if r.get("semantic_score", 0) >= min_score]
        scored.sort(key=lambda r: r["semantic_score"], reverse=True)
        return scored

    def __len__(self) -> int:
        return len(self._data)
