"""IndexPanel 单元测试 — 索引管理、文件夹选择、统计展示、文件列表"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt


class TestIndexPanelInitialState:
    """测试面板初始状态"""

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
        """测试初始源文件夹为 None"""
        assert self.panel.source_dir is None

    def test_initial_indexing_false(self):
        """测试初始索引状态为 False"""
        assert not self.panel._indexing

    def test_initial_dir_label(self):
        """测试初始文件夹标签"""
        assert "未选择" in self.panel.dir_label.text()

    def test_initial_build_button_disabled(self):
        """测试初始建立索引按钮禁用"""
        assert not self.panel.btn_build.isEnabled()

    def test_initial_update_button_disabled(self):
        """测试初始增量更新按钮禁用"""
        assert not self.panel.btn_update.isEnabled()

    def test_initial_clear_button_disabled(self):
        """测试初始清空索引按钮禁用"""
        assert not self.panel.btn_clear.isEnabled()

    def test_initial_refresh_button_enabled(self):
        """测试初始刷新统计按钮启用"""
        assert self.panel.btn_refresh.isEnabled()

    def test_initial_progress_hidden(self):
        """测试初始进度条隐藏"""
        assert not self.panel.progress_bar.isVisible()
        assert not self.panel.progress_label.isVisible()

    def test_initial_stats_placeholder(self):
        """测试初始统计信息为占位符"""
        from PySide6.QtWidgets import QLabel
        value = self.panel.stat_indexed.findChild(QLabel, "statValue")
        assert value is not None

    def test_initial_table_empty(self):
        """测试初始文件表格为空"""
        assert self.panel.file_table.rowCount() == 0

    def test_initial_stats_label(self):
        """测试初始状态标签"""
        assert "就绪" in self.panel.stats_label.text()


class TestIndexPanelFolderSelection:
    """测试文件夹选择功能"""

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
        """测试选择源文件夹后标签更新"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(tmp_path)):
            self.panel._on_select_source()

        assert self.panel.source_dir == tmp_path
        assert str(tmp_path) in self.panel.dir_label.text()
        assert self.panel.btn_build.isEnabled()
        assert self.panel.btn_update.isEnabled()

    def test_select_source_cancel(self):
        """测试取消选择源文件夹"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=""):
            self.panel._on_select_source()

        assert self.panel.source_dir is None


class TestIndexPanelStats:
    """测试数据统计功能"""

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
        """测试成功刷新统计"""
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
        """测试刷新统计（无文件）"""
        self.panel.indexer.get_stats.side_effect = Exception("no index")

        self.panel._refresh_stats()

        assert not self.panel.btn_clear.isEnabled()

    def test_refresh_stats_calls_get_all_indexed(self):
        """测试刷新统计时调用 get_all_indexed"""
        self.panel.indexer.get_stats.return_value = {
            "indexed_files": 5, "index_size": "10 KB", "index_dir": "/tmp/index",
        }
        self.panel.indexer.get_all_indexed.return_value = []

        self.panel._refresh_stats()

        self.panel.indexer.get_all_indexed.assert_called_once_with(limit=2000)

    def test_update_stat_finds_correct_card(self):
        """测试 _update_stat 找到并更新正确的统计卡片"""
        from PySide6.QtWidgets import QLabel
        self.panel._update_stat("📄 已索引文件", "99")

        stat_value = self.panel.stat_indexed.findChild(QLabel, "statValue")
        assert stat_value.text() == "99"


class TestIndexPanelBuildAndUpdate:
    """测试建立索引和增量更新"""

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
        """测试未选源文件夹时点击建立索引不执行"""
        self.panel.source_dir = None
        self.panel._on_build()
        assert not self.panel._indexing

    def test_build_shows_confirmation(self):
        """测试建立索引确认对话框的返回值"""
        from PySide6.QtWidgets import QMessageBox
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            with patch.object(self.panel, "_start_indexing") as mock_start:
                self.panel._on_build()
                mock_start.assert_called_once()

    def test_build_with_indexing_in_progress(self):
        """测试索引进行中时再次点击不执行"""
        self.panel._indexing = True
        with patch.object(self.panel, "_start_indexing") as mock_start:
            self.panel._on_build()
            mock_start.assert_not_called()

    def test_indexing_finished_updates_state(self):
        """测试索引完成后状态更新"""
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
        assert "10 个文件已索引" in self.panel.stats_label.text()

    def test_indexing_error_updates_state(self):
        """测试索引错误后状态更新"""
        self.panel._indexing = True
        self.panel.source_dir = Path("/tmp")

        self.panel._on_indexing_error("磁盘空间不足")

        assert not self.panel._indexing
        assert not self.panel.progress_bar.isVisible()
        assert "磁盘空间不足" in self.panel.stats_label.text()


class TestIndexPanelClear:
    """测试清空索引功能"""

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
        """测试成功清空索引"""
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
        """测试清空索引出错处理"""
        from PySide6.QtWidgets import QMessageBox
        self.panel.indexer.clear_index.side_effect = Exception("权限不足")

        with patch.object(QMessageBox, "warning", return_value=QMessageBox.Yes):
            self.panel._on_clear()

        assert "权限不足" in self.panel.stats_label.text()


class TestIndexPanelContextMenu:
    """测试表格右键菜单和文件移除"""

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
        """测试从索引中移除选中文件"""
        # Mock selection model
        mock_selection = MagicMock()
        mock_selection.selectedRows.return_value = [
            type("Index", (), {"row": lambda: 0})(),
        ]
        self.panel.file_table.selectionModel = MagicMock(return_value=mock_selection)

        self.panel._remove_selected_from_index()

        self.panel.indexer.remove_from_index.assert_called_once_with("/tmp/a.md")
        self.panel.indexer.get_stats.assert_called_once()
        assert "已从索引中移除 1 个文件" in self.panel.stats_label.text()

    def test_remove_with_no_selection(self):
        """测试无选中文件时不移除"""
        mock_selection = MagicMock()
        mock_selection.selectedRows.return_value = []
        self.panel.file_table.selectionModel = MagicMock(return_value=mock_selection)

        self.panel._remove_selected_from_index()

        self.panel.indexer.remove_from_index.assert_not_called()


class TestIndexPanelMockIntegration:
    """测试完整的 Mock 集成流程"""

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
        """测试 index_directory 快捷方法"""
        mock_build = MagicMock()
        self.panel._on_build = mock_build

        self.panel.index_directory(tmp_path)

        assert self.panel.source_dir == tmp_path
        assert str(tmp_path) in self.panel.dir_label.text()
        assert self.panel.btn_build.isEnabled()
        assert self.panel.btn_update.isEnabled()
        mock_build.assert_called_once()

    def test_mock_indexing_flow(self, qtbot, tmp_path):
        """测试使用 Mock 的完整索引流程"""
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
        assert "1 个文件已索引" in self.panel.stats_label.text()


class TestIndexPanelEdgeCases:
    """测试边界情况"""

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
        """测试未选源文件夹时增量更新不做操作"""
        self.panel.source_dir = None
        self.panel._on_update()
        assert not self.panel._indexing

    def test_build_without_source_returns(self):
        """测试未选源文件夹时建立索引返回"""
        self.panel.source_dir = None
        self.panel._on_build()
        assert not self.panel._indexing

    def test_multiple_quick_clicks_ignored(self):
        """测试索引进行中时忽略多次点击"""
        self.panel._indexing = True
        with patch.object(self.panel, "_start_indexing") as mock:
            self.panel._on_build()
            self.panel._on_update()
            mock.assert_not_called()

    def test_update_stat_nonexistent_title(self):
        """测试更新不存在的统计卡片不做任何事"""
        # Should not raise any error
        self.panel._update_stat("不存在的卡片", "123")

    def test_load_indexed_files_empty(self):
        """测试加载空索引列表"""
        self.panel.indexer.get_all_indexed.return_value = []
        self.panel._load_indexed_files()
        assert self.panel.file_table.rowCount() == 0

    def test_load_indexed_files_with_data(self):
        """测试加载有数据的索引列表"""
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
