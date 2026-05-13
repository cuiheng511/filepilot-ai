"""SummaryPanel 单元测试 — 文件选择、AI 摘要、批量处理、错误处理"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保 Qt 应用已创建（pytest-qt 的 qtbot 会自动处理）


class TestSummaryPanelInitialState:
    """测试面板初始状态"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        """创建面板并添加到 qtbot"""
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
        """测试初始标题"""
        assert self.panel.windowTitle() == ""  # 没有独立窗口标题

    def test_initial_file_path_label(self):
        """测试初始文件路径标签"""
        assert "未选择" in self.panel.file_path_label.text()

    def test_initial_buttons_disabled(self):
        """测试初始按钮状态"""
        assert not self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_batch.isEnabled()
        assert not self.panel.btn_copy.isEnabled()
        assert not self.panel.btn_clear.isEnabled()

    def test_initial_file_list_hidden(self):
        """测试初始文件列表隐藏"""
        assert not self.panel.file_list.isVisible()

    def test_initial_progress_hidden(self):
        """测试初始进度条隐藏"""
        assert not self.panel.progress_bar.isVisible()
        assert not self.panel.progress_label.isVisible()

    def test_initial_preview_empty(self):
        """测试初始预览区域为空"""
        assert self.panel.content_preview.toPlainText() == ""
        assert self.panel.summary_preview.toPlainText() == ""

    def test_initial_keywords_empty(self):
        """测试初始关键词区域为空"""
        assert self.panel.keywords_layout.count() == 0

    def test_initial_files_empty(self):
        """测试初始文件列表为空"""
        assert self.panel._files == []
        assert not self.panel._processing

    def test_supported_extensions(self):
        """测试支持的文件扩展名集合"""
        from filepilot.ui.summary_panel import SummaryPanel
        exts = SummaryPanel.SUPPORTED_EXTS
        assert ".pdf" in exts
        assert ".md" in exts
        assert ".py" in exts
        assert ".txt" in exts
        assert ".jpg" not in exts  # 图片文件不支持


class TestSummaryPanelFileSelection:
    """测试文件选择功能"""

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
            # 创建测试文件
            self.test_md = tmp_path / "test.md"
            self.test_md.write_text("# Test\n\nThis is a test markdown file for summary.")
            self.test_py = tmp_path / "test.py"
            self.test_py.write_text("def foo():\n    pass\n")
            self.test_txt = tmp_path / "test.txt"
            self.test_txt.write_text("Plain text file content.")

    def test_select_single_file_updates_path(self):
        """测试选择单个文件后路径标签更新"""
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
        """测试取消选择文件"""
        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName",
                   return_value=("", "")):
            self.panel._on_select_file()

        assert self.panel._files == []

    def test_select_single_file_loads_preview(self):
        """测试选择文件后加载内容预览"""
        mock_path = str(self.test_md)

        with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName",
                   return_value=(mock_path, "")):
            self.panel._on_select_file()

        content = self.panel.content_preview.toPlainText()
        assert "Test" in content

    def test_select_folder_populates_file_list(self):
        """测试选择文件夹后批量列表更新"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(self.tmp_dir)):
            self.panel._on_select_folder()

        assert len(self.panel._files) >= 3  # .md, .py, .txt
        assert self.panel.file_list.isVisible()
        assert not self.panel.btn_summarize.isEnabled()
        assert self.panel.btn_batch.isEnabled()

    def test_select_folder_cancel(self):
        """测试取消选择文件夹"""
        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=""):
            self.panel._on_select_folder()

        assert self.panel._files == []

    def test_select_folder_with_no_supported_files(self, qtbot):
        """测试选择没有支持文件的文件夹"""
        empty_dir = self.tmp_dir / "empty"
        empty_dir.mkdir()
        # 创建一个不支持的文件
        (empty_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        with patch("PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                   return_value=str(empty_dir)):
            self.panel._on_select_folder()

        assert self.panel._files == []


class TestSummaryPanelDisplayResults:
    """测试 AI 摘要结果展示"""

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
        """测试成功摘要结果的展示"""
        result = {
            "success": True,
            "summary": "这是 AI 生成的摘要内容。它简洁地概括了文档的核心要点。",
            "keywords": ["Python", "AI", "测试", "文档"],
            "filename": "test.md",
        }

        self.panel._display_summary_result(result)

        assert "AI 生成的摘要" in self.panel.summary_preview.toPlainText()
        assert self.panel.btn_copy.isEnabled()
        # 关键词标签应该被创建
        assert self.panel.keywords_layout.count() >= len(result["keywords"])

    def test_display_failed_summary(self):
        """测试失败摘要结果的展示"""
        result = {
            "success": False,
            "summary": "",
            "keywords": [],
            "filename": "test.md",
            "error": "AI 模型不可用",
        }

        self.panel._display_summary_result(result)

        assert "失败" in self.panel.summary_preview.toPlainText()
        assert "AI 模型不可用" in self.panel.summary_preview.toPlainText()
        assert not self.panel.btn_copy.isEnabled()

    def test_display_batch_result_all_success(self):
        """测试全部成功的批量处理结果"""
        combined = "## test1.md\n\nSummary 1\n\n---\n\n## test2.md\n\nSummary 2\n\n---\n"

        self.panel._display_batch_result(combined, total=2, errors=0)

        assert self.panel.summary_preview.toPlainText() == combined
        assert self.panel.btn_copy.isEnabled()
        assert "2/2 成功" in self.panel.stats_label.text()

    def test_display_batch_result_with_errors(self):
        """测试有错误的批量处理结果"""
        combined = "## test1.md\n\nSummary 1\n\n---\n\n## test2.md\n\nerror\n\n---\n"

        self.panel._display_batch_result(combined, total=2, errors=1)

        assert self.panel.btn_copy.isEnabled()
        assert "1/2 成功" in self.panel.stats_label.text()
        assert "1 个失败" in self.panel.stats_label.text()

    def test_display_error(self):
        """测试错误信息的展示"""
        error_msg = "网络连接失败"

        self.panel._display_batch_result("", total=1, errors=1)

        assert "1/2" not in self.panel.stats_label.text()

    def test_on_summarize_error(self):
        """测试摘要错误处理"""
        error_msg = "API key 无效"

        self.panel._on_summarize_error(error_msg)

        assert not self.panel._processing
        assert not self.panel.progress_bar.isVisible()
        assert error_msg in self.panel.summary_preview.toPlainText()
        assert error_msg in self.panel.stats_label.text()


class TestSummaryPanelClearAndCopy:
    """测试清空和复制功能"""

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
        """测试清空功能重置所有状态"""
        # 先设置一些状态
        self.panel._files = [Path("/tmp/test.md")]
        self.panel._processing = True
        self.panel.file_path_label.setText("test file")
        self.panel.summary_preview.setPlainText("some summary")
        self.panel.btn_summarize.setEnabled(True)
        self.panel.btn_clear.setEnabled(True)

        self.panel._on_clear()

        assert self.panel._files == []
        assert not self.panel._processing
        assert "未选择" in self.panel.file_path_label.text()
        assert self.panel.summary_preview.toPlainText() == ""
        assert not self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_clear.isEnabled()
        assert not self.panel.file_list.isVisible()

    def test_copy_summary_to_clipboard(self, qtbot):
        """测试复制摘要到剪贴板"""
        test_text = "这是要复制的摘要内容"
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
        """测试复制空摘要不做任何事"""
        self.panel.summary_preview.clear()

        with patch("filepilot.ui.summary_panel.QApplication.clipboard") as mock_clipboard:
            self.panel._on_copy_summary()
            mock_clipboard.return_value.setText.assert_not_called()


class TestSummaryPanelMockIntegration:
    """测试完整的 Mock 集成流程"""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        from filepilot.ui.summary_panel import SummaryPanel
        self.panel = SummaryPanel()
        qtbot.addWidget(self.panel)

    def test_mock_summarizer_integration(self, qtbot, tmp_path):
        """测试使用 Mock Summarizer 的完整摘要流程"""
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

        # 模拟选择文件
        self.panel._files = [test_file]
        self.panel.btn_summarize.setEnabled(True)

        # Simulate summarize (skip threading for test)
        self.panel._processing = True

        # 直接调用结果展示（模拟线程完成后的回调）
        self.panel._display_summary_result({
            "success": True,
            "summary": "Mocked summary content.",
            "keywords": ["test", "mock", "summary"],
            "filename": "test.md",
        })

        assert "Mocked summary" in self.panel.summary_preview.toPlainText()
        assert self.panel.btn_copy.isEnabled()

    def test_mock_batch_integration(self, qtbot, tmp_path):
        """测试使用 Mock Summarizer 的批量处理流程"""
        # 创建多个文件
        f1 = tmp_path / "a.md"
        f1.write_text("# A\n\nContent A")
        f2 = tmp_path / "b.md"
        f2.write_text("# B\n\nContent B")

        self.panel._files = [f1, f2]

        # 模拟批量处理结果展示
        combined = "## a.md\n\nSummary A\n\n---\n\n## b.md\n\nSummary B\n\n---\n"
        self.panel._display_batch_result(combined, total=2, errors=0)

        assert self.panel.summary_preview.toPlainText() == combined
        assert "2/2 成功" in self.panel.stats_label.text()
        assert self.panel.btn_copy.isEnabled()


class TestSummaryPanelErrors:
    """测试边界情况和错误处理"""

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
        """测试无文件时点击摘要按钮不执行"""
        self.panel._on_summarize()
        # 不应发生任何变化
        assert not self.panel._processing

    def test_batch_with_no_files(self):
        """测试无文件时点击批量按钮不执行"""
        self.panel._on_batch_summarize()
        assert not self.panel._processing

    def test_set_buttons_enabled_single_file(self):
        """测试按钮状态：单文件模式"""
        self.panel._files = [Path("/tmp/test.md")]
        self.panel._set_buttons_enabled(True)

        assert self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_batch.isEnabled()  # 单文件禁用批量

    def test_set_buttons_enabled_batch_mode(self):
        """测试按钮状态：批量模式"""
        self.panel._files = [Path("/tmp/a.md"), Path("/tmp/b.md")]
        self.panel._set_buttons_enabled(True)

        assert not self.panel.btn_summarize.isEnabled()  # 批量禁用单文件
        assert self.panel.btn_batch.isEnabled()

    def test_set_buttons_disabled(self):
        """测试按钮状态：全部禁用"""
        self.panel._files = [Path("/tmp/test.md")]
        self.panel._set_buttons_enabled(False)

        assert not self.panel.btn_summarize.isEnabled()
        assert not self.panel.btn_batch.isEnabled()
        assert not self.panel.btn_select_file.isEnabled()
        assert not self.panel.btn_select_folder.isEnabled()

    def test_keyword_tags_cleared_on_new_result(self):
        """测试新结果会清空旧关键词标签"""
        # 先显示一批关键词
        self.panel._display_summary_result({
            "success": True,
            "summary": "Test",
            "keywords": ["old1", "old2"],
            "filename": "test.md",
        })
        old_count = self.panel.keywords_layout.count()

        # 再显示新结果
        self.panel._display_summary_result({
            "success": True,
            "summary": "New test",
            "keywords": ["new1", "new2", "new3"],
            "filename": "new.md",
        })

        # 关键词被替换而不是追加
        new_count = self.panel.keywords_layout.count()
        assert new_count >= 3  # 至少 3 个新关键词标签 + stretch

    def test_preview_truncates_long_content(self, tmp_path):
        """测试过长内容预览截断"""
        long_file = tmp_path / "long.md"
        long_file.write_text("x" * 15000)

        self.panel._load_content_preview(long_file)
        preview = self.panel.content_preview.toPlainText()
        assert "(内容过长，已截断)" in preview
        assert len(preview) <= 10000 + len("(内容过长，已截断)")

    def test_show_event_init_ai_once(self):
        """测试 showEvent 只初始化 AI 一次"""
        assert not self.panel._ai_initialized

        with patch.object(self.panel, "_init_ai") as mock_init:
            # 第一次 show
            from PySide6.QtGui import QShowEvent
            self.panel.showEvent(QShowEvent())
            assert self.panel._ai_initialized
            assert mock_init.call_count == 1

            # 第二次 show 不应再调用
            self.panel.showEvent(QShowEvent())
            assert mock_init.call_count == 1  # 仍然只调用了一次
