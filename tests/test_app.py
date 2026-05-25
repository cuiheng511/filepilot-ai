"""Tests for filepilot.app — application bootstrap functions"""

from filepilot.app import create_service_container, load_settings


def test_load_settings():
    settings = load_settings()
    assert isinstance(settings, dict)
    assert "ai_provider" in settings


def test_create_service_container():
    settings = load_settings()
    svc = create_service_container(settings)
    assert svc is not None
    assert hasattr(svc, "scanner")
    assert hasattr(svc, "indexer")


def test_service_container_has_search_cache_methods():
    settings = load_settings()
    svc = create_service_container(settings)
    assert hasattr(svc, "search_cache_get")
    assert hasattr(svc, "search_cache_set")
    assert hasattr(svc, "search_cache_clear")
