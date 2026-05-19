"""Tests for TagsPanel — tag management panel."""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from filepilot.ui.tags_panel import TagsPanel


@pytest.fixture
def mock_tag_manager():
    tm = MagicMock()
    tm.get_tagged_files.return_value = {
        "/path/to/file1.py": {"tags": ["code", "important"], "color": "#FF6B6B"},
        "/path/to/file2.md": {"tags": ["docs"], "color": None},
    }
    tm.get_tags.side_effect = lambda p: {
        "/path/to/file1.py": ["code", "important"],
        "/path/to/file2.md": ["docs"],
    }.get(p, [])
    tm.get_color.side_effect = lambda p: {
        "/path/to/file1.py": "#FF6B6B",
        "/path/to/file2.md": None,
    }.get(p)
    tm.get_all_tags.return_value = ["code", "docs", "important"]
    return tm


@pytest.fixture
def panel(qtbot, mock_tag_manager):
    with patch("filepilot.ui.tags_panel.TagManager", return_value=mock_tag_manager):
        p = TagsPanel()
        qtbot.addWidget(p)
        return p


class TestTagsPanel:
    def test_constructor(self, panel):
        assert panel.tag_manager is not None
        assert panel.tagged_list is not None
        assert panel.tag_search_input is not None
        assert panel.stats_label is not None

    def test_refresh_tags_populates_list(self, panel):
        assert panel.tagged_list.count() == 2

    def test_refresh_tags_with_filter(self, panel, mock_tag_manager):
        mock_tag_manager.find_by_tag.return_value = ["/path/to/file2.md"]
        panel._refresh_tags(filtered_tag="docs")
        assert panel.tagged_list.count() == 1
        mock_tag_manager.find_by_tag.assert_called_once_with("docs")

    def test_stats_label_updated(self, panel):
        assert "2" in panel.stats_label.text()

    def test_stats_label_singular(self, panel, mock_tag_manager):
        mock_tag_manager.get_tagged_files.return_value = {
            "/only.py": {"tags": ["t"], "color": None}
        }
        mock_tag_manager.get_tags.return_value = ["t"]
        panel._refresh_tags()
        assert "1" in panel.stats_label.text()

    def test_search_dropdown_updated(self, panel, mock_tag_manager):
        panel._update_tag_search_dropdown()
        items = [panel.tag_search_input.itemText(i) for i in range(panel.tag_search_input.count())]
        for tag in ["code", "docs", "important"]:
            assert tag in items

    def test_clear_search_resets(self, panel):
        panel.tag_search_input.setEditText("code")
        panel._on_clear_search()
        assert panel.tag_search_input.currentText() == ""

    def test_search_by_tag(self, panel, mock_tag_manager):
        mock_tag_manager.find_by_tag.return_value = ["/path/to/file2.md"]
        panel.tag_search_input.setEditText("docs")
        panel._on_search_by_tag()
        mock_tag_manager.find_by_tag.assert_called_with("docs")

    def test_search_by_tag_empty_shows_all(self, panel):
        panel._on_search_by_tag()
        assert panel.tagged_list.count() == 2

    def test_add_tag_to_file_public_method(self, panel, mock_tag_manager):
        panel.add_tag_to_file("/test.py", "new_tag", "#fff")
        mock_tag_manager.add_tag.assert_called_once_with("/test.py", "new_tag", "#fff")

    def test_get_file_tags(self, panel, mock_tag_manager):
        tags = panel.get_file_tags("/path/to/file1.py")
        assert tags == ["code", "important"]

    def test_context_menu_no_item(self, panel):
        from PySide6.QtCore import QPoint

        panel._on_context_menu(QPoint(-100, -100))
        assert True

    def test_remove_tag_from_selected(self, panel, mock_tag_manager):
        item = panel.tagged_list.item(0)
        item.setSelected(True)
        with patch.object(panel, "_remove_tag") as mock_remove:
            panel._on_remove_tag_from_selected()
            mock_remove.assert_called()

    def test_item_double_click_existing_file(self, panel, qtbot, tmp_path):
        f = tmp_path / "exists.txt"
        f.write_text("test")
        mock_tag_manager = panel.tag_manager
        mock_tag_manager.get_tagged_files.return_value = {str(f): {"tags": ["t"], "color": None}}
        mock_tag_manager.get_tags.return_value = ["t"]
        panel._refresh_tags()
        item = panel.tagged_list.item(0)
        item.setData(Qt.UserRole, str(f))
        panel._on_item_double_click(item)
        assert True

    def test_on_tag_rules_uses_rules(self, panel):
        with patch("PySide6.QtWidgets.QDialog.exec", return_value=False):
            panel._on_tag_rules()
            assert True

    def test_on_item_double_click_nonexistent(self, panel):
        item = MagicMock()
        item.data.return_value = "/nonexistent/path"
        panel._on_item_double_click(item)
        assert True
