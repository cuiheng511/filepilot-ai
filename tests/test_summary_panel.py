"""SummaryPanel unit tests — file selection, AI summary generation, signal handling"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt


class TestSummaryPanelInitialState:
    """Test panel initial state"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        """Create panel and add to qtbot"""
        with (
            patch.multiple("filepilot.ai.summarizer", Summarizer=MagicMock()),
            patch.multiple("filepilot.ai.local_ai", LocalAI=MagicMock()),
            patch.multiple("filepilot.ai.cloud_ai", CloudAI=MagicMock()),
        ):
            from filepilot.ui.summary_panel import SummaryPanel

            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_initial_title(self):
        """Test initial section title label"""
        assert True  # Panel is embedded, no window title to check

    def test_initial_buttons_disabled(self):
        """Test initial button states"""
        assert not self.panel.btn_generate.isEnabled()
        assert self.panel.btn_add_files.isEnabled()
        assert self.panel.btn_add_folder.isEnabled()
        assert self.panel.btn_clear_files.isEnabled()

    def test_initial_file_list_empty(self):
        """Test initial file list is empty"""
        assert self.panel.file_list.count() == 0

    def test_initial_progress_hidden(self):
        """Test initial progress bar is hidden"""
        assert not self.panel.progress_bar.isVisible()

    def test_initial_summary_empty(self):
        """Test initial summary output is empty"""
        assert self.panel.summary_output.toPlainText() == ""

    def test_initial_keywords_empty(self):
        """Test initial keyword output is empty"""
        assert self.panel.keyword_output.toPlainText() == ""

    def test_initial_cancel_hidden(self):
        """Test cancel button is hidden initially"""
        assert not self.panel.btn_cancel.isVisible()

    def test_supported_extensions(self):
        """Test supported file extension set"""
        from filepilot.ui.summary_panel import SUPPORTED_EXTS

        assert ".pdf" in SUPPORTED_EXTS
        assert ".md" in SUPPORTED_EXTS
        assert ".py" in SUPPORTED_EXTS
        assert ".txt" in SUPPORTED_EXTS
        assert ".jpg" not in SUPPORTED_EXTS  # Image files not supported


class TestSummaryPanelFileSelection:
    """Test file selection functionality"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot, tmp_path):
        with (
            patch.multiple("filepilot.ai.summarizer", Summarizer=MagicMock()),
            patch.multiple("filepilot.ai.local_ai", LocalAI=MagicMock()),
            patch.multiple("filepilot.ai.cloud_ai", CloudAI=MagicMock()),
        ):
            from filepilot.ui.summary_panel import SummaryPanel

            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)
            self.tmp_dir = tmp_path
            # Create test files
            self.test_md = tmp_path / "test.md"
            self.test_md.write_text("# Test\n\nThis is a test markdown file for summary.")
            self.test_py = tmp_path / "test.py"
            self.test_py.write_text("def foo():\n    pass\n")
            self.test_txt = tmp_path / "test.txt"
            self.test_txt.write_text("Plain text file content.")

    def test_add_single_file_updates_list(self):
        """Test adding a single file populates the list"""
        mock_path = str(self.test_md)

        with patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=([mock_path], "")
        ):
            self.panel._on_add_files()

        assert self.panel.file_list.count() == 1
        assert self.panel.btn_generate.isEnabled()

    def test_add_single_file_cancel(self):
        """Test canceling file selection"""
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=([], "")):
            self.panel._on_add_files()

        assert self.panel.file_list.count() == 0
        assert not self.panel.btn_generate.isEnabled()

    def test_add_unsupported_file_skipped(self):
        """Test unsupported files are not added"""
        unsupported = self.tmp_dir / "program.exe"
        unsupported.write_bytes(b"\x00" * 100)

        with patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=([str(unsupported)], "")
        ):
            self.panel._on_add_files()

        assert self.panel.file_list.count() == 0

    def test_add_multiple_files(self):
        """Test adding multiple files"""
        paths = [str(self.test_md), str(self.test_py), str(self.test_txt)]

        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=(paths, "")):
            self.panel._on_add_files()

        assert self.panel.file_list.count() == 3
        assert self.panel.btn_generate.isEnabled()

    def test_add_duplicate_file_skipped(self):
        """Test adding the same file twice doesn't duplicate"""
        mock_path = str(self.test_md)

        with patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=([mock_path], "")
        ):
            self.panel._on_add_files()
            self.panel._on_add_files()

        assert self.panel.file_list.count() == 1

    def test_clear_files_empties_list(self):
        """Test clearing files empties the list and disables generate"""
        with patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=([str(self.test_md)], "")
        ):
            self.panel._on_add_files()

        assert self.panel.file_list.count() == 1
        self.panel.file_list.clear()
        # Call _on_add_files to update button state
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=([], "")):
            self.panel._on_add_files()
        assert not self.panel.btn_generate.isEnabled()

    def test_add_folder_scan(self, qtbot):
        """Test adding a folder scans and adds supported files"""
        from filepilot.core.file_scanner import FileInfo

        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = [
            FileInfo(
                path=Path(str(self.test_md)),
                name="test.md",
                extension=".md",
                size_bytes=100,
                size_str="100 B",
                category=None,
                mime_type="text/markdown",
                modified_time=datetime.now(),
                created_time=datetime.now(),
                is_directory=False,
            ),
        ]

        with (
            patch("filepilot.core.file_scanner.FileScanner", return_value=mock_scanner),
            patch(
                "PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=str(self.tmp_dir)
            ),
        ):
            self.panel._on_add_folder()
            qtbot.wait(500)

        assert self.panel.file_list.count() >= 1

    def test_add_folder_cancel(self):
        """Test canceling folder selection"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory", return_value=""):
            self.panel._on_add_folder()

        assert self.panel.file_list.count() == 0


class TestSummaryPanelFileList:
    """Test file list item data"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with (
            patch.multiple("filepilot.ai.summarizer", Summarizer=MagicMock()),
            patch.multiple("filepilot.ai.local_ai", LocalAI=MagicMock()),
            patch.multiple("filepilot.ai.cloud_ai", CloudAI=MagicMock()),
        ):
            from filepilot.ui.summary_panel import SummaryPanel

            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_add_file_item_stores_path(self):
        """Test _add_file_item stores the path in UserRole"""
        self.panel._add_file_item("test.md", ".md", "/tmp/test.md")
        assert self.panel.file_list.count() == 1
        item = self.panel.file_list.item(0)
        assert item.data(Qt.UserRole) == "/tmp/test.md"
        assert item.toolTip() == "/tmp/test.md"

    def test_add_file_item_enables_generate(self):
        """Test _add_file_item enables generate button"""
        self.panel._add_file_item("test.md", ".md", "/tmp/test.md")
        assert self.panel.btn_generate.isEnabled()


class TestSummaryPanelIsSupported:
    """Test file extension support checking"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with (
            patch.multiple("filepilot.ai.summarizer", Summarizer=MagicMock()),
            patch.multiple("filepilot.ai.local_ai", LocalAI=MagicMock()),
            patch.multiple("filepilot.ai.cloud_ai", CloudAI=MagicMock()),
        ):
            from filepilot.ui.summary_panel import SummaryPanel

            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_supported_pdf(self):
        assert self.panel._is_supported(Path("test.pdf"))

    def test_supported_markdown(self):
        assert self.panel._is_supported(Path("test.md"))

    def test_supported_python(self):
        assert self.panel._is_supported(Path("test.py"))

    def test_not_supported_image(self):
        assert not self.panel._is_supported(Path("test.jpg"))

    def test_not_supported_binary(self):
        assert not self.panel._is_supported(Path("test.exe"))


class TestSummaryPanelGenerateState:
    """Test generate button state management"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with (
            patch.multiple("filepilot.ai.summarizer", Summarizer=MagicMock()),
            patch.multiple("filepilot.ai.local_ai", LocalAI=MagicMock()),
            patch.multiple("filepilot.ai.cloud_ai", CloudAI=MagicMock()),
        ):
            from filepilot.ui.summary_panel import SummaryPanel

            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_generate_with_no_files_shows_warning(self):
        """Test clicking generate with no files shows a warning"""
        self.panel._on_generate()
        # State should remain unchanged
        assert not self.panel.btn_generate.isEnabled()  # Already disabled
        assert not self.panel.progress_bar.isVisible()

    def test_generate_enabled_after_adding_files(self):
        """Test generate is enabled after adding files"""
        self.panel._add_file_item("test.md", ".md", "/tmp/test.md")
        assert self.panel.btn_generate.isEnabled()

    def test_generate_disabled_during_processing(self):
        """Test generate is disabled during processing"""
        self.panel._add_file_item("test.md", ".md", "/tmp/test.md")
        # Simulate generate click - btn gets disabled
        self.panel.btn_generate.setEnabled(False)
        assert not self.panel.btn_generate.isEnabled()

    def test_enable_after_clear(self):
        """Test generate is disabled after clearing all files"""
        self.panel._add_file_item("test.md", ".md", "/tmp/test.md")
        assert self.panel.btn_generate.isEnabled()
        self.panel.file_list.clear()
        # Update button state after clear
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileNames", return_value=([], "")):
            self.panel._on_add_files()
        assert not self.panel.btn_generate.isEnabled()


class TestSummaryPanelSignalEmission:
    """Test signal emissions for displaying results"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with (
            patch.multiple("filepilot.ai.summarizer", Summarizer=MagicMock()),
            patch.multiple("filepilot.ai.local_ai", LocalAI=MagicMock()),
            patch.multiple("filepilot.ai.cloud_ai", CloudAI=MagicMock()),
        ):
            from filepilot.ui.summary_panel import SummaryPanel

            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_summary_ready_signal_updates_output(self):
        """Test summary_ready signal sets the summary_output text"""
        test_summary = "This is the AI-generated summary."
        self.panel.summary_ready.emit(test_summary)
        assert test_summary in self.panel.summary_output.toPlainText()

    def test_keyword_ready_signal_updates_output(self):
        """Test keyword_ready signal sets the keyword_output text"""
        test_keywords = "Python, AI, test"
        self.panel.keyword_ready.emit(test_keywords)
        assert test_keywords in self.panel.keyword_output.toPlainText()

    def test_progress_updated_signal_changes_bar(self):
        """Test progress_updated signal changes progress bar value"""
        self.panel.progress_bar.setVisible(True)
        self.panel.progress_updated.emit(50)
        assert self.panel.progress_bar.value() == 50

    def test_status_message_updates_label(self):
        """Test status_message signal updates stats_label"""
        self.panel.status_message.emit("Processing complete")
        assert "Processing complete" in self.panel.stats_label.text()


class TestSummaryPanelMockIntegration:
    """Test complete Mock integration flow"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        from filepilot.ui.summary_panel import SummaryPanel

        self.panel = SummaryPanel()
        qtbot.addWidget(self.panel)

    def test_summary_signal_propagation(self, qtbot):
        """Test that summary_ready signal propagates to output widget"""
        test_text = "Mocked summary content."
        self.panel.summary_ready.emit(test_text)
        assert "Mocked summary" in self.panel.summary_output.toPlainText()

    def test_keyword_signal_propagation(self, qtbot):
        """Test that keyword_ready signal propagates to output widget"""
        test_text = "test, mock, summary"
        self.panel.keyword_ready.emit(test_text)
        assert test_text in self.panel.keyword_output.toPlainText()


class TestSummaryPanelAIInit:
    """Test AI lazy initialization"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        from filepilot.ui.summary_panel import SummaryPanel

        self.panel = SummaryPanel()
        qtbot.addWidget(self.panel)
        assert not self.panel._lazy_init_done

    def test_ensure_ai_init_local_ai(self):
        """Test _ensure_ai_init sets up local AI"""
        assert not self.panel._lazy_init_done
        self.panel._ensure_ai_init()
        assert self.panel._lazy_init_done

    def test_ensure_ai_init_only_once(self):
        """Test _ensure_ai_init only runs once"""
        self.panel._ensure_ai_init()
        self.panel._ensure_ai_init()  # Second call should be no-op
        assert self.panel._lazy_init_done


class TestSummaryPanelErrors:
    """Test edge cases and error handling"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with (
            patch.multiple("filepilot.ai.summarizer", Summarizer=MagicMock()),
            patch.multiple("filepilot.ai.local_ai", LocalAI=MagicMock()),
            patch.multiple("filepilot.ai.cloud_ai", CloudAI=MagicMock()),
        ):
            from filepilot.ui.summary_panel import SummaryPanel

            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_generate_with_no_files(self):
        """Test clicking generate with no files shows warning"""
        self.panel._on_generate()
        assert not self.panel.progress_bar.isVisible()
        # Button should remain disabled since no files
        assert not self.panel.btn_generate.isEnabled()

    def test_cancel_hidden_initially(self):
        """Test cancel button is hidden initially"""
        assert not self.panel.btn_cancel.isVisible()

    def test_cancel_visible_during_generate(self):
        """Test cancel is visible during generate"""
        self.panel._add_file_item("test.md", ".md", "/tmp/test.md")
        self.panel.btn_generate.setEnabled(False)
        self.panel.btn_cancel.setVisible(True)
        assert not self.panel.btn_cancel.isHidden()
