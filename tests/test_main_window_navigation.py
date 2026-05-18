"""Tests for main-window navigation mapping."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from filepilot.core import config
from filepilot.core.service_container import ServiceContainer
from filepilot.ui.dashboard_panel import DashboardPanel
from filepilot.ui.main_window import MainWindow
from filepilot.ui.search_panel import SearchPanel


def test_grouped_navigation_opens_matching_panel(tmp_path, monkeypatch):
    """Navigation separators must not shift the stacked page index."""
    settings_dir = tmp_path / "settings"
    monkeypatch.setattr(config, "SETTINGS_DIR", settings_dir)
    monkeypatch.setattr(config, "SETTINGS_FILE", settings_dir / "settings.json")
    monkeypatch.setattr(config, "ENCRYPTED_KEY_FILE", settings_dir / "api_key.enc")
    monkeypatch.setattr(config, "SALT_FILE", settings_dir / ".key_salt")

    app = QApplication.instance() or QApplication([])
    window = MainWindow(services=ServiceContainer())

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
            app.processEvents()
            assert window.content_stack.currentIndex() == window._panel_indices[panel_key]
    finally:
        window.close()


def test_switch_to_panel_selects_matching_nav_row(tmp_path, monkeypatch):
    """Programmatic panel switches should highlight the visible navigation item."""
    settings_dir = tmp_path / "settings"
    monkeypatch.setattr(config, "SETTINGS_DIR", settings_dir)
    monkeypatch.setattr(config, "SETTINGS_FILE", settings_dir / "settings.json")
    monkeypatch.setattr(config, "ENCRYPTED_KEY_FILE", settings_dir / "api_key.enc")
    monkeypatch.setattr(config, "SALT_FILE", settings_dir / ".key_salt")

    app = QApplication.instance() or QApplication([])
    window = MainWindow(services=ServiceContainer())

    try:
        window._switch_to_panel(window._panel_indices["search"])
        app.processEvents()
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
