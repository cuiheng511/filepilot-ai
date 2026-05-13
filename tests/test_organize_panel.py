"""OrganizePanel 单元测试 — 文件夹选择、规则配置、预览执行、结果展示"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt


class TestOrganizePanelInitialState:
    """测试面板初始状态"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.organize_panel",
            FileScanner=MagicMock(),
            FileOrganizer=MagicMock(),
        ):
            from filepilot.ui.organize_panel import OrganizePanel
            self.panel = OrganizePanel()
            qtbot.addWidget(self.panel)

    def test_initial_source_none(self):
        """测试初始源文件夹为 None"""
        assert self.panel.source_dir is None

    def test_initial_target_none(self):
        """测试初始目标文件夹为 None"""
        assert self.panel.target_dir is None

    def test_initial_files_empty(self):
        """测试初始文件列表为空"""
        assert self.panel.files == []

    def test_initial_src_label(self):
        """测试初始源文件夹标签"""
        assert "未选择" in self.panel.src_path_label.text()

    def test_initial_preview_button_disabled(self):
        """测试初始预览按钮禁用"""
        assert not self.panel.btn_preview.isEnabled()

    def test_initial_execute_button_disabled(self):
        """测试初始执行按钮禁用"""
        assert not self.panel.btn_execute.isEnabled()

    def test_initial_table_empty(self):
        """测试初始结果表格为空"""
        assert self.panel.result_table.rowCount() == 0

    def test_initial_category_rule_checked(self):
        """测试初始按文件类型归类已选中"""
        assert self.panel.cb_category.isChecked()

    def test_initial_progress_hidden(self):
        """测试初始进度条隐藏"""
        assert not self.panel.progress_bar.isVisible()

    def test_rule_map_has_all_rules(self):
        """测试规则映射包含所有规则"""
        from filepilot.ui.organize_panel import OrganizePanel
        assert "category" in OrganizePanel.RULE_MAP
        assert "date" in OrganizePanel.RULE_MAP
        assert "extension" in OrganizePanel.RULE_MAP
        assert "size" in OrganizePanel.RULE_MAP


class TestOrganizePanelFolderSelection:
    """测试文件夹选择功能"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.organize_panel",
            FileScanner=MagicMock(),
            FileOrganizer=MagicMock(),
        ):
            from filepilot.ui.organize_panel import OrganizePanel
            self.panel = OrganizePanel()
            qtbot.addWidget(self.panel)

    def test_select_source_updates_label(self, tmp_path):
        """测试选择源文件夹后标签更新"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(tmp_path)):
            self.panel._on_select_source()

        assert self.panel.source_dir == tmp_path
        assert str(tmp_path) in self.panel.src_path_label.text()
        assert self.panel.btn_preview.isEnabled()

    def test_select_source_sets_default_target(self, tmp_path):
        """测试选择源文件夹后自动设置默认目标"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(tmp_path)):
            self.panel._on_select_source()

        assert self.panel.target_dir == tmp_path / "_organized"
        assert "_organized" in self.panel.dst_path_label.text()

    def test_select_source_does_not_override_existing_target(self, tmp_path):
        """测试选择源文件夹不覆盖已有的自定义目标"""
        custom_target = Path("/custom/target")
        self.panel.target_dir = custom_target
        self.panel.dst_path_label.setText(f"🎯 {custom_target}")

        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(tmp_path)):
            self.panel._on_select_source()

        assert self.panel.target_dir == custom_target  # 不应被覆盖

    def test_select_source_cancel(self):
        """测试取消选择源文件夹"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=""):
            self.panel._on_select_source()
        assert self.panel.source_dir is None

    def test_select_target_updates_label(self, tmp_path):
        """测试选择目标文件夹后标签更新"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(tmp_path)):
            self.panel._on_select_target()

        assert self.panel.target_dir == tmp_path
        assert str(tmp_path) in self.panel.dst_path_label.text()

    def test_select_target_cancel(self):
        """测试取消选择目标文件夹"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=""):
            self.panel._on_select_target()
        assert self.panel.target_dir is None


class TestOrganizePanelRules:
    """测试整理规则选择"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.organize_panel",
            FileScanner=MagicMock(),
            FileOrganizer=MagicMock(),
        ):
            from filepilot.ui.organize_panel import OrganizePanel
            self.panel = OrganizePanel()
            qtbot.addWidget(self.panel)

    def test_get_selected_rules_default(self):
        """测试默认选中分类规则"""
        from filepilot.core.file_organizer import CategoryRule
        rules = self.panel._get_selected_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], CategoryRule)

    def test_get_selected_rules_multiple(self):
        """测试多选规则"""
        self.panel.cb_date.setChecked(True)
        self.panel.cb_extension.setChecked(True)
        self.panel.cb_category.setChecked(True)

        rules = self.panel._get_selected_rules()
        assert len(rules) == 3

    def test_get_selected_rules_fallback_to_category(self):
        """测试全不选时默认使用分类规则"""
        from filepilot.core.file_organizer import CategoryRule
        self.panel.cb_category.setChecked(False)
        self.panel.cb_date.setChecked(False)
        self.panel.cb_extension.setChecked(False)
        self.panel.cb_size.setChecked(False)

        rules = self.panel._get_selected_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], CategoryRule)

    def test_category_rule_toggle(self):
        """测试分类规则勾选框开关"""
        from filepilot.core.file_organizer import CategoryRule
        self.panel.cb_category.setChecked(False)
        rules = self.panel._get_selected_rules()
        # 应该 fallback 到 CategoryRule
        assert isinstance(rules[0], CategoryRule)

    def test_template_help_shows_dialog(self):
        """测试模板帮助弹出对话框"""
        with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
            self.panel._on_template_help()
            mock_info.assert_called_once()


class TestOrganizePanelPreviewAndExecute:
    """测试预览和执行功能"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot, tmp_path):
        with patch.multiple(
            "filepilot.ui.organize_panel",
            FileScanner=MagicMock(),
            FileOrganizer=MagicMock(),
        ):
            from filepilot.ui.organize_panel import OrganizePanel
            self.panel = OrganizePanel()
            qtbot.addWidget(self.panel)
            self.panel.source_dir = tmp_path
            self.panel.target_dir = tmp_path / "_organized"
            self.panel.btn_preview.setEnabled(True)

    def test_preview_without_source(self):
        """测试未选源文件夹时预览不做操作"""
        self.panel.source_dir = None
        self.panel._on_preview()
        # 不应启动任何异步操作
        assert not self.panel.progress_bar.isVisible()

    def test_display_preview_shows_operations(self):
        """测试预览结果展示"""
        operations = [
            {"source": "a.pdf", "destination": "/organized/PDF/a.pdf",
             "category": "PDF", "size": "1 MB"},
            {"source": "b.py", "destination": "/organized/Code/b.py",
             "category": "Code", "size": "2 KB"},
        ]

        self.panel._display_preview(operations, files=[MagicMock()])

        assert self.panel.result_table.rowCount() == 2
        assert self.panel.result_table.item(0, 0).text() == "a.pdf"
        assert self.panel.result_table.item(0, 2).text() == "PDF"
        assert self.panel.btn_execute.isEnabled()
        assert "2 个文件将被整理" in self.panel.stats_label.text()

    def test_display_preview_empty_operations(self):
        """测试空预览结果"""
        self.panel._display_preview([], files=[])

        assert self.panel.result_table.rowCount() == 0
        assert not self.panel.btn_execute.isEnabled()

    def test_display_preview_sets_files(self):
        """测试预览时设置文件列表"""
        mock_files = [MagicMock(), MagicMock()]
        self.panel._display_preview([], files=mock_files)

        assert self.panel.files == mock_files

    def test_display_execution_shows_results(self):
        """测试执行结果展示"""
        operations = [
            {"source": "a.pdf", "destination": "/organized/PDF/a.pdf",
             "category": "PDF", "size": "1 MB", "dry_run": False},
        ]
        self.panel.organizer.stats = {"organized_count": 1, "errors": 0}

        self.panel._display_execution(operations)

        assert self.panel.result_table.rowCount() == 1
        assert "已移动" in self.panel.result_table.item(0, 4).text()

    def test_display_execution_with_errors(self):
        """测试执行结果展示（有错误）"""
        operations = [
            {"source": "a.pdf", "destination": "/organized/PDF/a.pdf",
             "category": "PDF", "size": "1 MB", "dry_run": False},
        ]
        self.panel.organizer.stats = {"organized_count": 1, "errors": 1}

        self.panel._display_execution(operations)

        assert "1 个错误" in self.panel.stats_label.text()


class TestOrganizePanelClear:
    """测试清空结果功能"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.organize_panel",
            FileScanner=MagicMock(),
            FileOrganizer=MagicMock(),
        ):
            from filepilot.ui.organize_panel import OrganizePanel
            self.panel = OrganizePanel()
            qtbot.addWidget(self.panel)

    def test_clear_results_empties_table(self):
        """测试清空结果表格"""
        self.panel.result_table.setRowCount(5)
        self.panel.btn_execute.setEnabled(True)

        self.panel._clear_results()

        assert self.panel.result_table.rowCount() == 0
        assert not self.panel.btn_execute.isEnabled()
        assert "就绪" in self.panel.stats_label.text()


class TestOrganizePanelMockIntegration:
    """测试完整的 Mock 集成流程"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot, tmp_path):
        with patch.multiple(
            "filepilot.ui.organize_panel",
            FileScanner=MagicMock(),
            FileOrganizer=MagicMock(),
        ):
            from filepilot.ui.organize_panel import OrganizePanel
            self.panel = OrganizePanel()
            qtbot.addWidget(self.panel)
            self.panel.source_dir = tmp_path
            self.panel.target_dir = tmp_path / "_organized"

    def test_mock_preview_flow(self, qtbot):
        """测试使用 Mock 的完整预览流程"""
        # Mock scanner and organizer
        mock_file = MagicMock()
        mock_file.name = "report.pdf"
        mock_file.path = Path("/tmp/report.pdf")
        mock_file.extension = ".pdf"
        mock_file.size_bytes = 1024
        mock_file.size_str = "1 KB"
        mock_file.modified_time = None

        self.panel.scanner.scan.return_value = [mock_file]
        self.panel.organizer.organize.return_value = [
            {"source": "report.pdf", "destination": "/organized/PDF/report.pdf",
             "category": "PDF", "size": "1 KB"},
        ]

        # Simulate display preview (skipping threading)
        self.panel._display_preview(
            self.panel.organizer.organize.return_value,
            files=[mock_file],
        )

        assert self.panel.result_table.rowCount() == 1
        assert "report.pdf" in self.panel.result_table.item(0, 0).text()

    def test_mock_execute_flow(self, qtbot):
        """测试使用 Mock 的完整执行流程"""
        mock_file = MagicMock()
        self.panel.files = [mock_file]
        self.panel.organizer.organize.return_value = [
            {"source": "report.pdf", "destination": "/organized/PDF/report.pdf",
             "category": "PDF", "size": "1 KB", "dry_run": False},
        ]
        self.panel.organizer.stats = {"organized_count": 1, "errors": 0}

        # Simulate display execution
        self.panel._display_execution(self.panel.organizer.organize.return_value)

        assert "已移动" in self.panel.result_table.item(0, 4).text()
        assert "1 个文件已移动" in self.panel.stats_label.text()


class TestOrganizePanelEdgeCases:
    """测试边界情况"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.organize_panel",
            FileScanner=MagicMock(),
            FileOrganizer=MagicMock(),
        ):
            from filepilot.ui.organize_panel import OrganizePanel
            self.panel = OrganizePanel()
            qtbot.addWidget(self.panel)

    def test_execute_with_no_source(self):
        """测试未选源文件夹时执行不做操作"""
        self.panel.source_dir = None
        self.panel._on_execute()
        # 不设置 source_dir 时 _on_execute 应直接返回
        with patch.object(self.panel, "_get_selected_rules") as mock_rules:
            self.panel._on_execute()
            mock_rules.assert_not_called()

    def test_execute_with_no_files(self):
        """测试无文件时执行不做操作"""
        self.panel.source_dir = Path("/tmp")
        self.panel.files = []
        # files 为空时 _on_execute 应直接返回
        with patch.object(self.panel, "_get_selected_rules") as mock_rules:
            self.panel._on_execute()
            mock_rules.assert_not_called()

    def test_rename_input_placeholder(self):
        """测试重命名输入框的占位文本"""
        assert "留空不重命名" in self.panel.rename_input.placeholderText()
