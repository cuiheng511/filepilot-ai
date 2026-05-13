"""IndexPanel unit tests — index management, folder selection, statistics display, file list"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt


class TestIndexPanelInitialState:
    """Test panel initial state"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)

    def test_initial_source_dir_none(self):
        """Test initial source directory is None"""
        assert self.panel.source_dir is None

    def test_initial_indexing_false(self):
        """Test initial indexing state is False"""
        assert not self.panel._indexing

    def test_initial_dir_label(self):
        """Test initial directory label"""
        assert "Not selected" in self.panel.dir_label.text()

    def test_initial_build_button_disabled(self):
        """Test initial build index button is disabled"""
        assert not self.panel.btn_build.isEnabled()

    def test_initial_update_button_disabled(self):
        """Test initial incremental update button is disabled"""
        assert not self.panel.btn_update.isEnabled()

    def test_initial_clear_button_disabled(self):
        """Test initial clear index button is disabled"""
        assert not self.panel.btn_clear.isEnabled()

    def test_initial_refresh_button_enabled(self):
        """Test initial refresh stats button is enabled"""
        assert self.panel.btn_refresh.isEnabled()

    def test_initial_progress_hidden(self):
        """Test initial progress bar is hidden"""
        assert not self.panel.progress_bar.isVisible()
        assert not self.panel.progress_label.isVisible()

    def test_initial_stats_placeholder(self):
        """Test initial stats show placeholder"""
        from PySide6.QtWidgets import QLabel
        value = self.panel.stat_indexed.findChild(QLabel, "statValue")
        assert value is not None

    def test_initial_table_empty(self):
        """Test initial file table is empty"""
        assert self.panel.file_table.rowCount() == 0

    def test_initial_stats_label(self):
        """Test initial status label"""
        assert "Ready" in self.panel.stats_label.text()


class TestIndexPanelFolderSelection:
    """Test folder selection functionality"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)

    def test_select_source_updates_label(self, tmp_path):
        """Test selecting source folder updates the label"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(tmp_path)):
            self.panel._on_select_source()

        assert self.panel.source_dir == tmp_path
        assert str(tmp_path) in self.panel.dir_label.text()
        assert self.panel.btn_build.isEnabled()
        assert self.panel.btn_update.isEnabled()

    def test_select_source_cancel(self):
        """Test canceling source folder selection"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=""):
            self.panel._on_select_source()

        assert self.panel.source_dir is None


class TestIndexPanelStats:
    """Test statistics functionality"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)

    def test_refresh_stats_success(self):
        """Test successful stats refresh"""
        self.panel.indexer.get_stats.return_value = {
            "indexed_files": 42,
            "index_size": "128 KB",
            "index_dir": "/tmp/index",
        }
        self.panel.indexer.get_all_indexed.return_value = [
            {"filename": "test.md", "path": "/tmp/test.md",
             "category": "Markdown", "size_str": "1 KB", "modified": "2024-01-15"},
        ]

        self.panel._refresh_stats()

        from PySide6.QtWidgets import QLabel
        # Verify stats cards updated
        stat_value = self.panel.stat_indexed.findChild(QLabel, "statValue")
        assert stat_value.text() == "42"

        stat_size = self.panel.stat_size.findChild(QLabel, "statValue")
        assert stat_size.text() == "128 KB"

        # Verify clear button enabled
        assert self.panel.btn_clear.isEnabled()

    def test_refresh_stats_no_files(self):
        """Test refreshing stats with no files"""
        self.panel.indexer.get_stats.side_effect = Exception("no index")

        self.panel._refresh_stats()

        assert not self.panel.btn_clear.isEnabled()

    def test_refresh_stats_calls_get_all_indexed(self):
        """Test refresh stats calls get_all_indexed"""
        self.panel.indexer.get_stats.return_value = {
            "indexed_files": 5, "index_size": "10 KB", "index_dir": "/tmp/index",
        }
        self.panel.indexer.get_all_indexed.return_value = []

        self.panel._refresh_stats()

        self.panel.indexer.get_all_indexed.assert_called_once_with(limit=2000)

    def test_update_stat_finds_correct_card(self):
        """Test _update_stat finds and updates the correct stat card"""
        from PySide6.QtWidgets import QLabel
        self.panel._update_stat("📄 Indexed Files", "99")

        stat_value = self.panel.stat_indexed.findChild(QLabel, "statValue")
        assert stat_value.text() == "99"


class TestIndexPanelBuildAndUpdate:
    """Test building and incremental update of index"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot, tmp_path):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)
            self.panel.source_dir = tmp_path
            self.panel.btn_build.setEnabled(True)

    def test_build_without_source_does_nothing(self):
        """Test clicking build without source does nothing"""
        self.panel.source_dir = None
        self.panel._on_build()
        assert not self.panel._indexing

    def test_build_shows_confirmation(self):
        """Test build shows confirmation dialog"""
        from PySide6.QtWidgets import QMessageBox
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            with patch.object(self.panel, "_start_indexing") as mock_start:
                self.panel._on_build()
                mock_start.assert_called_once()

    def test_build_with_indexing_in_progress(self):
        """Test clicking build during indexing does nothing"""
        self.panel._indexing = True
        with patch.object(self.panel, "_start_indexing") as mock_start:
            self.panel._on_build()
            mock_start.assert_not_called()

    def test_indexing_finished_updates_state(self):
        """Test state update after indexing completes"""
        self.panel._indexing = True
        self.panel.source_dir = Path("/tmp")
        self.panel.indexer.get_stats.return_value = {
            "indexed_files": 10, "index_size": "256 KB", "index_dir": "/tmp/index",
        }
        self.panel.indexer.get_all_indexed.return_value = []

        self.panel._on_indexing_finished()

        assert not self.panel._indexing
        assert not self.panel.progress_bar.isVisible()
        assert self.panel.btn_build.isEnabled()
        assert self.panel.btn_update.isEnabled()
        assert self.panel.btn_refresh.isEnabled()
        assert "10 files indexed" in self.panel.stats_label.text()

    def test_indexing_error_updates_state(self):
        """Test state update after indexing error"""
        self.panel._indexing = True
        self.panel.source_dir = Path("/tmp")

        self.panel._on_indexing_error("Insufficient disk space")

        assert not self.panel._indexing
        assert not self.panel.progress_bar.isVisible()
        assert "Insufficient disk space" in self.panel.stats_label.text()


class TestIndexPanelClear:
    """Test clear index functionality"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)

    def test_clear_index_success(self):
        """Test successful index clearing"""
        from PySide6.QtWidgets import QMessageBox
        self.panel.indexer.clear_index = MagicMock()
        self.panel.indexer.get_stats.return_value = {
            "indexed_files": 0, "index_size": "0 B", "index_dir": "/tmp/index",
        }

        with patch.object(QMessageBox, "warning", return_value=QMessageBox.Yes):
            with patch.object(self.panel, "_refresh_stats") as mock_refresh:
                self.panel._on_clear()
                self.panel.indexer.clear_index.assert_called_once()
                mock_refresh.assert_called_once()

    def test_clear_index_error_handling(self):
        """Test error handling when clearing index"""
        from PySide6.QtWidgets import QMessageBox
        self.panel.indexer.clear_index.side_effect = Exception("Permission denied")

        with patch.object(QMessageBox, "warning", return_value=QMessageBox.Yes):
            self.panel._on_clear()

        assert "Permission denied" in self.panel.stats_label.text()


class TestIndexPanelContextMenu:
    """Test table context menu and file removal"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)
            # Populate table with some data
            self.panel.file_table.setRowCount(2)
            self.panel.file_table.setItem(0, 0, type("Item", (), {"text": lambda: "a.md"})())
            self.panel.file_table.setItem(0, 1, type("Item", (), {"text": lambda: "/tmp/a.md"})())
            self.panel.file_table.setItem(1, 0, type("Item", (), {"text": lambda: "b.md"})())
            self.panel.file_table.setItem(1, 1, type("Item", (), {"text": lambda: "/tmp/b.md"})())

    def test_remove_selected_from_index(self):
        """Test removing selected files from index"""
        # Mock selection model
        mock_selection = MagicMock()
        mock_selection.selectedRows.return_value = [
            type("Index", (), {"row": lambda: 0})(),
        ]
        self.panel.file_table.selectionModel = MagicMock(return_value=mock_selection)

        self.panel._remove_selected_from_index()

        self.panel.indexer.remove_from_index.assert_called_once_with("/tmp/a.md")
        self.panel.indexer.get_stats.assert_called_once()
        assert "1 file removed from index" in self.panel.stats_label.text()

    def test_remove_with_no_selection(self):
        """Test removing with no selection does nothing"""
        mock_selection = MagicMock()
        mock_selection.selectedRows.return_value = []
        self.panel.file_table.selectionModel = MagicMock(return_value=mock_selection)

        self.panel._remove_selected_from_index()

        self.panel.indexer.remove_from_index.assert_not_called()


class TestIndexPanelMockIntegration:
    """Test complete Mock integration flow"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)

    def test_index_directory_shortcut(self, tmp_path):
        """Test index_directory shortcut method"""
        mock_build = MagicMock()
        self.panel._on_build = mock_build

        self.panel.index_directory(tmp_path)

        assert self.panel.source_dir == tmp_path
        assert str(tmp_path) in self.panel.dir_label.text()
        assert self.panel.btn_build.isEnabled()
        assert self.panel.btn_update.isEnabled()
        mock_build.assert_called_once()

    def test_mock_indexing_flow(self, qtbot, tmp_path):
        """Test complete indexing flow with Mock"""
        # Setup source directory
        self.panel.source_dir = tmp_path
        self.panel.btn_build.setEnabled(True)

        # Mock scanner to return files
        mock_file = MagicMock()
        mock_file.name = "test.md"
        mock_file.path = tmp_path / "test.md"
        mock_file.extension = ".md"
        mock_file.category = type("Cat", (), {"label": "Markdown"})()
        mock_file.size_bytes = 100
        mock_file.size_str = "100 B"
        mock_file.is_directory = False
        mock_file.modified_time = None
        mock_file.created_time = None

        self.panel.scanner.scan.return_value = [mock_file]
        self.panel.indexer.index_files.return_value = 1
        self.panel.indexer.get_stats.return_value = {
            "indexed_files": 1, "index_size": "10 KB", "index_dir": str(tmp_path),
        }

        # Simulate indexing finished
        self.panel._on_indexing_finished()

        assert self.panel.indexer.get_stats.called
        assert "1 files indexed" in self.panel.stats_label.text()


class TestIndexPanelEdgeCases:
    """Test edge cases"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.index_panel",
            FileScanner=MagicMock(),
            FileIndexer=MagicMock(),
        ):
            from filepilot.ui.index_panel import IndexPanel
            self.panel = IndexPanel()
            qtbot.addWidget(self.panel)

    def test_update_without_source(self):
        """Test clicking update without source does nothing"""
        self.panel.source_dir = None
        self.panel._on_update()
        assert not self.panel._indexing

    def test_build_without_source_returns(self):
        """Test clicking build without source returns"""
        self.panel.source_dir = None
        self.panel._on_build()
        assert not self.panel._indexing

    def test_multiple_quick_clicks_ignored(self):
        """Test multiple quick clicks are ignored during indexing"""
        self.panel._indexing = True
        with patch.object(self.panel, "_start_indexing") as mock:
            self.panel._on_build()
            self.panel._on_update()
            mock.assert_not_called()

    def test_update_stat_nonexistent_title(self):
        """Test updating non-existent stat card does nothing"""
        # Should not raise any error
        self.panel._update_stat("Non-existent card", "123")

    def test_load_indexed_files_empty(self):
        """Test loading empty index list"""
        self.panel.indexer.get_all_indexed.return_value = []
        self.panel._load_indexed_files()
        assert self.panel.file_table.rowCount() == 0

    def test_load_indexed_files_with_data(self):
        """Test loading index list with data"""
        self.panel.indexer.get_all_indexed.return_value = [
            {"filename": "a.py", "path": "/tmp/a.py", "category": "Code",
             "size_str": "1 KB", "modified": "2024-01-15"},
            {"filename": "b.md", "path": "/tmp/b.md", "category": "Markdown",
             "size_str": "2 KB", "modified": "2024-01-16"},
        ]

        self.panel._load_indexed_files()

        assert self.panel.file_table.rowCount() == 2
        assert self.panel.file_table.item(0, 0).text() == "a.py"
        assert self.panel.file_table.item(1, 0).text() == "b.md"
