"""Tests for community plugin registry safety."""

import hashlib
from unittest.mock import MagicMock, patch

from filepilot.core.plugin_registry import (
    PluginEntry,
    PluginRegistry,
    get_plugin_path,
    is_safe_plugin_name,
    verify_plugin_sha256,
)


def test_plugin_name_validation_rejects_path_traversal():
    assert is_safe_plugin_name("csv_analyzer")
    assert not is_safe_plugin_name("../outside")
    assert not is_safe_plugin_name("nested/plugin")


def test_get_plugin_path_stays_inside_plugins_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("filepilot.core.plugin_registry.PLUGINS_DIR", tmp_path)

    assert get_plugin_path("safe_plugin") == (tmp_path / "safe_plugin.py").resolve()


def test_install_plugin_rejects_unsafe_name(tmp_path, monkeypatch):
    monkeypatch.setattr("filepilot.core.plugin_registry.PLUGINS_DIR", tmp_path)
    entry = PluginEntry(
        name="../outside",
        display_name="Bad",
        description="",
        version="1.0.0",
        author="unknown",
        url="https://example.test/bad.py",
    )

    assert PluginRegistry().install_plugin(entry) is False
    assert not (tmp_path.parent / "outside.py").exists()


def test_install_plugin_writes_safe_name_inside_plugins_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("filepilot.core.plugin_registry.PLUGINS_DIR", tmp_path)
    content = b"from filepilot.core.plugin_system import BaseFileExtractor\n"
    entry = PluginEntry(
        name="safe_plugin",
        display_name="Safe",
        description="",
        version="1.0.0",
        author="unknown",
        url="https://example.test/safe.py",
        sha256=hashlib.sha256(content).hexdigest(),
    )
    response = MagicMock()
    response.content = content

    with patch("filepilot.core.plugin_registry.requests.get", return_value=response):
        assert PluginRegistry().install_plugin(entry) is True

    assert (tmp_path / "safe_plugin.py").exists()
    assert entry.installed is True


def test_plugin_sha256_validation():
    content = "print('hello')\n"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

    assert verify_plugin_sha256(content, digest)
    assert verify_plugin_sha256(content.encode("utf-8"), digest)
    assert not verify_plugin_sha256(content, "0" * 64)


def test_install_plugin_rejects_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr("filepilot.core.plugin_registry.PLUGINS_DIR", tmp_path)
    entry = PluginEntry(
        name="safe_plugin",
        display_name="Safe",
        description="",
        version="1.0.0",
        author="unknown",
        url="https://example.test/safe.py",
        sha256="0" * 64,
    )
    response = MagicMock()
    response.content = b"print('tampered')\n"

    with patch("filepilot.core.plugin_registry.requests.get", return_value=response):
        assert PluginRegistry().install_plugin(entry) is False

    assert not (tmp_path / "safe_plugin.py").exists()


def test_install_plugin_rejects_missing_hash_pin(tmp_path, monkeypatch):
    monkeypatch.setattr("filepilot.core.plugin_registry.PLUGINS_DIR", tmp_path)
    entry = PluginEntry(
        name="safe_plugin",
        display_name="Safe",
        description="",
        version="1.0.0",
        author="unknown",
        url="https://example.test/safe.py",
    )
    response = MagicMock()
    response.content = b"print('unpinned')\n"

    with patch("filepilot.core.plugin_registry.requests.get", return_value=response):
        assert PluginRegistry().install_plugin(entry) is False

    assert not (tmp_path / "safe_plugin.py").exists()
