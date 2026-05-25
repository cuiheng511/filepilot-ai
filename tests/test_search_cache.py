"""Tests for filepilot.core.search_cache — file-based search cache"""

from pathlib import Path

from filepilot.core import search_cache


def test_cache_results_and_get(tmp_path, monkeypatch):
    monkeypatch.setattr(search_cache, "CACHE_DIR", tmp_path / "search_cache")
    results = [{"path": "/a.txt", "score": 1.0}]
    search_cache.cache_results("hello world", results)
    cached = search_cache.get_cached_results("hello world")
    assert cached == results


def test_get_cached_results_miss(tmp_path, monkeypatch):
    monkeypatch.setattr(search_cache, "CACHE_DIR", tmp_path / "search_cache")
    assert search_cache.get_cached_results("nonexistent") is None


def test_cache_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(search_cache, "CACHE_DIR", tmp_path / "search_cache")
    search_cache.cache_results("q", [{"path": "/a.txt"}])
    search_cache.cache_results("q", [{"path": "/b.txt"}])
    cached = search_cache.get_cached_results("q")
    assert cached == [{"path": "/b.txt"}]


def test_clear_search_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(search_cache, "CACHE_DIR", tmp_path / "search_cache")
    search_cache.cache_results("k1", [{"path": "/1"}])
    search_cache.cache_results("k2", [{"path": "/2"}])
    cleared = search_cache.clear_search_cache()
    assert cleared == 2
    assert search_cache.get_cached_results("k1") is None
    assert search_cache.get_cached_results("k2") is None


def test_get_cache_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(search_cache, "CACHE_DIR", tmp_path / "search_cache")
    stats = search_cache.get_cache_stats()
    assert "entries" in stats
    assert "total_size_bytes" in stats


def test_cache_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(search_cache, "CACHE_DIR", tmp_path / "search_cache")
    monkeypatch.setattr(search_cache, "CACHE_TTL_HOURS", 0)
    search_cache.cache_results("stale", [{"path": "/stale"}])
    cached = search_cache.get_cached_results("stale")
    assert cached is None
