"""Tests for DashboardPanel."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QListWidgetItem

from filepilot.core.event_bus import EventBus
from filepilot.i18n import t
from filepilot.ui.dashboard_panel import DashboardPanel


def test_update_stats_updates_all_four_cards():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.update_stats(total_files=42, total_size="12 MB", categories=5, tags=3)
        assert panel.stat_cards["📊 Total Files"].text() == "42"
        assert panel.stat_cards[t("disk_total")].text() == "12 MB"
        assert panel.stat_cards["📁 Categories"].text() == "5"
        assert panel.stat_cards["🏷️ Tags"].text() == "3"
    finally:
        panel.close()


def test_update_stats_formats_thousands():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.update_stats(total_files=12345)
        assert panel.stat_cards["📊 Total Files"].text() == "12,345"
    finally:
        panel.close()


def test_update_recent_folders_populates_list():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.update_recent_folders([r"C:\Users\test\Docs", r"C:\Users\test\Photos"])
        assert panel.recent_folders_list.count() == 2
        assert panel.recent_folders_list.item(0).toolTip() == r"C:\Users\test\Docs"
    finally:
        panel.close()


def test_update_recent_folders_truncates_to_ten():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        folders = [f"C:\\folder_{i}" for i in range(15)]
        panel.update_recent_folders(folders)
        assert panel.recent_folders_list.count() == 10
    finally:
        panel.close()


def test_update_recent_folders_empty_shows_placeholder():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.update_recent_folders([])
        assert panel.recent_folders_list.count() == 1
        assert "No recent folders" in panel.recent_folders_list.item(0).text()
    finally:
        panel.close()


def test_update_recent_files_populates_list():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.update_recent_files([r"C:\Users\test\readme.md", r"C:\Users\test\notes.txt"])
        assert panel.recent_files_list.count() == 2
    finally:
        panel.close()


def test_update_recent_files_empty_shows_placeholder():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.update_recent_files([])
        assert panel.recent_files_list.count() == 1
        assert "No recent files" in panel.recent_files_list.item(0).text()
    finally:
        panel.close()


def test_update_recent_files_truncates_to_ten():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        files = [f"C:\\file_{i}.txt" for i in range(15)]
        panel.update_recent_files(files)
        assert panel.recent_files_list.count() == 10
    finally:
        panel.close()


def test_double_click_folder_emits_signal():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        signals = []
        panel.open_folder.connect(lambda p: signals.append(p))
        panel.update_recent_folders([r"C:\test"])
        item = panel.recent_folders_list.item(0)
        panel._on_folder_double_click(item)
        assert signals == [r"C:\test"]
    finally:
        panel.close()


def test_double_click_folder_emits_event_bus():
    QApplication.instance() or QApplication([])
    bus = EventBus()
    panel = DashboardPanel(event_bus=bus)
    try:
        signals = []
        bus.open_folder_requested.connect(lambda p: signals.append(p))
        panel.update_recent_folders([r"C:\test"])
        panel._on_folder_double_click(panel.recent_folders_list.item(0))
        assert signals == [r"C:\test"]
    finally:
        panel.close()


def test_double_click_file_emits_signal():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        signals = []
        panel.open_file.connect(lambda p: signals.append(p))
        panel.update_recent_files([r"C:\test\readme.md"])
        panel._on_file_double_click(panel.recent_files_list.item(0))
        assert signals == [r"C:\test\readme.md"]
    finally:
        panel.close()


def test_double_click_file_emits_event_bus():
    QApplication.instance() or QApplication([])
    bus = EventBus()
    panel = DashboardPanel(event_bus=bus)
    try:
        signals = []
        bus.open_file_requested.connect(lambda p: signals.append(p))
        panel.update_recent_files([r"C:\test\readme.md"])
        panel._on_file_double_click(panel.recent_files_list.item(0))
        assert signals == [r"C:\test\readme.md"]
    finally:
        panel.close()


def test_double_click_empty_item_does_nothing():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        signals = []
        panel.open_folder.connect(lambda p: signals.append(p))
        item = QListWidgetItem()
        panel._on_folder_double_click(item)
        assert signals == []
    finally:
        panel.close()


def test_create_section_returns_frame_with_title():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        section = panel._create_section("Test Section")
        assert section is not None
    finally:
        panel.close()


def test_quick_action_buttons_exist():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        assert panel.btn_open_folder.text() == "📂 Open Folder"
        assert panel.btn_scan.text() == t("browse_scan")
        assert panel.btn_index.text() == "📇 Build Index"
        assert panel.btn_find_duplicates.text() == "🔍 Find Duplicates"
    finally:
        panel.close()


def test_set_current_dir_noop():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.set_current_dir("/some/path")
    finally:
        panel.close()


def test_recent_files_shows_modified_time():
    QApplication.instance() or QApplication([])
    panel = DashboardPanel()
    try:
        panel.update_recent_files([__file__])
        assert panel.recent_files_list.count() == 1
        tip = panel.recent_files_list.item(0).toolTip()
        assert "Modified:" in tip
    finally:
        panel.close()
