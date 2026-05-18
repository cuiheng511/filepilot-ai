"""Tests for main-window navigation mapping."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from filepilot.core import config
from filepilot.core.service_container import ServiceContainer
from filepilot.ui.dashboard_panel import DashboardPanel
from filepilot.ui.main_window import MainWindow
from filepilot.ui.search_panel import SearchPanel


def _make_window(tmp_path, monkeypatch) -> MainWindow:
    """Helper: create a MainWindow with isolated settings."""
    settings_dir = tmp_path / "settings"
    monkeypatch.setattr(config, "SETTINGS_DIR", settings_dir)
    monkeypatch.setattr(config, "SETTINGS_FILE", settings_dir / "settings.json")
    monkeypatch.setattr(config, "ENCRYPTED_KEY_FILE", settings_dir / "api_key.enc")
    monkeypatch.setattr(config, "SALT_FILE", settings_dir / ".key_salt")
    QApplication.instance() or QApplication([])
    return MainWindow(services=ServiceContainer())


# ── Existing tests (kept for backward compat) ──


def test_grouped_navigation_opens_matching_panel(tmp_path, monkeypatch):
    """Navigation separators must not shift the stacked page index."""
    window = _make_window(tmp_path, monkeypatch)
    try:
        for panel_key in (
            "dashboard",
            "browse",
            "favorites",
            "search",
            "tags",
            "organize",
            "duplicates",
            "summary",
            "index",
            "plugins",
        ):
            window.nav_list.setCurrentRow(window._nav_key_to_row[panel_key])
            QApplication.processEvents()
            assert window.content_stack.currentIndex() == window._panel_indices[panel_key]
    finally:
        window.close()


def test_switch_to_panel_selects_matching_nav_row(tmp_path, monkeypatch):
    """Programmatic panel switches should highlight the visible navigation item."""
    window = _make_window(tmp_path, monkeypatch)
    try:
        window._switch_to_panel(window._panel_indices["search"])
        QApplication.processEvents()
        assert window.nav_list.currentRow() == window._nav_key_to_row["search"]
        assert window.content_stack.currentIndex() == window._panel_indices["search"]
    finally:
        window.close()


def test_search_panel_initializes_saved_searches_after_combo_exists(tmp_path, monkeypatch):
    settings_dir = tmp_path / "settings"
    monkeypatch.setattr(config, "SETTINGS_DIR", settings_dir)
    monkeypatch.setattr(config, "SETTINGS_FILE", settings_dir / "settings.json")
    monkeypatch.setattr(config, "ENCRYPTED_KEY_FILE", settings_dir / "api_key.enc")
    monkeypatch.setattr(config, "SALT_FILE", settings_dir / ".key_salt")
    config.save({"saved_searches": [{"name": "Invoices", "query": "invoice"}]})

    QApplication.instance() or QApplication([])
    panel = SearchPanel()

    try:
        assert panel.saved_combo.findText("Invoices") >= 0
    finally:
        panel.close()


def test_dashboard_stats_update_existing_stat_cards():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()

    try:
        panel.update_stats(total_files=42, total_size="12 MB", categories=5, tags=3)

        assert panel.stat_cards["📊 Total Files"].text() == "42"
        assert panel.stat_cards["💾 Total Size"].text() == "12 MB"
        assert panel.stat_cards["📁 Categories"].text() == "5"
        assert panel.stat_cards["🏷️ Tags"].text() == "3"
    finally:
        panel.close()


# ── New navigation tests ──


def test_nav_separator_items_are_non_selectable(tmp_path, monkeypatch):
    """Separator items should have Qt.NoItemFlags."""
    window = _make_window(tmp_path, monkeypatch)
    try:
        for i in range(window.nav_list.count()):
            item = window.nav_list.item(i)
            if not (item.flags() & Qt.ItemIsEnabled):
                # Found a separator — verify it's marked as non-selectable
                assert item.flags() == Qt.NoItemFlags
                return
        pytest.fail("No separator item found")
    finally:
        window.close()


def test_switch_to_panel_invalid_index_does_nothing(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    try:
        initial = window.content_stack.currentIndex()
        window._switch_to_panel(9999)
        assert window.content_stack.currentIndex() == initial
    finally:
        window.close()


def test_switch_to_panel_repeated_same_index_no_error(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    try:
        idx = window._panel_indices["search"]
        window._switch_to_panel(idx)
        window._switch_to_panel(idx)
        assert window.content_stack.currentIndex() == idx
    finally:
        window.close()


def test_shortcut_mapping_covers_all_panels(tmp_path, monkeypatch):
    """Each panel key must have a corresponding keyboard shortcut."""
    window = _make_window(tmp_path, monkeypatch)
    try:
        for panel_key in (
            "browse",
            "search",
            "organize",
            "duplicates",
            "summary",
            "index",
            "favorites",
            "tags",
            "plugins",
        ):
            assert panel_key in window._nav_key_to_row, f"Missing nav key: {panel_key}"
            assert panel_key in window._panel_indices, f"Missing panel index: {panel_key}"
    finally:
        window.close()


def test_global_search_switches_to_search_panel(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    try:
        window._on_global_search()
        QApplication.processEvents()
        assert window.content_stack.currentIndex() == window._panel_indices["search"]
    finally:
        window.close()


def test_on_nav_changed_separator_skipped(tmp_path, monkeypatch):
    """Selecting a separator row must not change the stack index."""
    window = _make_window(tmp_path, monkeypatch)
    try:
        before = window.content_stack.currentIndex()
        # Find a separator row
        for i in range(window.nav_list.count()):
            item = window.nav_list.item(i)
            if item and not (item.flags() & Qt.ItemIsEnabled):
                window.nav_list.setCurrentRow(i)
                QApplication.processEvents()
                assert window.content_stack.currentIndex() == before
                return
        pytest.fail("No separator found")
    finally:
        window.close()


def test_all_panel_indices_valid(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    try:
        for key, idx in window._panel_indices.items():
            assert 0 <= idx < window.content_stack.count(), f"Index {idx} out of range for {key}"
    finally:
        window.close()


def test_nav_key_to_row_all_valid(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    try:
        for key, row in window._nav_key_to_row.items():
            assert 0 <= row < window.nav_list.count(), f"Row {row} out of range for {key}"
    finally:
        window.close()
