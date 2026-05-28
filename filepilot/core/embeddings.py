"""Embedding cache for semantic search."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import sqlite3
import time
from collections.abc import Iterable
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


def _settings_provider_key() -> str:
    """Return a stable key for the current embedding provider settings."""
    try:
        from filepilot.core.config import load

        settings = load()
        provider = settings.get("ai_provider", "ollama")
        model = settings.get("ai_model", "qwen2.5:7b")
        api_base = settings.get("ai_api_base", "http://localhost:11434")
        api_key = settings.get("ai_api_key", "")
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest() if api_key else ""
        return "|".join([provider, model, api_base, api_key_hash])
    except Exception:
        logger.debug("Failed to read embedding provider settings", exc_info=True)
        return "unknown"


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
    """Persistent embedding cache backed by SQLite.

    Old JSON caches are migrated on startup. New entries include optional file
    metadata and the active provider key so stale vectors are less likely to be
    reused after a file or model changes.
    """

    def __init__(self, cache_dir: str | Path = "~/.filepilot"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_path = self.cache_dir / "embeddings.sqlite3"
        self.legacy_json_path = self.cache_dir / "embeddings.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cache_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._ensure_schema()
        self._migrate_legacy_json()

    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                cache_key TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                provider_key TEXT NOT NULL,
                mtime REAL,
                size INTEGER,
                embedding TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_path ON embeddings(path)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_embeddings_provider_path "
            "ON embeddings(provider_key, path)"
        )
        self._conn.commit()

    def _migrate_legacy_json(self) -> None:
        if not self.legacy_json_path.exists():
            return
        try:
            data = json.loads(self.legacy_json_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("legacy embedding cache is not an object")
        except Exception:
            logger.warning("Failed to load embedding cache, starting fresh")
            return

        provider_key = _settings_provider_key()
        for path, embedding in data.items():
            if isinstance(path, str) and isinstance(embedding, list):
                self._put_row(path, embedding, None, None, provider_key)
        self._conn.commit()
        try:
            self.legacy_json_path.replace(self.legacy_json_path.with_suffix(".json.migrated"))
        except OSError:
            logger.debug("Failed to rename migrated embedding JSON cache", exc_info=True)

    @staticmethod
    def _cache_key(
        path: str,
        mtime: float | None,
        size: int | None,
        provider_key: str,
    ) -> str:
        payload = {
            "path": path,
            "mtime": mtime,
            "size": size,
            "provider_key": provider_key,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def save(self) -> None:
        self._conn.commit()

    def get(
        self,
        path: str,
        mtime: float | None = None,
        size: int | None = None,
        provider_key: str | None = None,
    ) -> list[float] | None:
        provider = provider_key or _settings_provider_key()
        cache_key = self._cache_key(path, mtime, size, provider)
        row = self._conn.execute(
            "SELECT embedding FROM embeddings WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None and mtime is None and size is None:
            row = self._conn.execute(
                """
                SELECT embedding FROM embeddings
                WHERE path = ? AND provider_key = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (path, provider),
            ).fetchone()
        if row is None:
            return None
        try:
            return cast("list[float]", json.loads(row[0]))
        except json.JSONDecodeError:
            logger.warning("Failed to decode cached embedding for %s", path)
            return None

    def put(
        self,
        path: str,
        embedding: list[float],
        mtime: float | None = None,
        size: int | None = None,
        provider_key: str | None = None,
    ) -> None:
        self._put_row(path, embedding, mtime, size, provider_key or _settings_provider_key())

    def _put_row(
        self,
        path: str,
        embedding: list[float],
        mtime: float | None,
        size: int | None,
        provider_key: str,
    ) -> None:
        cache_key = self._cache_key(path, mtime, size, provider_key)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO embeddings
                (cache_key, path, provider_key, mtime, size, embedding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                path,
                provider_key,
                mtime,
                size,
                json.dumps(embedding, separators=(",", ":")),
                time.time(),
            ),
        )

    def remove(self, path: str) -> None:
        self._conn.execute("DELETE FROM embeddings WHERE path = ?", (path,))

    def clear(self) -> None:
        self._conn.execute("DELETE FROM embeddings")

    def stats(self) -> dict[str, int | str]:
        """Return cache storage and row statistics."""
        self.save()
        size_bytes = self.cache_path.stat().st_size if self.cache_path.exists() else 0
        provider_count_row = self._conn.execute(
            "SELECT COUNT(DISTINCT provider_key) FROM embeddings"
        ).fetchone()
        return {
            "entries": len(self),
            "providers": int(provider_count_row[0]) if provider_count_row else 0,
            "size_bytes": size_bytes,
            "path": str(self.cache_path),
        }

    def prune_missing_paths(self) -> int:
        """Remove cache rows for files that no longer exist on disk."""
        rows = self._conn.execute("SELECT DISTINCT path FROM embeddings").fetchall()
        missing = [row[0] for row in rows if not Path(row[0]).exists()]
        return self.remove_paths(missing)

    def prune_provider(self, provider_key: str | None = None) -> int:
        """Remove entries for the given provider, defaulting to the active provider."""
        provider = provider_key or _settings_provider_key()
        cursor = self._conn.execute(
            "DELETE FROM embeddings WHERE provider_key = ?",
            (provider,),
        )
        return int(cursor.rowcount or 0)

    def remove_paths(self, paths: Iterable[str]) -> int:
        """Remove all entries for the provided paths."""
        path_list = list(paths)
        if not path_list:
            return 0
        before = self._conn.total_changes
        self._conn.executemany("DELETE FROM embeddings WHERE path = ?", [(p,) for p in path_list])
        return int(self._conn.total_changes - before)

    def vacuum(self) -> None:
        """Compact the SQLite database after large deletes."""
        self.save()
        self._conn.execute("VACUUM")

    def search(
        self,
        query_embedding: list[float],
        candidates: list[dict],
        min_score: float = 0.0,
    ) -> list[dict]:
        """Re-rank candidates by cosine similarity against query embedding.

        Each candidate dict gets a ``semantic_score`` key (0-1).
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
        row = self._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
        return int(row[0]) if row else 0
