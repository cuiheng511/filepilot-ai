"""Tests for filepilot.core.service_container — typed service locator"""

from filepilot.core.file_scanner import FileScanner
from filepilot.core.service_container import ServiceContainer


def test_override_scanner():
    custom = FileScanner()
    svc = ServiceContainer(scanner=custom)
    assert svc.scanner is custom


def test_empty_container():
    svc = ServiceContainer()
    assert svc.scanner is None
    assert svc.indexer is None
    assert svc.organizer is None
    assert svc.duplicate_finder is None
    assert svc.local_ai is None


def test_get_scanner_creates_default():
    svc = ServiceContainer()
    assert svc.scanner is None
    scanner = svc.get_scanner()
    assert scanner is not None
    assert svc.scanner is scanner  # cached


def test_get_indexer_creates_default():
    svc = ServiceContainer()
    assert svc.get_indexer() is not None


def test_get_organizer_creates_default():
    svc = ServiceContainer()
    assert svc.get_organizer() is not None


def test_get_duplicate_finder_creates_default():
    svc = ServiceContainer()
    assert svc.get_duplicate_finder() is not None


def test_get_watcher_creates_default():
    svc = ServiceContainer()
    assert svc.get_watcher() is not None


def test_search_cache_methods():
    svc = ServiceContainer()
    assert svc.search_cache_get("test") is None
    assert svc.search_cache_stats() == {}
    svc.search_cache_clear()  # no-op, should not raise


def test_dataclass_repr():
    svc = ServiceContainer(scanner=FileScanner())
    rep = repr(svc)
    assert "scanner" in rep
