"""File Tags panel — manage tags, colors, and cross-directory search."""

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from filepilot.core.tag_manager import TagManager
from filepilot.ui.base_panel import BasePanel


class TagsPanel(BasePanel):
    """File Tags panel — manage tags, colors, and cross-directory search."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tag_manager = TagManager()
        self._setup_ui()
        self._connect_signals()
        self._refresh_tags()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("\U0001f3f7\ufe0f File Tags")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel(
            "Add custom tags and color markers to files. Search across directories by tag name."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 8px;")
        layout.addWidget(desc)

        search_layout = QHBoxLayout()
        self.tag_search_input = QComboBox()
        self.tag_search_input.setEditable(True)
        self.tag_search_input.setInsertPolicy(QComboBox.NoInsert)
        self.tag_search_input.setPlaceholderText("Search files by tag...")
        search_layout.addWidget(self.tag_search_input, 1)

        self.btn_search_tag = QPushButton("\U0001f50d Search")
        self.btn_search_tag.clicked.connect(self._on_search_by_tag)
        search_layout.addWidget(self.btn_search_tag)

        self.btn_clear_search = QPushButton("Clear")
        self.btn_clear_search.clicked.connect(self._on_clear_search)
        search_layout.addWidget(self.btn_clear_search)

        layout.addLayout(search_layout)

        self.tagged_list = QListWidget()
        self.tagged_list.setAlternatingRowColors(True)
        self.tagged_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tagged_list.itemDoubleClicked.connect(self._on_item_double_click)
        layout.addWidget(self.tagged_list, 1)

        toolbar = QHBoxLayout()
        self.btn_add_tag = QPushButton("\U0001f3f7\ufe0f Add Tag to File...")
        self.btn_remove_tag = QPushButton("\U0001f5d1\ufe0f Remove Tag...")
        self.btn_remove_tag.setEnabled(False)
        toolbar.addWidget(self.btn_add_tag)
        toolbar.addWidget(self.btn_remove_tag)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.stats_label = QLabel("0 tagged files")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.tagged_list.customContextMenuRequested.connect(self._on_context_menu)
        self.tagged_list.itemSelectionChanged.connect(
            lambda: self.btn_remove_tag.setEnabled(len(self.tagged_list.selectedItems()) > 0)
        )
        self.tagged_list.itemClicked.connect(self._on_item_double_click)
        self.btn_add_tag.clicked.connect(self._on_add_tag_to_file)
        self.btn_remove_tag.clicked.connect(self._on_remove_tag_from_selected)

    def _refresh_tags(self, filtered_tag: str | None = None):
        """Refresh the tagged files list, optionally filtered by tag."""
        self.tagged_list.clear()

        if filtered_tag:
            files = self.tag_manager.find_by_tag(filtered_tag)
        else:
            files = list(self.tag_manager.get_tagged_files().keys())

        for path_str in sorted(files):
            path = Path(path_str)
            tags = self.tag_manager.get_tags(path_str)
            color = self.tag_manager.get_color(path_str) or "#888"
            tag_str = ", ".join(tags[:3])
            if len(tags) > 3:
                tag_str += f" +{len(tags) - 3} more"
            item = QListWidgetItem(f"\U0001f4c1 {path.name}")
            item.setToolTip(f"{path_str}\nTags: {tag_str}")
            item.setData(Qt.UserRole, path_str)
            item.setForeground(QColor(color))
            self.tagged_list.addItem(item)

        total = len(files)
        self.stats_label.setText(f"{total} tagged file{'s' if total != 1 else ''}")
        self._update_tag_search_dropdown()

    def _update_tag_search_dropdown(self):
        current = self.tag_search_input.currentText()
        self.tag_search_input.clear()
        for tag in self.tag_manager.get_all_tags():
            self.tag_search_input.addItem(tag)
        if current:
            self.tag_search_input.setEditText(current)

    @Slot()
    def _on_search_by_tag(self):
        tag = self.tag_search_input.currentText().strip()
        if tag:
            self._refresh_tags(filtered_tag=tag)
        else:
            self._refresh_tags()

    @Slot()
    def _on_clear_search(self):
        self.tag_search_input.setEditText("")
        self._refresh_tags()

    @Slot()
    def _on_context_menu(self, pos):
        item = self.tagged_list.itemAt(pos)
        if not item:
            return
        path_str = item.data(Qt.UserRole)
        if not path_str:
            return

        menu = QMenu(self)
        add_action = menu.addAction("\U0001f3f7\ufe0f Add Tag...")
        remove_action = menu.addAction("\U0001f5d1\ufe0f Remove Tag...")
        color_action = menu.addAction("\U0001f3a8 Change Color...")
        clear_action = menu.addAction("\u274c Remove All Tags")
        action = menu.exec(self.tagged_list.viewport().mapToGlobal(pos))

        if action == add_action:
            self._add_tag(path_str)
        elif action == remove_action:
            self._remove_tag(path_str)
        elif action == color_action:
            self._change_color(path_str)
        elif action == clear_action:
            self.tag_manager.remove_file(path_str)
            self._refresh_tags()
            self.status_message.emit(f"Removed all tags from {Path(path_str).name}")

    def _add_tag(self, path_str: str):
        tag, ok = QInputDialog.getText(self, "Add Tag", "Enter tag name:")
        if ok and tag.strip():
            self.tag_manager.add_tag(path_str, tag.strip())
            self._refresh_tags()
            self.status_message.emit(f"Added tag '{tag.strip()}' to {Path(path_str).name}")

    def _remove_tag(self, path_str: str):
        tags = self.tag_manager.get_tags(path_str)
        if not tags:
            return
        tag, ok = QInputDialog.getItem(self, "Remove Tag", "Select tag:", tags)
        if ok and tag:
            self.tag_manager.remove_tag(path_str, tag)
            self._refresh_tags()
            self.status_message.emit(f"Removed tag '{tag}' from {Path(path_str).name}")

    def _change_color(self, path_str: str):
        from PySide6.QtWidgets import QColorDialog

        current = self.tag_manager.get_color(path_str) or "#888"
        qcolor = QColorDialog.getColor(QColor(current), self, "Pick a color")
        if qcolor.isValid():
            self.tag_manager.set_color(path_str, qcolor.name())
            self._refresh_tags()
            self.status_message.emit(f"Changed color for {Path(path_str).name}")

    @Slot()
    def _on_add_tag_to_file(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "Select File to Tag")
        if path:
            self._add_tag(path)

    @Slot()
    def _on_remove_tag_from_selected(self):
        items = self.tagged_list.selectedItems()
        if not items:
            return
        for item in items:
            path_str = item.data(Qt.UserRole)
            if path_str:
                tags = self.tag_manager.get_tags(path_str)
                if len(tags) == 1:
                    self.tag_manager.remove_file(path_str)
                else:
                    self._remove_tag(path_str)
        self._refresh_tags()

    @Slot()
    def _on_item_double_click(self, item):
        path_str = item.data(Qt.UserRole)
        if path_str and Path(path_str).exists():
            self.status_message.emit(f"File: {Path(path_str).name}")
        elif path_str:
            self.status_message.emit("File no longer exists")

    def add_tag_to_file(self, file_path: str | Path, tag: str, color: str | None = None):
        self.tag_manager.add_tag(file_path, tag, color)
        self._refresh_tags()

    def get_file_tags(self, file_path: str | Path) -> list[str]:
        return list(self.tag_manager.get_tags(file_path))
