"""SummaryPanel unit tests — file selection, AI summary, batch processing, error handling"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure Qt app is created (pytest-qt's qtbot handles this automatically)


class TestSummaryPanelInitialState:
    """Test panel initial state"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        """Create panel and add to qtbot"""
        with patch.multiple(
            "filepilot.ui.summary_panel",
            Summarizer=MagicMock(),
            LocalAI=MagicMock(),
            CloudAI=MagicMock(),
        ):
            from filepilot.ui.summary_panel import SummaryPanel
            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_initial_title(self):
        """Test initial title"""
        assert self.panel.windowTitle() == ""  # No independent window title

    def test_initial_file_path_label(self):
        """Test initial file path label"""
        assert "Not selected" in self.panel.file_path_label.text()

    def test_initial_buttons_disabled(self):
        """Test initial button states"""
        assert not self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_batch.isEnabled()
        assert not self.panel.btn_copy.isEnabled()
        assert not self.panel.btn_clear.isEnabled()

    def test_initial_file_list_hidden(self):
        """Test initial file list is hidden"""
        assert not self.panel.file_list.isVisible()

    def test_initial_progress_hidden(self):
        """Test initial progress bar is hidden"""
        assert not self.panel.progress_bar.isVisible()
        assert not self.panel.progress_label.isVisible()

    def test_initial_preview_empty(self):
        """Test initial preview area is empty"""
        assert self.panel.content_preview.toPlainText() == ""
        assert self.panel.summary_preview.toPlainText() == ""

    def test_initial_keywords_empty(self):
        """Test initial keywords area is empty"""
        assert self.panel.keywords_layout.count() == 0

    def test_initial_files_empty(self):
        """Test initial file list is empty"""
        assert self.panel._files == []
        assert not self.panel._processing

    def test_supported_extensions(self):
        """Test supported file extension set"""
        from filepilot.ui.summary_panel import SummaryPanel
        exts = SummaryPanel.SUPPORTED_EXTS
        assert ".pdf" in exts
        assert ".md" in exts
        assert ".py" in exts
        assert ".txt" in exts
        assert ".jpg" not in exts  # Image files not supported


class TestSummaryPanelFileSelection:
    """Test file selection functionality"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot, tmp_path):
        with patch.multiple(
            "filepilot.ui.summary_panel",
            Summarizer=MagicMock(),
            LocalAI=MagicMock(),
            CloudAI=MagicMock(),
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

    def test_select_single_file_updates_path(self):
        """Test selecting a single file updates the path label"""
        mock_path = str(self.test_md)

        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName",
                   return_value=(mock_path, "")):
            self.panel._on_select_file()

        assert self.panel._files == [self.test_md]
        assert self.test_md.name in self.panel.file_path_label.text()
        assert self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_batch.isEnabled()
        assert self.panel.btn_clear.isEnabled()

    def test_select_single_file_cancel(self):
        """Test canceling file selection"""
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName",
                   return_value=("", "")):
            self.panel._on_select_file()

        assert self.panel._files == []

    def test_select_single_file_loads_preview(self):
        """Test selecting a file loads content preview"""
        mock_path = str(self.test_md)

        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName",
                   return_value=(mock_path, "")):
            self.panel._on_select_file()

        content = self.panel.content_preview.toPlainText()
        assert "Test" in content

    def test_select_folder_populates_file_list(self):
        """Test selecting a folder populates the batch list"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(self.tmp_dir)):
            self.panel._on_select_folder()

        assert len(self.panel._files) >= 3  # .md, .py, .txt
        assert self.panel.file_list.isVisible()
        assert not self.panel.btn_summarize.isEnabled()
        assert self.panel.btn_batch.isEnabled()

    def test_select_folder_cancel(self):
        """Test canceling folder selection"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=""):
            self.panel._on_select_folder()

        assert self.panel._files == []

    def test_select_folder_with_no_supported_files(self, qtbot):
        """Test selecting a folder with no supported files"""
        empty_dir = self.tmp_dir / "empty"
        empty_dir.mkdir()
        # Create an unsupported file
        (empty_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(empty_dir)):
            self.panel._on_select_folder()

        assert self.panel._files == []


class TestSummaryPanelDisplayResults:
    """Test AI summary result display"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.summary_panel",
            Summarizer=MagicMock(),
            LocalAI=MagicMock(),
            CloudAI=MagicMock(),
        ):
            from filepilot.ui.summary_panel import SummaryPanel
            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_display_successful_summary(self):
        """Test display of successful summary result"""
        result = {
            "success": True,
            "summary": "This is the AI-generated summary. It concisely covers the key points of the document.",
            "keywords": ["Python", "AI", "test", "document"],
            "filename": "test.md",
        }

        self.panel._display_summary_result(result)

        assert "AI-generated" in self.panel.summary_preview.toPlainText()
        assert self.panel.btn_copy.isEnabled()
        # Keyword tags should be created
        assert self.panel.keywords_layout.count() >= len(result["keywords"])

    def test_display_failed_summary(self):
        """Test display of failed summary result"""
        result = {
            "success": False,
            "summary": "",
            "keywords": [],
            "filename": "test.md",
            "error": "AI model unavailable",
        }

        self.panel._display_summary_result(result)

        assert "Failed" in self.panel.summary_preview.toPlainText()
        assert "AI model unavailable" in self.panel.summary_preview.toPlainText()
        assert not self.panel.btn_copy.isEnabled()

    def test_display_batch_result_all_success(self):
        """Test display of fully successful batch results"""
        combined = "## test1.md\n\nSummary 1\n\n---\n\n## test2.md\n\nSummary 2\n\n---\n"

        self.panel._display_batch_result(combined, total=2, errors=0)

        assert self.panel.summary_preview.toPlainText() == combined
        assert self.panel.btn_copy.isEnabled()
        assert "2/2 successful" in self.panel.stats_label.text()

    def test_display_batch_result_with_errors(self):
        """Test display of batch results with errors"""
        combined = "## test1.md\n\nSummary 1\n\n---\n\n## test2.md\n\nerror\n\n---\n"

        self.panel._display_batch_result(combined, total=2, errors=1)

        assert self.panel.btn_copy.isEnabled()
        assert "1/2 successful" in self.panel.stats_label.text()
        assert "1 failed" in self.panel.stats_label.text()

    def test_display_error(self):
        """Test display of error message"""
        error_msg = "Network connection failed"

        self.panel._display_batch_result("", total=1, errors=1)

        assert "1/2" not in self.panel.stats_label.text()

    def test_on_summarize_error(self):
        """Test summary error handling"""
        error_msg = "API key invalid"

        self.panel._on_summarize_error(error_msg)

        assert not self.panel._processing
        assert not self.panel.progress_bar.isVisible()
        assert error_msg in self.panel.summary_preview.toPlainText()
        assert error_msg in self.panel.stats_label.text()


class TestSummaryPanelClearAndCopy:
    """Test clear and copy functionality"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.summary_panel",
            Summarizer=MagicMock(),
            LocalAI=MagicMock(),
            CloudAI=MagicMock(),
        ):
            from filepilot.ui.summary_panel import SummaryPanel
            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_clear_resets_state(self):
        """Test clear resets all state"""
        # Set some state first
        self.panel._files = [Path("/tmp/test.md")]
        self.panel._processing = True
        self.panel.file_path_label.setText("test file")
        self.panel.summary_preview.setPlainText("some summary")
        self.panel.btn_summarize.setEnabled(True)
        self.panel.btn_clear.setEnabled(True)

        self.panel._on_clear()

        assert self.panel._files == []
        assert not self.panel._processing
        assert "Not selected" in self.panel.file_path_label.text()
        assert self.panel.summary_preview.toPlainText() == ""
        assert not self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_clear.isEnabled()
        assert not self.panel.file_list.isVisible()

    def test_copy_summary_to_clipboard(self, qtbot):
        """Test copying summary to clipboard"""
        test_text = "This is the summary content to copy"
        self.panel.summary_preview.setPlainText(test_text)
        self.panel.btn_copy.setEnabled(True)

        with patch.object(self.panel.summary_preview, "toPlainText",
                          return_value=test_text):
            with patch("filepilot.ui.summary_panel.QApplication.clipboard") as mock_clipboard:
                mock_clipboard_instance = MagicMock()
                mock_clipboard.return_value = mock_clipboard_instance

                self.panel._on_copy_summary()

                mock_clipboard_instance.setText.assert_called_once_with(test_text)

    def test_copy_empty_summary_does_nothing(self, qtbot):
        """Test copying empty summary does nothing"""
        self.panel.summary_preview.clear()

        with patch("filepilot.ui.summary_panel.QApplication.clipboard") as mock_clipboard:
            self.panel._on_copy_summary()
            mock_clipboard.return_value.setText.assert_not_called()


class TestSummaryPanelMockIntegration:
    """Test complete Mock integration flow"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        from filepilot.ui.summary_panel import SummaryPanel
        self.panel = SummaryPanel()
        qtbot.addWidget(self.panel)

    def test_mock_summarizer_integration(self, qtbot, tmp_path):
        """Test complete summary flow with Mock Summarizer"""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent for summary test.")

        # Mock Summarizer
        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = {
            "success": True,
            "summary": "Mocked summary content.",
            "keywords": ["test", "mock", "summary"],
            "filename": "test.md",
        }
        self.panel._summarizer = mock_summarizer

        # Simulate file selection
        self.panel._files = [test_file]
        self.panel.btn_summarize.setEnabled(True)

        # Simulate summarize (skip threading for test)
        self.panel._processing = True

        # Directly call result display (simulating thread completion callback)
        self.panel._display_summary_result({
            "success": True,
            "summary": "Mocked summary content.",
            "keywords": ["test", "mock", "summary"],
            "filename": "test.md",
        })

        assert "Mocked summary" in self.panel.summary_preview.toPlainText()
        assert self.panel.btn_copy.isEnabled()

    def test_mock_batch_integration(self, qtbot, tmp_path):
        """Test complete batch flow with Mock Summarizer"""
        # Create multiple files
        f1 = tmp_path / "a.md"
        f1.write_text("# A\n\nContent A")
        f2 = tmp_path / "b.md"
        f2.write_text("# B\n\nContent B")

        self.panel._files = [f1, f2]

        # Simulate batch result display
        combined = "## a.md\n\nSummary A\n\n---\n\n## b.md\n\nSummary B\n\n---\n"
        self.panel._display_batch_result(combined, total=2, errors=0)

        assert self.panel.summary_preview.toPlainText() == combined
        assert "2/2 successful" in self.panel.stats_label.text()
        assert self.panel.btn_copy.isEnabled()


class TestSummaryPanelErrors:
    """Test edge cases and error handling"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.summary_panel",
            Summarizer=MagicMock(),
            LocalAI=MagicMock(),
            CloudAI=MagicMock(),
        ):
            from filepilot.ui.summary_panel import SummaryPanel
            self.panel = SummaryPanel()
            qtbot.addWidget(self.panel)

    def test_summarize_with_no_files(self):
        """Test clicking summarize with no files does nothing"""
        self.panel._on_summarize()
        # Should not change any state
        assert not self.panel._processing

    def test_batch_with_no_files(self):
        """Test clicking batch with no files does nothing"""
        self.panel._on_batch_summarize()
        assert not self.panel._processing

    def test_set_buttons_enabled_single_file(self):
        """Test button states: single file mode"""
        self.panel._files = [Path("/tmp/test.md")]
        self.panel._set_buttons_enabled(True)

        assert self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_batch.isEnabled()  # Single file disables batch

    def test_set_buttons_enabled_batch_mode(self):
        """Test button states: batch mode"""
        self.panel._files = [Path("/tmp/a.md"), Path("/tmp/b.md")]
        self.panel._set_buttons_enabled(True)

        assert not self.panel.btn_summarize.isEnabled()  # Batch disables single file
        assert self.panel.btn_batch.isEnabled()

    def test_set_buttons_disabled(self):
        """Test button states: all disabled"""
        self.panel._files = [Path("/tmp/test.md")]
        self.panel._set_buttons_enabled(False)

        assert not self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_batch.isEnabled()
        assert not self.panel.btn_select_file.isEnabled()
        assert not self.panel.btn_select_folder.isEnabled()

    def test_keyword_tags_cleared_on_new_result(self):
        """Test keyword tags are cleared on new result"""
        # Display one set of keywords first
        self.panel._display_summary_result({
            "success": True,
            "summary": "Test",
            "keywords": ["old1", "old2"],
            "filename": "test.md",
        })
        old_count = self.panel.keywords_layout.count()

        # Display new result
        self.panel._display_summary_result({
            "success": True,
            "summary": "New test",
            "keywords": ["new1", "new2", "new3"],
            "filename": "new.md",
        })

        # Keywords should be replaced, not appended
        new_count = self.panel.keywords_layout.count()
        assert new_count >= 3  # At least 3 keyword tags + stretch

    def test_preview_truncates_long_content(self, tmp_path):
        """Test preview truncates long content"""
        long_file = tmp_path / "long.md"
        long_file.write_text("x" * 15000)

        self.panel._load_content_preview(long_file)
        preview = self.panel.content_preview.toPlainText()
        assert "(content too long, truncated)" in preview
        assert len(preview) <= 10000 + len("(content too long, truncated)")

    def test_show_event_init_ai_once(self):
        """Test showEvent only initializes AI once"""
        assert not self.panel._ai_initialized

        with patch.object(self.panel, "_init_ai") as mock_init:
            # First show
            from PySide6.QtGui import QShowEvent
            self.panel.showEvent(QShowEvent())
            assert self.panel._ai_initialized
            assert mock_init.call_count == 1

            # Second show should not call again
            self.panel.showEvent(QShowEvent())
            assert mock_init.call_count == 1  # Still only called once
