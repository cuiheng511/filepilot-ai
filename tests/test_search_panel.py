"""Search panel unit tests — _display_results, highlight conversion, and export."""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox


class TestDisplayResults:
    """Test _display_results produces correct QListWidgetItems."""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        with patch.multiple(
            "filepilot.ui.search_panel",
            FileIndexer=MagicMock(),
            FileScanner=MagicMock(),
            AppState=MagicMock(),
            EventBus=MagicMock(),
        ):
            from filepilot.ui.search_panel import SearchPanel

            self.panel = SearchPanel()
            qtbot.addWidget(self.panel)

    def test_display_results_creates_items(self):
        results = [
            {
                "path": "/tmp/test.py",
                "filename": "test.py",
                "extension": ".py",
                "category": "Code",
                "size": 1024,
                "size_str": "1.0 KB",
                "modified": "2024-06-15 14:30",
                "score": 0.92,
                "highlights": '<b class="match">import</b> os',
            }
        ]
        self.panel._display_results(results, "test query")
        assert self.panel.result_list.count() == 1

    def test_display_results_stores_filepath(self):
        results = [
            {
                "path": "/tmp/test.py",
                "filename": "test.py",
                "extension": ".py",
                "category": "Code",
                "size": 1024,
                "size_str": "1.0 KB",
                "modified": "2024-06-15 14:30",
                "score": 0.92,
                "highlights": "",
            }
        ]
        self.panel._display_results(results, "query")
        item = self.panel.result_list.item(0)
        assert item.data(Qt.UserRole) == "/tmp/test.py"

    def test_display_results_stores_html(self):
        results = [
            {
                "path": "/tmp/test.py",
                "filename": "test.py",
                "extension": ".py",
                "category": "Code",
                "size": 1024,
                "size_str": "1.0 KB",
                "modified": "2024-06-15 14:30",
                "score": 0.92,
                "highlights": '<b class="match">import</b> os',
            }
        ]
        self.panel._display_results(results, "query")
        item = self.panel.result_list.item(0)
        html = item.data(Qt.UserRole + 1)
        assert html is not None
        assert "💻" in html  # Code icon
        assert "test.py" in html
        assert "92%" in html  # score as percentage

    def test_display_results_no_highlights_empty_snippet(self):
        results = [
            {
                "path": "/tmp/no_hl.txt",
                "filename": "no_hl.txt",
                "extension": ".txt",
                "category": "Document",
                "size": 50,
                "size_str": "50 B",
                "modified": "2024-06-15 14:30",
                "score": 0.5,
                "highlights": "",
            }
        ]
        self.panel._display_results(results, "query")
        item = self.panel.result_list.item(0)
        html = item.data(Qt.UserRole + 1)
        assert html is not None
        assert "📌" not in html  # no highlight snippet

    def test_display_results_highlight_converted(self):
        raw = '<b class="match">pricing</b> strategy <b class="match">risk</b>'
        expected_style = 'style="color:#e67e22;background:#fff3e0;"'
        results = [
            {
                "path": "/tmp/rpt.pdf",
                "filename": "rpt.pdf",
                "extension": ".pdf",
                "category": "PDF",
                "size": 500,
                "size_str": "500 B",
                "modified": "2024-06-15 14:30",
                "score": 0.85,
                "highlights": raw,
            }
        ]
        self.panel._display_results(results, "query")
        item = self.panel.result_list.item(0)
        html = item.data(Qt.UserRole + 1)
        assert expected_style in html
        assert "pricing" in html
        assert "risk" in html

    def test_display_results_truncates_long_highlights(self):
        long_hl = ('<b class="match">word</b> ' * 50).strip()
        results = [
            {
                "path": "/tmp/long.txt",
                "filename": "long.txt",
                "extension": ".txt",
                "category": "Text",
                "size": 100,
                "size_str": "100 B",
                "modified": "2024-06-15 14:30",
                "score": 0.9,
                "highlights": long_hl,
            }
        ]
        self.panel._display_results(results, "query")
        item = self.panel.result_list.item(0)
        html = item.data(Qt.UserRole + 1)
        # Highlight snippet should be present and end with ellipsis
        assert "📌" in html
        assert "…" in html

    def test_display_results_updates_stats_label(self):
        results = [
            {
                "path": "/tmp/a.py",
                "filename": "a.py",
                "extension": ".py",
                "category": "Code",
                "size": 1,
                "size_str": "1 B",
                "modified": "",
                "score": 1.0,
                "highlights": "",
            }
        ]
        self.panel._display_results(results, "my query")
        assert "1 results" in self.panel.stats_label.text()
        assert "my query" in self.panel.stats_label.text()

    def test_export_uses_filename_from_path(self, qtbot, tmp_path):
        """_on_export should use Path(filepath).name when item.text() is empty."""
        export_path = tmp_path / "export.json"
        results = [
            {
                "path": "/tmp/report.pdf",
                "filename": "report.pdf",
                "extension": ".pdf",
                "category": "PDF",
                "size": 500,
                "size_str": "500 B",
                "modified": "2024-06-15 14:30",
                "score": 0.85,
                "highlights": "",
            }
        ]
        self.panel._display_results(results, "q")
        from filepilot.ui.search_panel import QFileDialog

        with patch.object(
            QFileDialog, "getSaveFileName", return_value=(str(export_path), "JSON (*.json)")
        ):
            self.panel._on_export()
        data = eval(export_path.read_text(encoding="utf-8"))
        assert data[0]["name"] == "report.pdf"


class TestBatchOperations:
    """Test search results batch operations — context menu, delete, move, copy, tag."""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot, tmp_path):
        with patch.multiple(
            "filepilot.ui.search_panel",
            FileIndexer=MagicMock(),
            FileScanner=MagicMock(),
            AppState=MagicMock(),
            EventBus=MagicMock(),
        ):
            from filepilot.ui.search_panel import SearchPanel

            self.panel = SearchPanel()
            qtbot.addWidget(self.panel)
            self.src_files = []
            for i in range(3):
                f = tmp_path / f"file{i}.txt"
                f.write_text(f"content {i}")
                self.src_files.append(f)
            # Populate the result list
            results = [
                {
                    "path": str(f),
                    "filename": f.name,
                    "extension": ".txt",
                    "category": "Text",
                    "size": 10,
                    "size_str": "10 B",
                    "modified": "2024-06-15 14:30",
                    "score": 0.9,
                    "highlights": "",
                }
                for f in self.src_files
            ]
            self.panel._display_results(results, "test")
            self.panel.tag_manager = MagicMock()

    def test_get_selected_paths_returns_empty_when_no_selection(self):
        paths = self.panel._get_selected_paths()
        assert paths == []

    def test_get_selected_paths_returns_selected_items(self):
        self.panel.result_list.item(0).setSelected(True)
        self.panel.result_list.item(2).setSelected(True)
        paths = self.panel._get_selected_paths()
        assert len(paths) == 2
        assert paths[0] == str(self.src_files[0])
        assert paths[1] == str(self.src_files[2])

    def test_batch_delete_results(self):
        with (
            patch("filepilot.ui.search_panel.QMessageBox.question", return_value=QMessageBox.Yes),
            patch("filepilot.ui.search_panel.send2trash") as mock_trash,
        ):
            self.panel.result_list.item(0).setSelected(True)
            self.panel.result_list.item(1).setSelected(True)
            self.panel._batch_delete_results()
            assert mock_trash.call_count == 2
            mock_trash.assert_any_call(str(self.src_files[0]))
            mock_trash.assert_any_call(str(self.src_files[1]))

    def test_batch_delete_results_cancelled(self):
        with (
            patch("filepilot.ui.search_panel.QMessageBox.question", return_value=QMessageBox.No),
            patch("filepilot.ui.search_panel.send2trash") as mock_trash,
        ):
            self.panel.result_list.item(0).setSelected(True)
            self.panel._batch_delete_results()
            mock_trash.assert_not_called()

    def test_batch_move_results(self, tmp_path):
        dest = tmp_path / "moved"
        dest.mkdir()
        with patch(
            "filepilot.ui.search_panel.QFileDialog.getExistingDirectory", return_value=str(dest)
        ):
            self.panel.result_list.item(0).setSelected(True)
            self.panel._batch_move_results()
            assert (dest / "file0.txt").exists()
            assert not self.src_files[0].exists()

    def test_batch_copy_results(self, tmp_path):
        dest = tmp_path / "copied"
        dest.mkdir()
        with patch(
            "filepilot.ui.search_panel.QFileDialog.getExistingDirectory", return_value=str(dest)
        ):
            self.panel.result_list.item(0).setSelected(True)
            self.panel._batch_copy_results()
            assert (dest / "file0.txt").exists()
            assert self.src_files[0].exists()  # original untouched

    def test_batch_tag_results(self):
        with patch(
            "filepilot.ui.search_panel.QInputDialog.getText", return_value=("important", True)
        ):
            self.panel.result_list.item(0).setSelected(True)
            self.panel.result_list.item(1).setSelected(True)
            self.panel._batch_tag_results()
            assert self.panel.tag_manager.add_tag.call_count == 2
            self.panel.tag_manager.add_tag.assert_any_call(str(self.src_files[0]), "important")
            self.panel.tag_manager.add_tag.assert_any_call(str(self.src_files[1]), "important")

    def test_batch_tag_results_cancelled(self):
        with patch("filepilot.ui.search_panel.QInputDialog.getText", return_value=("", False)):
            self.panel.result_list.item(0).setSelected(True)
            self.panel._batch_tag_results()
            self.panel.tag_manager.add_tag.assert_not_called()

    def test_remove_paths_from_results(self):
        self.panel._remove_paths_from_results([str(self.src_files[0])])
        assert self.panel.result_list.count() == 2
        assert self.panel.result_list.item(0).data(Qt.UserRole) == str(self.src_files[1])

    def test_open_file_location(self):
        with patch("filepilot.ui.search_panel.QDesktopServices.openUrl") as mock_open:
            self.panel.result_list.item(0).setSelected(True)
            self.panel._open_file_location()
            mock_open.assert_called_once()

    def test_context_menu_has_expected_actions(self):
        menu = self.panel._create_result_context_menu()
        actions = menu.actions()
        texts = [a.text() for a in actions]
        assert "🗑 Send to Trash" in texts
        assert "✂ Move to..." in texts
        assert "📋 Copy to..." in texts
        assert "🏷 Add Tag..." in texts
        assert "📂 Open File Location" in texts
        assert "↩ Undo Move" in texts

    def test_undo_move_action_disabled_initially(self):
        menu = self.panel._create_result_context_menu()
        for a in menu.actions():
            if a.text() == "↩ Undo Move":
                assert not a.isEnabled()
                return

    def test_undo_move_records_and_reverts(self, tmp_path):
        dest = tmp_path / "moved"
        dest.mkdir()
        with patch(
            "filepilot.ui.search_panel.QFileDialog.getExistingDirectory", return_value=str(dest)
        ):
            self.panel.result_list.item(0).setSelected(True)
            self.panel._batch_move_results()
            assert (dest / "file0.txt").exists()
            assert not self.src_files[0].exists()
            assert len(self.panel._batch_undo_log) == 1
            assert self.panel._batch_undo_log[0]["from"] == str(dest / "file0.txt")
            assert self.panel._batch_undo_log[0]["to"] == str(self.src_files[0])

            # Undo
            self.panel._batch_undo_move()
            assert self.src_files[0].exists()
            assert not (dest / "file0.txt").exists()
            assert len(self.panel._batch_undo_log) == 0

    def test_undo_move_nothing_when_empty(self):
        # Should not crash when undo log is empty
        self.panel._batch_undo_move()
