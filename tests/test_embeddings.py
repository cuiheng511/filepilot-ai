"""Tests for embedding-based semantic search."""

import tempfile
from pathlib import Path

import pytest

from filepilot.core.embeddings import (
    EmbeddingCache,
    cosine_similarity,
    embed_text,
    get_embedding_provider,
)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector(self):
        a = [1.0, 0.0]
        b = [0.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_partial_match(self):
        a = [3.0, 4.0]
        b = [6.0, 8.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0


class TestEmbeddingCache:
    def test_put_get(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        cache.put("/path/to/file.txt", [0.1, 0.2, 0.3])
        assert cache.get("/path/to/file.txt") == [0.1, 0.2, 0.3]

    def test_get_missing(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        assert cache.get("/nonexistent") is None

    def test_remove(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        cache.put("/a", [1.0])
        cache.remove("/a")
        assert cache.get("/a") is None

    def test_clear(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        cache.put("/a", [1.0])
        cache.put("/b", [2.0])
        cache.clear()
        assert cache.get("/a") is None
        assert cache.get("/b") is None
        assert len(cache) == 0

    def test_len(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        assert len(cache) == 0
        cache.put("/a", [1.0])
        assert len(cache) == 1
        cache.put("/b", [2.0])
        assert len(cache) == 2

    def test_persistence(self):
        tmpdir = tempfile.mkdtemp()
        cache1 = EmbeddingCache(cache_dir=tmpdir)
        cache1.put("/persist.txt", [0.5, 0.5])
        cache1.save()

        cache2 = EmbeddingCache(cache_dir=tmpdir)
        assert cache2.get("/persist.txt") == [0.5, 0.5]

    def test_load_corrupt_json(self, caplog):
        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "embeddings.json"
        path.write_text("not json", encoding="utf-8")
        cache = EmbeddingCache(cache_dir=tmpdir)
        assert len(cache) == 0
        assert "Failed to load embedding cache" in caplog.text

    def test_search_re_rank(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        cache.put("/doc1.txt", [1.0, 0.0])
        cache.put("/doc2.txt", [0.0, 1.0])
        cache.put("/doc3.txt", [0.9, 0.1])

        candidates = [
            {"path": "/doc1.txt", "score": 10},
            {"path": "/doc2.txt", "score": 20},
            {"path": "/doc3.txt", "score": 15},
        ]

        query_emb = [1.0, 0.0]
        ranked = cache.search(query_emb, candidates)
        assert len(ranked) == 3
        assert ranked[0]["path"] == "/doc1.txt"  # highest cosine to query
        assert ranked[0]["semantic_score"] == pytest.approx(1.0)
        assert ranked[2]["path"] == "/doc2.txt"

    def test_search_empty_query(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        candidates = [{"path": "/a.txt", "score": 10}]
        ranked = cache.search([], candidates)
        assert ranked == candidates

    def test_search_min_score_filter(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        cache.put("/good.txt", [1.0, 0.0])
        cache.put("/bad.txt", [0.0, 1.0])

        candidates = [
            {"path": "/good.txt", "score": 10},
            {"path": "/bad.txt", "score": 10},
        ]

        ranked = cache.search([1.0, 0.0], candidates, min_score=0.5)
        assert len(ranked) == 1
        assert ranked[0]["path"] == "/good.txt"


class TestEmbedText:
    def test_returns_empty_on_no_provider(self, monkeypatch):
        monkeypatch.setattr(
            "filepilot.core.embeddings.get_embedding_provider",
            lambda: None,
        )
        assert embed_text("hello") == []

    def test_returns_empty_on_embed_failure(self, monkeypatch):
        class FailingProvider:
            def embed(self, text):
                raise RuntimeError("API down")

        monkeypatch.setattr(
            "filepilot.core.embeddings.get_embedding_provider",
            lambda: FailingProvider(),
        )
        assert embed_text("hello") == []


class TestEmbeddingProvider:
    def test_provider_cache_tracks_settings_changes(self, monkeypatch):
        import filepilot.ai.cloud_ai as cloud_ai
        import filepilot.ai.local_ai as local_ai
        import filepilot.core.config as config
        import filepilot.core.embeddings as embeddings

        class FakeProvider:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        settings = {
            "ai_provider": "ollama",
            "ai_model": "first-model",
            "ai_api_base": "http://localhost:11434",
            "ai_api_key": "",
        }

        monkeypatch.setattr(embeddings, "_embedding_provider", None)
        monkeypatch.setattr(embeddings, "_embedding_provider_key", None)
        monkeypatch.setattr(config, "load", lambda: settings.copy())
        monkeypatch.setattr(local_ai, "OllamaProvider", FakeProvider)
        monkeypatch.setattr(local_ai, "LlamaCppProvider", FakeProvider)
        monkeypatch.setattr(cloud_ai, "OpenAIProvider", FakeProvider)
        monkeypatch.setattr(cloud_ai, "AnthropicProvider", FakeProvider)

        first = get_embedding_provider()
        second = get_embedding_provider()
        assert second is first

        settings["ai_model"] = "second-model"
        third = get_embedding_provider()
        assert third is not first
        assert third.kwargs["model"] == "second-model"

        settings["ai_provider"] = "anthropic"
        assert get_embedding_provider() is None
