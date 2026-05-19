"""Tests for DirectoryTreeWidget — directory tree with expand/collapse."""

import pytest
from PySide6.QtCore import Qt

from filepilot.ui.directory_tree import DirectoryTreeWidget


class TestDirectoryTreeWidget:
    def test_constructor_defaults(self, qtbot):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        assert tree._show_hidden is False
        assert tree.tree is not None
        assert tree.tree.columnCount() >= 1

    def test_constructor_with_show_hidden(self, qtbot):
        tree = DirectoryTreeWidget(show_hidden=True)
        qtbot.addWidget(tree)
        assert tree._show_hidden is True

    def test_set_show_hidden(self, qtbot):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.set_show_hidden(True)
        assert tree._show_hidden is True
        tree.set_show_hidden(False)
        assert tree._show_hidden is False

    def test_load_directory_creates_root_item(self, qtbot, tmp_path):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        assert tree.tree.topLevelItemCount() == 1
        item = tree.tree.topLevelItem(0)
        assert item.text(0) == tmp_path.name
        assert item.data(0, Qt.UserRole) == str(tmp_path)
        assert item.isExpanded()

    def test_load_directory_clears_existing(self, qtbot, tmp_path):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        tree.load_directory(tmp_path)
        assert tree.tree.topLevelItemCount() == 1

    def test_populate_shows_dirs(self, qtbot, tmp_path):
        (tmp_path / "subdir").mkdir()
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        root = tree.tree.topLevelItem(0)
        assert root.childCount() == 1
        child = root.child(0)
        assert "subdir" in child.text(0)

    def test_populate_hides_dot_dirs(self, qtbot, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / "visible").mkdir()
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        root = tree.tree.topLevelItem(0)
        for i in range(root.childCount()):
            assert not root.child(i).text(0).startswith("📁 .")

    def test_populate_shows_dot_dirs_when_hidden_enabled(self, qtbot, tmp_path):
        (tmp_path / ".hidden").mkdir()
        tree = DirectoryTreeWidget(show_hidden=True)
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        root = tree.tree.topLevelItem(0)
        found_hidden = any(".hidden" in root.child(i).text(0) for i in range(root.childCount()))
        assert found_hidden

    def test_clear_removes_all(self, qtbot, tmp_path):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        tree.clear()
        assert tree.tree.topLevelItemCount() == 0

    def test_set_root_expanded(self, qtbot, tmp_path):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        tree.set_root_expanded(False)
        assert not tree.tree.topLevelItem(0).isExpanded()
        tree.set_root_expanded(True)
        assert tree.tree.topLevelItem(0).isExpanded()

    def test_set_root_expanded_no_items(self, qtbot):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.set_root_expanded()
        assert True

    def test_on_item_clicked_emits_directory_selected(self, qtbot, tmp_path):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        root = tree.tree.topLevelItem(0)
        with qtbot.waitSignal(tree.directory_selected) as blocker:
            tree._on_item_clicked(root, 0)
        assert blocker.args == [str(tmp_path)]

    def test_on_item_clicked_populates_empty_dir(self, qtbot, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        root = tree.tree.topLevelItem(0)
        child = root.child(0)
        assert child.childCount() == 0
        tree._on_item_clicked(child, 0)
        assert child.childCount() == 0  # empty dir has no children

    def test_on_item_clicked_sorts_dirs_first(self, qtbot, tmp_path):
        (tmp_path / "b_dir").mkdir()
        (tmp_path / "a_dir").mkdir()
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        root = tree.tree.topLevelItem(0)
        for i in range(1, root.childCount()):
            assert root.child(i - 1).text(0) <= root.child(i).text(0)

    def test_expand_path(self, qtbot, tmp_path):
        sub = tmp_path / "a" / "b" / "c"
        sub.mkdir(parents=True)
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        tree.expand_path(sub)
        root = tree.tree.topLevelItem(0)
        assert root.isExpanded()

    def test_expand_path_not_found(self, qtbot, tmp_path):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        tree.load_directory(tmp_path)
        tree.expand_path(tmp_path / "nonexistent")
        assert True

    def test_permission_error_handled(self, qtbot, tmp_path):
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        restricted.chmod(0o000)
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        try:
            tree.load_directory(tmp_path)
        except PermissionError:
            pytest.fail("PermissionError was not caught")
        finally:
            restricted.chmod(0o755)

    def test_signal_directory_selected_type(self, qtbot, tmp_path):
        tree = DirectoryTreeWidget()
        qtbot.addWidget(tree)
        assert tree.directory_selected is not None
