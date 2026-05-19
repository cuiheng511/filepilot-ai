"""Tests for PluginManagerPanel — plugin management panel."""

from unittest.mock import MagicMock, patch

import pytest

from filepilot.ui.plugin_manager_panel import PluginManagerPanel


class MockExtractor:
    def __init__(self, name, display_name, version="1.0.0", description="Test", extensions=None):
        self.name = name
        self.display_name = display_name
        self.version = version
        self.description = description
        if extensions:
            self.extensions = extensions

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, v):
        self._name = v

    @property
    def display_name(self):
        return self._display_name

    @display_name.setter
    def display_name(self, v):
        self._display_name = v

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, v):
        self._version = v

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, v):
        self._description = v


@pytest.fixture
def mock_plugin_manager():
    pm = MagicMock()
    pm.plugins_dir = "/tmp/plugins"
    pm.get_all_extractors.return_value = []
    return pm


@pytest.fixture
def panel(qtbot, mock_plugin_manager):
    with patch("filepilot.ui.plugin_manager_panel.PluginManager", return_value=mock_plugin_manager):
        p = PluginManagerPanel()
        qtbot.addWidget(p)
        return p


class TestPluginManagerPanel:
    def test_constructor(self, panel):
        assert panel.plugin_manager is not None
        assert panel.plugin_list is not None
        assert panel.stats_label is not None
        assert panel.btn_discover is not None
        assert panel.btn_install_sample is not None
        assert panel.btn_open_dir is not None

    def test_refresh_plugins_empty(self, panel):
        panel._refresh_plugins()
        assert panel.plugin_list.count() == 0
        assert "0" in panel.stats_label.text()

    def test_refresh_plugins_with_extractors(self, panel, mock_plugin_manager):
        ext = MagicMock()
        ext.name = "PDFExtractor"
        ext.display_name = "PDF Extractor"
        ext.version = "1.0.0"
        ext.description = "Extracts text from PDF files"
        ext.extensions = [".pdf"]
        mock_plugin_manager.get_all_extractors.return_value = [ext]

        panel._refresh_plugins()
        assert panel.plugin_list.count() == 1
        item = panel.plugin_list.item(0)
        assert "PDF Extractor" in item.text()
        assert "1.0.0" in item.toolTip()

    def test_on_discover(self, panel, mock_plugin_manager):
        ext = MagicMock()
        ext.name = "TestExtractor"
        ext.display_name = "Test Extractor"
        ext.version = "0.1.0"
        ext.description = "Test"
        mock_plugin_manager.get_all_extractors.return_value = [ext]

        panel._on_discover()
        mock_plugin_manager.reload.assert_called_once()
        assert panel.plugin_list.count() == 1

    def test_on_install_sample(self, panel, mock_plugin_manager):
        mock_path = MagicMock()
        mock_path.name = "sample_extractor.py"
        mock_plugin_manager.install_sample_plugin.return_value = mock_path
        ext = MagicMock()
        ext.name = "SampleExtractor"
        ext.display_name = "Sample Extractor"
        ext.version = "0.1.0"
        ext.description = "Sample"
        mock_plugin_manager.get_all_extractors.return_value = [ext]

        with patch(
            "filepilot.core.plugin_system.PluginManager.install_sample_plugin",
            return_value=mock_path,
        ):
            panel._on_install_sample()
            assert panel.plugin_list.count() == 1

    def test_on_open_dir_windows(self, panel, mock_plugin_manager):
        mock_plugin_manager.plugins_dir = MagicMock()
        with patch("sys.platform", "win32"), patch("subprocess.Popen") as mock_popen:
            panel._on_open_dir()
            mock_plugin_manager.plugins_dir.mkdir.assert_called_once_with(
                parents=True, exist_ok=True
            )
            mock_popen.assert_called_once()

    def test_on_open_dir_macos(self, panel, mock_plugin_manager):
        mock_plugin_manager.plugins_dir = MagicMock()
        with patch("sys.platform", "darwin"), patch("subprocess.Popen") as mock_popen:
            panel._on_open_dir()
            mock_popen.assert_called_once()

    def test_on_open_dir_linux(self, panel, mock_plugin_manager):
        mock_plugin_manager.plugins_dir = MagicMock()
        with patch("sys.platform", "linux"), patch("subprocess.Popen") as mock_popen:
            panel._on_open_dir()
            mock_popen.assert_called_once()

    def test_on_open_dir_error_handled(self, panel, mock_plugin_manager):
        mock_plugin_manager.plugins_dir = MagicMock()
        mock_plugin_manager.plugins_dir.mkdir.side_effect = PermissionError("denied")
        panel._on_open_dir()
        assert True

    def test_status_message_updates_label(self, panel):
        panel.status_message.emit("Test message")
        assert panel.stats_label.text() == "Test message"
