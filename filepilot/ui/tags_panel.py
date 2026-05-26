"""File Tags panel — manage tags, colors, and cross-directory search."""

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
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

        # Tabs: List view | Tag Cloud
        from PySide6.QtWidgets import QTabWidget

        self._view_tabs = QTabWidget()

        # List view tab
        list_tab = QWidget()
        list_layout = QVBoxLayout(list_tab)
        list_layout.setContentsMargins(0, 0, 0, 0)
        self.tagged_list = QListWidget()
        self.tagged_list.setAlternatingRowColors(True)
        self.tagged_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tagged_list.itemDoubleClicked.connect(self._on_item_double_click)
        list_layout.addWidget(self.tagged_list)
        self._view_tabs.addTab(list_tab, "List View")

        # Tag Cloud tab
        from filepilot.ui.tag_cloud import TagCloudWidget

        self.tag_cloud = TagCloudWidget(tag_manager=self.tag_manager)
        self.tag_cloud.tag_clicked.connect(self._on_cloud_tag_clicked)
        self._view_tabs.addTab(self.tag_cloud, "Tag Cloud")
        self._view_tabs.currentChanged.connect(self._on_view_tab_changed)

        layout.addWidget(self._view_tabs, 1)

        toolbar = QHBoxLayout()
        self.btn_add_tag = QPushButton("\U0001f3f7\ufe0f Add Tag to File...")
        self.btn_remove_tag = QPushButton("\U0001f5d1\ufe0f Remove Tag...")
        self.btn_remove_tag.setEnabled(False)
        toolbar.addWidget(self.btn_add_tag)
        toolbar.addWidget(self.btn_remove_tag)
        toolbar.addStretch()
        self.btn_tag_rules = QPushButton("\U0001f3af Tag Rules...")
        self.btn_tag_rules.clicked.connect(self._on_tag_rules)
        toolbar.addWidget(self.btn_tag_rules)
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
    def _on_cloud_tag_clicked(self, tag: str):
        """Handle tag click from cloud view — filter list by that tag."""
        self.tag_search_input.setEditText(tag)
        self._view_tabs.setCurrentIndex(0)  # Switch to list view
        self._refresh_tags(filtered_tag=tag)

    @Slot()
    def _on_view_tab_changed(self, index: int):
        """Refresh tag cloud when switching to cloud tab."""
        if index == 1:
            self.tag_cloud.refresh()

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

    # ── Tag Automation Rules Dialog ───────────────────────────────────────

    @Slot()
    def _on_tag_rules(self):
        from filepilot.core.tag_rules import get_rules

        rules = get_rules()
        dialog = QDialog(self)
        dialog.setWindowTitle("\U0001f3af Tag Automation Rules")
        dialog.setMinimumSize(500, 350)

        layout = QVBoxLayout(dialog)
        layout.addWidget(
            QLabel("Rules determine which files get auto-tagged based on file properties.")
        )

        rule_list = QListWidget()
        for r in rules:
            cond = r.get("conditions", {})
            parts = []
            exts = cond.get("extensions", [])
            if exts:
                parts.append(", ".join(exts))
            cats = cond.get("categories", [])
            if cats:
                parts.append(f"cat: {', '.join(cats)}")
            ms = cond.get("min_size_mb", 0)
            xs = cond.get("max_size_mb", 0)
            if ms or xs:
                parts.append(f"size: {ms}-{xs} MB")
            age = cond.get("max_age_days", 0)
            if age:
                parts.append(f"age: <{age}d")
            summary = ", ".join(parts) if parts else "all files"
            tags = ", ".join(r.get("tags", []))
            rule_list.addItem(f"{r['name']}  \u2192  [{tags}]  ({summary})")
        layout.addWidget(rule_list, 1)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Rule")
        edit_btn = QPushButton("✏ Edit Rule")
        del_btn = QPushButton("🗑 Delete")
        del_btn.setEnabled(False)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        rule_list.itemSelectionChanged.connect(
            lambda: del_btn.setEnabled(len(rule_list.selectedItems()) > 0)
        )

        def on_add():
            dialog.accept()
            self._edit_rule_dialog(None)

        def on_edit():
            idx = rule_list.currentRow()
            if idx >= 0:
                dialog.accept()
                self._edit_rule_dialog(idx)

        def on_delete():
            idx = rule_list.currentRow()
            if idx >= 0:
                from filepilot.core.tag_rules import delete_rule

                delete_rule(idx)
                self._on_tag_rules()

        add_btn.clicked.connect(on_add)
        edit_btn.clicked.connect(on_edit)
        del_btn.clicked.connect(on_delete)
        dialog.exec()

    def _edit_rule_dialog(self, rule_index: int | None):
        """Show rule editor dialog. If rule_index is None, create new rule."""
        from filepilot.core.tag_rules import add_rule, get_rules, update_rule

        rule = None
        if rule_index is not None:
            rules = get_rules()
            if 0 <= rule_index < len(rules):
                rule = rules[rule_index]

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Rule" if rule else "New Rule")
        dialog.setMinimumSize(400, 300)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g. Large PDFs")
        if rule:
            name_input.setText(rule["name"])
        form.addRow("Name:", name_input)

        ext_input = QLineEdit()
        ext_input.setPlaceholderText(".pdf, .docx, .jpg (comma separated)")
        if rule:
            ext_input.setText(", ".join(rule.get("conditions", {}).get("extensions", [])))
        form.addRow("Extensions:", ext_input)

        cat_input = QLineEdit()
        cat_input.setPlaceholderText("PDF, Code, Image, Office (comma separated)")
        if rule:
            cat_input.setText(", ".join(rule.get("conditions", {}).get("categories", [])))
        form.addRow("Categories:", cat_input)

        min_size_input = QSpinBox()
        min_size_input.setRange(0, 99999)
        min_size_input.setSuffix(" MB")
        if rule:
            min_size_input.setValue(rule.get("conditions", {}).get("min_size_mb", 0))
        form.addRow("Min size:", min_size_input)

        max_size_input = QSpinBox()
        max_size_input.setRange(0, 99999)
        max_size_input.setSuffix(" MB")
        if rule:
            max_size_input.setValue(rule.get("conditions", {}).get("max_size_mb", 0))
        form.addRow("Max size:", max_size_input)

        age_input = QSpinBox()
        age_input.setRange(0, 9999)
        age_input.setSuffix(" days")
        age_input.setSpecialValueText("any")
        if rule:
            age_input.setValue(rule.get("conditions", {}).get("max_age_days", 0))
        form.addRow("Max age:", age_input)

        tag_input = QLineEdit()
        tag_input.setPlaceholderText("important, archive, review (comma separated)")
        if rule:
            tag_input.setText(", ".join(rule.get("tags", [])))
        form.addRow("Tags to apply:", tag_input)

        layout.addLayout(form)
        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        name = name_input.text().strip()
        if not name:
            return

        conditions: dict[str, list[str] | int] = {}
        exts = [e.strip() for e in ext_input.text().split(",") if e.strip()]
        if exts:
            conditions["extensions"] = exts
        cats = [c.strip() for c in cat_input.text().split(",") if c.strip()]
        if cats:
            conditions["categories"] = cats
        if min_size_input.value() > 0:
            conditions["min_size_mb"] = min_size_input.value()
        if max_size_input.value() > 0:
            conditions["max_size_mb"] = max_size_input.value()
        if age_input.value() > 0:
            conditions["max_age_days"] = age_input.value()

        tags = [t.strip() for t in tag_input.text().split(",") if t.strip()]
        if not tags:
            return

        if rule_index is None:
            add_rule(name, conditions, tags)
        else:
            update_rule(rule_index, name, conditions, tags)

        self._refresh_tags()
        self.status_message.emit(f"Rule saved: {name}")
