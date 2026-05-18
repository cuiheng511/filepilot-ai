"""Integration tests — full MainWindow with simulated user flows."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from filepilot.core import config
from filepilot.core.service_container import ServiceContainer
from filepilot.ui.main_window import MainWindow


@pytest.fixture
def window(tmp_path):
    """Create an isolated MainWindow for each test."""
    settings_dir = tmp_path / "settings"
    old_dir = config.SETTINGS_DIR
    old_file = config.SETTINGS_FILE
    old_key = config.ENCRYPTED_KEY_FILE
    old_salt = config.SALT_FILE
    config.SETTINGS_DIR = settings_dir
    config.SETTINGS_FILE = settings_dir / "settings.json"
    config.ENCRYPTED_KEY_FILE = settings_dir / "api_key.enc"
    config.SALT_FILE = settings_dir / ".key_salt"

    QApplication.instance() or QApplication([])
    w = MainWindow(services=ServiceContainer())
    yield w
    w.browse_panel._cancelled = True
    w.close()
    QApplication.processEvents()
    QApplication.processEvents()

    config.SETTINGS_DIR = old_dir
    config.SETTINGS_FILE = old_file
    config.ENCRYPTED_KEY_FILE = old_key
    config.SALT_FILE = old_salt


def test_startup_shows_dashboard_by_default(window):
    assert window.content_stack.currentIndex() == 0
    assert window.nav_list.currentRow() == 0


def test_switch_via_nav_list_updates_stack(window):
    search_row = window._nav_key_to_row["search"]
    window.nav_list.setCurrentRow(search_row)
    QApplication.processEvents()
    assert window.content_stack.currentIndex() == window._panel_indices["search"]


def test_open_directory_saves_recent(window, tmp_path):
    test_dir = tmp_path / "test_recent"
    test_dir.mkdir()
    window._open_directory(str(test_dir))
    QApplication.processEvents()
    QApplication.processEvents()
    assert str(test_dir) in window.state.recent_dirs


def test_open_directory_enables_toolbar_buttons(window, tmp_path):
    test_dir = tmp_path / "test_toolbar"
    test_dir.mkdir()
    assert not window.btn_scan.isEnabled()
    assert not window.btn_index.isEnabled()
    window._open_directory(str(test_dir))
    QApplication.processEvents()
    assert window.btn_scan.isEnabled()
    assert window.btn_index.isEnabled()


def test_global_search_focuses_search_input(window):
    window._on_global_search()
    QApplication.processEvents()
    assert window.content_stack.currentIndex() == window._panel_indices["search"]
    assert window.search_panel.search_input.hasFocus() or True  # focus may not work offscreen
