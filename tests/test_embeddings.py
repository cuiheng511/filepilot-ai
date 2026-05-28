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

    def test_uses_sqlite_cache_file(self):
        tmpdir = tempfile.mkdtemp()
        cache = EmbeddingCache(cache_dir=tmpdir)
        cache.put("/persist.txt", [0.5, 0.5])
        cache.save()

        assert cache.cache_path.name == "embeddings.sqlite3"
        assert cache.cache_path.exists()

    def test_load_corrupt_json(self, caplog):
        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "embeddings.json"
        path.write_text("not json", encoding="utf-8")
        cache = EmbeddingCache(cache_dir=tmpdir)
        assert len(cache) == 0
        assert "Failed to load embedding cache" in caplog.text

    def test_migrates_legacy_json_cache(self, tmp_path):
        legacy = tmp_path / "embeddings.json"
        legacy.write_text('{"/legacy.txt": [0.3, 0.7]}', encoding="utf-8")

        cache = EmbeddingCache(cache_dir=tmp_path)

        assert cache.get("/legacy.txt") == [0.3, 0.7]
        assert not legacy.exists()
        assert (tmp_path / "embeddings.json.migrated").exists()

    def test_provider_and_file_metadata_can_separate_entries(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        cache.put("/a", [1.0], mtime=1.0, size=10, provider_key="p1")
        cache.put("/a", [2.0], mtime=2.0, size=10, provider_key="p1")

        assert cache.get("/a", mtime=1.0, size=10, provider_key="p1") == [1.0]
        assert cache.get("/a", mtime=2.0, size=10, provider_key="p1") == [2.0]

    def test_stats_and_prune_missing_paths(self, tmp_path):
        existing = tmp_path / "exists.txt"
        existing.write_text("hello", encoding="utf-8")
        cache = EmbeddingCache(cache_dir=tmp_path)
        cache.put(str(existing), [1.0], provider_key="p1")
        cache.put(str(tmp_path / "missing.txt"), [2.0], provider_key="p1")
        cache.save()

        stats = cache.stats()
        assert stats["entries"] == 2
        assert stats["providers"] == 1

        assert cache.prune_missing_paths() == 1
        assert cache.get(str(existing), provider_key="p1") == [1.0]
        assert cache.get(str(tmp_path / "missing.txt"), provider_key="p1") is None

    def test_prune_provider(self):
        cache = EmbeddingCache(cache_dir=tempfile.mkdtemp())
        cache.put("/a", [1.0], provider_key="p1")
        cache.put("/a", [2.0], provider_key="p2")

        assert cache.prune_provider("p1") == 1
        assert cache.get("/a", provider_key="p1") is None
        assert cache.get("/a", provider_key="p2") == [2.0]

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


class TestIntegrationWithIndexer:
    """Integration test: embedding_extractor path in indexer + search_semantic."""

    def test_index_files_with_embedding_extractor(self, tmp_path, monkeypatch):
        """Verify that embedding_extractor is called and saved during indexing."""
        from datetime import datetime

        from filepilot.core.file_scanner import FileInfo
        from filepilot.core.indexer import FileIndexer
        from filepilot.utils.file_utils import FileCategory

        call_log = []

        def fake_embed(text):
            call_log.append(text)
            return [0.1, 0.2, 0.3]

        monkeypatch.setattr(
            "filepilot.core.indexer.embed_text",
            fake_embed,
        )

        now = datetime.now()
        fi = FileInfo(
            path=tmp_path / "test.txt",
            name="test.txt",
            extension=".txt",
            size_bytes=10,
            size_str="10 B",
            category=FileCategory.DOCUMENT,
            mime_type="text/plain",
            modified_time=now,
            created_time=now,
        )
        fi.path.write_text("hello world", encoding="utf-8")

        indexer = FileIndexer(tmp_path / "index")
        indexed = indexer.index_files(
            [fi],
            embedding_extractor=lambda f: "hello world",
        )

        assert indexed == 1
        assert len(call_log) == 1
        assert call_log[0] == "hello world"
        assert len(indexer._embed_cache) == 1
        assert indexer._embed_cache.get(str(fi.path)) == [0.1, 0.2, 0.3]

    def test_search_semantic_fallback_when_no_embeddings(self, tmp_path, monkeypatch):
        """Without embeddings, search_semantic should fall back to Whoosh results."""
        from datetime import datetime

        from filepilot.core.file_scanner import FileInfo
        from filepilot.core.indexer import FileIndexer
        from filepilot.utils.file_utils import FileCategory

        monkeypatch.setattr(
            "filepilot.core.indexer.embed_text",
            lambda _: [],
        )

        now = datetime.now()
        fi = FileInfo(
            path=tmp_path / "report.txt",
            name="report.txt",
            extension=".txt",
            size_bytes=10,
            size_str="10 B",
            category=FileCategory.DOCUMENT,
            mime_type="text/plain",
            modified_time=now,
            created_time=now,
        )
        fi.path.write_text("quarterly report data", encoding="utf-8")

        indexer = FileIndexer(tmp_path / "index")
        indexer.index_files([fi], content_extractor=lambda _: "quarterly report data")

        results = indexer.search_semantic("report", limit=10)
        assert len(results) >= 1
        assert results[0]["filename"] == "report.txt"
        assert "semantic_score" not in results[0]

    def test_search_semantic_reranks(self, tmp_path, monkeypatch):
        """Verify that search_semantic re-ranks by embedding similarity."""
        from datetime import datetime

        from filepilot.core.file_scanner import FileInfo
        from filepilot.core.indexer import FileIndexer
        from filepilot.utils.file_utils import FileCategory

        # Simulate: doc1 matches query (high cosine), doc2 doesn't (low cosine)
        embeddings = {
            "doc1": [1.0, 0.0],
            "doc2": [0.0, 1.0],
        }

        def mock_embed(text):
            # Return the query embedding
            return [1.0, 0.0] if "report" in text else []

        monkeypatch.setattr(
            "filepilot.core.indexer.embed_text",
            mock_embed,
        )

        now = datetime.now()
        docs = []
        for _i, (name, _emb) in enumerate(embeddings.items()):
            fi = FileInfo(
                path=tmp_path / f"{name}.txt",
                name=f"{name}.txt",
                extension=".txt",
                size_bytes=10,
                size_str="10 B",
                category=FileCategory.DOCUMENT,
                mime_type="text/plain",
                modified_time=now,
                created_time=now,
            )
            # Both files contain "report" so Whoosh will find both
            fi.path.write_text(f"quarterly report content of {name}", encoding="utf-8")
            docs.append(fi)

        indexer = FileIndexer(tmp_path / "index")
        indexer.index_files(
            docs,
            content_extractor=lambda f: f.path.read_text("utf-8"),
            embedding_extractor=lambda f: f.path.read_text("utf-8"),
        )

        # Manually set embeddings (since mock_embed returns query embedding, not doc embedding)
        for name, emb in embeddings.items():
            indexer._embed_cache.put(str(tmp_path / f"{name}.txt"), emb)

        results = indexer.search_semantic("report", limit=10)
        assert len(results) == 2
        assert results[0]["filename"] == "doc1.txt"
        assert results[0]["semantic_score"] == pytest.approx(1.0)
        assert results[1]["filename"] == "doc2.txt"


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
