"""OrganizePanel unit tests — folder selection, rule configuration, preview, execution, results display"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox


class TestOrganizePanelInitialState:
    """Test panel initial state"""

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
        """Test initial source folder is None"""
        assert self.panel.source_dir is None

    def test_initial_target_none(self):
        """Test initial target folder is None"""
        assert self.panel.target_dir is None

    def test_initial_files_empty(self):
        """Test initial file list is empty"""
        assert self.panel.files == []

    def test_initial_src_label(self):
        """Test initial source folder label"""
        assert "Not selected" in self.panel.src_path_label.text()

    def test_initial_preview_button_disabled(self):
        """Test initial preview button is disabled"""
        assert not self.panel.btn_preview.isEnabled()

    def test_initial_execute_button_disabled(self):
        """Test initial execute button is disabled"""
        assert not self.panel.btn_execute.isEnabled()

    def test_initial_table_empty(self):
        """Test initial result table is empty"""
        assert self.panel.result_table.rowCount() == 0

    def test_initial_category_rule_checked(self):
        """Test initial category rule is checked"""
        assert self.panel.cb_category.isChecked()

    def test_review_unknown_enabled_by_default(self):
        """Unknown files are routed to Review by default in desktop organize."""
        assert self.panel.cb_review_unknown.isChecked()

    def test_initial_pipeline_stage(self):
        """Workflow starts at the selection stage."""
        assert "[Select]" in self.panel.pipeline_label.text()

    def test_initial_progress_hidden(self):
        """Test initial progress bar is hidden"""
        assert not self.panel.progress_bar.isVisible()

    def test_rule_map_has_all_rules(self):
        """Test rule map contains all rules"""
        from filepilot.ui.organize_panel import OrganizePanel

        assert "category" in OrganizePanel.RULE_MAP
        assert "date" in OrganizePanel.RULE_MAP
        assert "extension" in OrganizePanel.RULE_MAP
        assert "size" in OrganizePanel.RULE_MAP


class TestOrganizePanelFolderSelection:
    """Test folder selection functionality"""

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
        """Test selecting source folder updates the label"""
        with patch(
            "PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=str(tmp_path)
        ):
            self.panel._on_select_source()

        assert self.panel.source_dir == tmp_path
        assert str(tmp_path) in self.panel.src_path_label.text()
        assert self.panel.btn_preview.isEnabled()

    def test_select_source_sets_default_target(self, tmp_path):
        """Test selecting source folder auto-sets default target"""
        with patch(
            "PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=str(tmp_path)
        ):
            self.panel._on_select_source()

        assert self.panel.target_dir == tmp_path / "_organized"
        assert "_organized" in self.panel.dst_path_label.text()

    def test_select_source_does_not_override_existing_target(self, tmp_path):
        """Test selecting source folder does not override existing custom target"""
        custom_target = Path("/custom/target")
        self.panel.target_dir = custom_target
        self.panel.dst_path_label.setText(f"🎯 {custom_target}")

        with patch(
            "PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=str(tmp_path)
        ):
            self.panel._on_select_source()

        assert self.panel.target_dir == custom_target  # Should not be overridden

    def test_select_source_cancel(self):
        """Test canceling source folder selection"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=""):
            self.panel._on_select_source()
        assert self.panel.source_dir is None

    def test_select_target_updates_label(self, tmp_path):
        """Test selecting target folder updates the label"""
        with patch(
            "PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=str(tmp_path)
        ):
            self.panel._on_select_target()

        assert self.panel.target_dir == tmp_path
        assert str(tmp_path) in self.panel.dst_path_label.text()

    def test_select_target_cancel(self):
        """Test canceling target folder selection"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=""):
            self.panel._on_select_target()
        assert self.panel.target_dir is None


class TestOrganizePanelRules:
    """Test organize rule selection"""

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
        """Test default selection of category rule"""
        from filepilot.core.file_organizer import CategoryRule

        rules = self.panel._get_selected_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], CategoryRule)

    def test_get_selected_rules_multiple(self):
        """Test multiple rule selection"""
        self.panel.cb_date.setChecked(True)
        self.panel.cb_extension.setChecked(True)
        self.panel.cb_category.setChecked(True)

        rules = self.panel._get_selected_rules()
        assert len(rules) == 3

    def test_get_selected_rules_fallback_to_category(self):
        """Test fallback to category rule when none selected"""
        from filepilot.core.file_organizer import CategoryRule

        self.panel.cb_category.setChecked(False)
        self.panel.cb_date.setChecked(False)
        self.panel.cb_extension.setChecked(False)
        self.panel.cb_size.setChecked(False)

        rules = self.panel._get_selected_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], CategoryRule)

    def test_category_rule_toggle(self):
        """Test category rule checkbox toggle"""
        from filepilot.core.file_organizer import CategoryRule

        self.panel.cb_category.setChecked(False)
        rules = self.panel._get_selected_rules()
        # Should fallback to CategoryRule
        assert isinstance(rules[0], CategoryRule)

    def test_template_help_shows_dialog(self):
        """Test template help shows dialog"""
        with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
            self.panel._on_template_help()
            mock_info.assert_called_once()


class TestOrganizePanelPreviewAndExecute:
    """Test preview and execute functionality"""

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
        """Test preview without source does nothing"""
        self.panel.source_dir = None
        self.panel._on_preview()
        # Should not start any async operation
        assert not self.panel.progress_bar.isVisible()

    def test_display_preview_shows_operations(self):
        """Test preview result display"""
        operations = [
            {
                "source": "a.pdf",
                "destination": "/organized/PDF/a.pdf",
                "category": "PDF",
                "size": "1 MB",
            },
            {
                "source": "b.py",
                "destination": "/organized/Code/b.py",
                "category": "Code",
                "size": "2 KB",
            },
        ]

        self.panel._display_preview(operations, files=[MagicMock()])

        assert self.panel.result_table.rowCount() == 2
        assert self.panel.result_table.item(0, 0).text() == "a.pdf"
        assert self.panel.result_table.item(0, 2).text() == "PDF"
        assert self.panel.btn_execute.isEnabled()
        assert "2 files will be organized" in self.panel.stats_label.text()
        assert "Precheck passed" in self.panel.precheck_label.text()

    def test_display_preview_empty_operations(self):
        """Test empty preview result"""
        self.panel._display_preview([], files=[])

        assert self.panel.result_table.rowCount() == 0
        assert not self.panel.btn_execute.isEnabled()
        assert "needs attention" in self.panel.precheck_label.text()

    def test_display_preview_sets_files(self):
        """Test preview sets file list"""
        mock_files = [MagicMock(), MagicMock()]
        self.panel._display_preview([], files=mock_files)

        assert self.panel.files == mock_files

    def test_display_preview_uses_custom_target_dir(self, tmp_path):
        """Preview status should show the selected target without appending _organized."""
        custom_target = tmp_path / "custom"
        self.panel.source_dir = tmp_path / "source"
        self.panel.target_dir = custom_target

        self.panel._display_preview([], files=[])

        assert f"target: {custom_target}" in self.panel.stats_label.text()

    def test_precheck_blocks_existing_target(self, tmp_path):
        """Execution should be blocked when a planned destination already exists."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        source.write_text("source")
        dest.write_text("dest")

        self.panel._display_preview(
            [
                {
                    "source": str(source),
                    "destination": str(dest),
                    "category": "Document",
                    "size": "1 B",
                }
            ],
            files=[MagicMock()],
        )

        assert not self.panel.btn_execute.isEnabled()
        assert "target path" in self.panel.precheck_label.text()
        assert "target exists" in self.panel.result_table.item(0, 4).text()

    def test_precheck_marks_review_destinations(self, tmp_path):
        """Review-routed files should be visible in the precheck warning strip."""
        source = tmp_path / "unknown.bin"
        source.write_text("source")

        self.panel._display_preview(
            [
                {
                    "source": str(source),
                    "destination": str(tmp_path / "Review" / "unknown.bin"),
                    "category": "Other",
                    "size": "1 B",
                }
            ],
            files=[MagicMock()],
        )

        assert self.panel.btn_execute.isEnabled()
        assert "routed to Review" in self.panel.precheck_label.text()

    def test_display_execution_shows_results(self):
        """Test execution result display"""
        operations = [
            {
                "source": "a.pdf",
                "destination": "/organized/PDF/a.pdf",
                "category": "PDF",
                "size": "1 MB",
                "dry_run": False,
            },
        ]
        self.panel.organizer.stats = {"organized_count": 1, "errors": 0}

        self.panel._display_execution(operations)

        assert self.panel.result_table.rowCount() == 1
        assert "Moved" in self.panel.result_table.item(0, 4).text()
        assert "[Done]" in self.panel.pipeline_label.text()

    def test_display_execution_with_errors(self):
        """Test execution result display (with errors)"""
        operations = [
            {
                "source": "a.pdf",
                "destination": "/organized/PDF/a.pdf",
                "category": "PDF",
                "size": "1 MB",
                "dry_run": False,
            },
        ]
        self.panel.organizer.stats = {"organized_count": 1, "errors": 1}

        self.panel._display_execution(operations)

        assert "1 error" in self.panel.stats_label.text()


class TestOrganizePanelClear:
    """Test clear results functionality"""

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
        """Test clear results empties the table"""
        self.panel.result_table.setRowCount(5)
        self.panel.btn_execute.setEnabled(True)

        self.panel._clear_results()

        assert self.panel.result_table.rowCount() == 0
        assert not self.panel.btn_execute.isEnabled()
        assert "Ready" in self.panel.stats_label.text()


class TestOrganizePanelMockIntegration:
    """Test complete Mock integration flow"""

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
        """Test complete preview flow using Mock"""
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
            {
                "source": "report.pdf",
                "destination": "/organized/PDF/report.pdf",
                "category": "PDF",
                "size": "1 KB",
            },
        ]

        # Simulate display preview (skipping threading)
        self.panel._display_preview(
            self.panel.organizer.organize.return_value,
            files=[mock_file],
        )

        assert self.panel.result_table.rowCount() == 1
        assert "report.pdf" in self.panel.result_table.item(0, 0).text()

    def test_mock_execute_flow(self, qtbot):
        """Test complete execute flow using Mock"""
        mock_file = MagicMock()
        self.panel.files = [mock_file]
        self.panel.organizer.organize.return_value = [
            {
                "source": "report.pdf",
                "destination": "/organized/PDF/report.pdf",
                "category": "PDF",
                "size": "1 KB",
                "dry_run": False,
            },
        ]
        self.panel.organizer.stats = {"organized_count": 1, "errors": 0}

        # Simulate display execution
        self.panel._display_execution(self.panel.organizer.organize.return_value)

        assert "Moved" in self.panel.result_table.item(0, 4).text()
        assert "files moved" in self.panel.stats_label.text()


class TestOrganizePanelEdgeCases:
    """Test edge cases"""

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
        """Test executing without source does nothing"""
        self.panel.source_dir = None
        self.panel._on_execute()
        # Without source_dir _on_execute should return immediately
        with patch.object(self.panel, "_get_selected_rules") as mock_rules:
            self.panel._on_execute()
            mock_rules.assert_not_called()

    def test_execute_with_no_files(self):
        """Test executing without files does nothing"""
        self.panel.source_dir = Path("/tmp")
        self.panel.files = []
        # With empty files _on_execute should return immediately
        with patch.object(self.panel, "_get_selected_rules") as mock_rules:
            self.panel._on_execute()
            mock_rules.assert_not_called()

    def test_rename_input_placeholder(self):
        """Test rename input placeholder text"""
        assert (
            "Supports: {name} {date} {time} {ext} {category}"
            in self.panel.rename_input.placeholderText()
        )

    def test_undo_btn_disabled_by_default(self):
        """Test undo rename button is disabled initially"""
        assert not self.panel.regex_undo_btn.isEnabled()

    def test_undo_empty_does_nothing(self):
        """Test _on_regex_undo with empty undo stack"""
        self.panel._regex_undo = []
        self.panel._on_regex_undo()
        assert self.panel._regex_undo == []


class TestOrganizePanelRegexUndo:
    """Tests for batch regex rename undo functionality"""

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

    def test_undo_restores_file_in_reverse_order(self, tmp_path, monkeypatch):
        src1 = tmp_path / "a.txt"
        src2 = tmp_path / "b.txt"
        dst1 = tmp_path / "a_renamed.txt"
        dst2 = tmp_path / "b_renamed.txt"
        dst1.write_text("a")
        dst2.write_text("b")
        self.panel._regex_undo = [
            {"source": str(src1), "destination": str(dst1)},
            {"source": str(src2), "destination": str(dst2)},
        ]
        self.panel.regex_undo_btn.setEnabled(True)
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.question",
            lambda *a, **kw: QMessageBox.Yes,
        )
        self.panel._on_regex_undo()

        assert self.panel._regex_undo == []
        assert not self.panel.regex_undo_btn.isEnabled()
        assert src1.exists()
        assert src2.exists()
        assert not dst1.exists()
        assert not dst2.exists()

    def test_undo_skips_nonexistent_destination_gracefully(self, tmp_path, monkeypatch):
        """Production silently skips nonexistent destination (no error count increment)."""
        self.panel._regex_undo = [
            {"source": str(tmp_path / "missing.txt"), "destination": str(tmp_path / "gone.txt")},
        ]
        self.panel.regex_undo_btn.setEnabled(True)
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.question",
            lambda *a, **kw: QMessageBox.Yes,
        )
        self.panel._on_regex_undo()

        assert self.panel._regex_undo == []
        assert not self.panel.regex_undo_btn.isEnabled()

    def test_undo_empty_stack_does_nothing(self):
        self.panel._regex_undo = []
        self.panel._on_regex_undo()
        assert self.panel._regex_undo == []

    def test_undo_rejected_by_user_does_nothing(self, tmp_path, monkeypatch):
        src = tmp_path / "old.txt"
        dst = tmp_path / "new.txt"
        dst.write_text("content")
        self.panel._regex_undo = [
            {"source": str(src), "destination": str(dst)},
        ]
        self.panel.regex_undo_btn.setEnabled(True)
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.question",
            lambda *a, **kw: QMessageBox.No,
        )
        self.panel._on_regex_undo()

        assert len(self.panel._regex_undo) == 1
        assert self.panel.regex_undo_btn.isEnabled()
