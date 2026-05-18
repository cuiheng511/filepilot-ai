"""TabbedFileBrowser unit tests — tab management, navigation, and services."""

from unittest.mock import MagicMock, patch

import pytest


class TestTabbedFileBrowserInitialState:
    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.tabbed_browser",
            FileScanner=MagicMock(),
            AppState=MagicMock(),
            EventBus=MagicMock(),
        ):
            from filepilot.ui.tabbed_browser import TabbedFileBrowser

            self.browser = TabbedFileBrowser()
            qtbot.addWidget(self.browser)

    def test_initial_tab_exists(self):
        assert self.browser._tabs.count() >= 1

    def test_initial_active_is_panel(self):
        from filepilot.ui.file_browser import FileBrowserPanel

        assert isinstance(self.browser._active(), FileBrowserPanel)

    def test_tab_text_is_new_tab(self):
        assert self.browser._tabs.tabText(0) == "New Tab"

    def test_files_property_empty(self):
        assert self.browser.files == []

    def test_categories_property_empty(self):
        assert self.browser.categories == {}


class TestTabbedFileBrowserTabs:
    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.tabbed_browser",
            FileScanner=MagicMock(),
            AppState=MagicMock(),
            EventBus=MagicMock(),
        ):
            from filepilot.ui.tabbed_browser import TabbedFileBrowser

            self.browser = TabbedFileBrowser()
            qtbot.addWidget(self.browser)

    def test_add_new_tab(self):
        self.browser._add_new_tab()
        assert self.browser._tabs.count() == 2
        assert self.browser._tabs.currentIndex() == 1  # new tab selected

    def test_add_new_tab_with_dir(self, tmp_path):
        panel = self.browser._add_new_tab(str(tmp_path))
        assert panel.current_dir == tmp_path
        assert tmp_path.name in self.browser._tabs.tabText(self.browser._tabs.count() - 1)

    def test_close_tab_keeps_at_least_one(self):
        # Start with 1 tab, close it — should auto-create a new one
        self.browser._close_tab(0)
        assert self.browser._tabs.count() >= 1

    def test_close_tab_middle(self):
        self.browser._add_new_tab()
        self.browser._add_new_tab()
        assert self.browser._tabs.count() == 3
        self.browser._close_tab(1)
        assert self.browser._tabs.count() == 2

    def test_tab_changed_updates_label(self, tmp_path):
        self.browser._add_new_tab(str(tmp_path))
        self.browser._close_tab(0)  # close original, triggers tab change
        assert tmp_path.name in self.browser._tabs.tabText(self.browser._tabs.currentIndex())

    def test_load_directory_active(self, tmp_path):
        self.browser.load_directory(tmp_path)
        active = self.browser._active()
        assert active is not None
        assert active.current_dir == tmp_path
        text = self.browser._tabs.tabText(self.browser._tabs.currentIndex())
        assert tmp_path.name in text

    def test_load_directory_none_active(self, tmp_path):
        """load_directory creates new tab if none active."""
        # Remove all tabs so active returns None
        self.browser._close_tab(0)
        self.browser.load_directory(str(tmp_path))
        assert self.browser._tabs.count() >= 1

    def test_scan_directory_delegates(self, tmp_path):
        with patch.object(self.browser._active(), "scan_directory") as mock_scan:
            self.browser.scan_directory(tmp_path)
            mock_scan.assert_called_once_with(tmp_path)


class TestTabbedFileBrowserServices:
    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.tabbed_browser",
            FileScanner=MagicMock(),
            AppState=MagicMock(),
            EventBus=MagicMock(),
        ):
            from filepilot.ui.tabbed_browser import TabbedFileBrowser

            self.browser = TabbedFileBrowser()
            qtbot.addWidget(self.browser)

    def test_update_services_propagates(self):
        scanner = MagicMock()
        state = MagicMock()
        bus = MagicMock()
        with patch.object(self.browser._active(), "update_services") as mock_upd:
            self.browser.update_services(scanner=scanner, app_state=state, event_bus=bus)
            mock_upd.assert_called_once_with(scanner=scanner, app_state=state, event_bus=bus)

    def test_file_opened_signal_forwarded(self, qtbot):
        """file_opened from a tab panel is forwarded via TabbedFileBrowser."""
        from filepilot.ui.file_browser import FileBrowserPanel

        panel = self.browser._active()
        assert isinstance(panel, FileBrowserPanel)
        with qtbot.assertNotEmitted(self.browser.file_opened):
            pass  # No file opened yet
        with qtbot.waitSignal(self.browser.file_opened, timeout=500):
            panel.file_opened.emit("/tmp/test.txt")
