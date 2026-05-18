"""Directory tree widget for file browser."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class DirectoryTreeWidget(QWidget):
    """Directory tree panel with expand/collapse and click-to-navigate."""

    directory_selected = Signal(str)  # emitted when a directory is clicked

    def __init__(self, show_hidden: bool = False, parent=None):
        super().__init__(parent)
        self._show_hidden = show_hidden
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("🗂 Directories"))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name"])
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setRootIsDecorated(True)
        self.tree.header().setStretchLastSection(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree, 1)

    def set_show_hidden(self, show: bool):
        self._show_hidden = show

    def load_directory(self, dir_path: Path):
        """Load directory into tree, clearing existing content."""
        self.tree.clear()
        root = QTreeWidgetItem(self.tree)
        root.setText(0, dir_path.name)
        root.setData(0, Qt.UserRole, str(dir_path))
        root.setExpanded(True)
        self._populate(dir_path, root)

    def _populate(self, dir_path: Path, parent_item: QTreeWidgetItem):
        """Recursively populate children."""
        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries:
                if entry.name.startswith(".") and not self._show_hidden:
                    continue
                if entry.is_dir():
                    child = QTreeWidgetItem(parent_item)
                    child.setText(0, f"📁 {entry.name}")
                    child.setData(0, Qt.UserRole, str(entry))
                    child.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        except PermissionError:
            pass

    def expand_path(self, dir_path: Path):
        """Expand the tree to reveal a path."""
        parts = list(dir_path.parts)
        current = self.tree.invisibleRootItem()
        for _i, part in enumerate(parts):
            found = False
            for j in range(current.childCount()):
                child = current.child(j)
                if child.text(0).lstrip("📁 ") == part:
                    child.setExpanded(True)
                    current = child
                    found = True
                    break
            if not found:
                break

    def clear(self):
        self.tree.clear()

    def set_root_expanded(self, expanded: bool = True):
        if self.tree.topLevelItemCount():
            self.tree.topLevelItem(0).setExpanded(expanded)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Emit directory_selected when a directory item is clicked."""
        dir_path = item.data(0, Qt.UserRole)
        if dir_path and Path(dir_path).is_dir():
            if item.childCount() == 0 and item.data(0, Qt.UserRole):
                self._populate(Path(dir_path), item)
            self.directory_selected.emit(dir_path)
