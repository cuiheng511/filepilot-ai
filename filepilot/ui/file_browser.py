"""File browser panel — directory tree, file list, and preview"""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.tag_manager import TagManager
from filepilot.ui.base_panel import BasePanel
from filepilot.ui.directory_tree import DirectoryTreeWidget
from filepilot.ui.preview_panel import PreviewPanel
from filepilot.utils.file_utils import (
    CATEGORY_ICONS,
    get_category_name,
    get_file_size_str,
)

COLUMN_DEFS = {
    "name": ("Name", QHeaderView.Stretch),
    "size": ("Size", QHeaderView.ResizeToContents),
    "type": ("Type", QHeaderView.ResizeToContents),
    "modified": ("Modified", QHeaderView.Interactive),
    "created": ("Created", QHeaderView.Interactive),
    "path": ("Path", QHeaderView.Stretch),
    "extension": ("Ext", QHeaderView.ResizeToContents),
    "tags": ("Tags", QHeaderView.ResizeToContents),
}

DEFAULT_COLUMNS = ["name", "size", "type", "modified", "path", "tags"]


class FileBrowserPanel(BasePanel):
    """File browser panel — browse, scan, preview files"""

    file_opened = Signal(str)  # Emitted when a file is opened (double-click)
    batch_files_ready = Signal(list)  # Emitted during scan with batches of FileInfo
    scan_completed = Signal(str)  # Emitted when a full scan finishes

    def __init__(
        self,
        scanner: FileScanner | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.scanner = scanner or FileScanner()
        self.state = app_state
        self.event_bus = event_bus
        self.current_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.categories: dict[str, list[FileInfo]] = {}
        self.tag_manager = TagManager()
        self._column_keys: list[str] = []
        self._col_index: dict[str, int] = {}

        self._setup_ui()
        self._connect_signals()
        self._load_column_config()

    def update_services(
        self,
        scanner: FileScanner | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
    ):
        """Update service references without recreating the panel"""
        if scanner is not None:
            self.scanner = scanner
        if app_state is not None:
            self.state = app_state
        if event_bus is not None:
            self.event_bus = event_bus

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._create_header(layout)
        self._create_toolbar(layout)
        self._create_progress_bar(layout)
        self._create_splitter(layout)
        self._create_stats_bar(layout)
        self._create_status_label(layout)

    def _create_header(self, layout):
        header_layout = QHBoxLayout()
        title = QLabel("📂 File Browser")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.dir_label = QLabel("No folder opened")
        self.dir_label.setObjectName("statusLabel")
        header_layout.addWidget(self.dir_label)
        layout.addLayout(header_layout)
        desc = QLabel(
            "Browse files, preview content, and manage your folders. "
            "Drag and drop folders to open them.",
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

    def _create_toolbar(self, layout):
        toolbar_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self._on_refresh)
        self.btn_refresh.setEnabled(False)
        toolbar_layout.addWidget(self.btn_refresh)
        self.btn_export = QPushButton("📤 Export")
        self.btn_export.clicked.connect(self._on_export)
        self.btn_export.setEnabled(False)
        toolbar_layout.addWidget(self.btn_export)
        self.btn_actions = QPushButton("⚡ Actions")
        self.btn_actions.setEnabled(False)
        self.actions_menu = QMenu(self)
        self.actions_menu.addAction("📋 Copy", self._batch_copy)
        self.actions_menu.addAction("✂ Move", self._batch_move)
        self.actions_menu.addAction("🗑 Delete", self._batch_delete)
        self.btn_actions.setMenu(self.actions_menu)
        toolbar_layout.addWidget(self.btn_actions)
        toolbar_layout.addStretch()
        self.btn_columns = QPushButton("📋 Columns")
        self.btn_columns.clicked.connect(self._on_show_column_menu)
        toolbar_layout.addWidget(self.btn_columns)
        self.cb_show_hidden = QCheckBox("Show hidden files")
        self.cb_show_hidden.stateChanged.connect(self._on_refresh)
        toolbar_layout.addWidget(self.cb_show_hidden)
        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.setObjectName("btnDanger")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        toolbar_layout.addWidget(self.btn_cancel)
        layout.addLayout(toolbar_layout)

    def _create_progress_bar(self, layout):
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def _create_splitter(self, layout):
        main_splitter = QSplitter(Qt.Horizontal)
        self.dir_tree = DirectoryTreeWidget(show_hidden=self.cb_show_hidden.isChecked())
        self.dir_tree.directory_selected.connect(self._on_dir_selected)
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.addWidget(QLabel("📄 Files"))
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(0)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSortingEnabled(True)
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._on_file_context_menu)
        self.file_table.itemSelectionChanged.connect(self._on_file_selected)
        self.file_table.cellDoubleClicked.connect(self._on_file_double_click)
        file_layout.addWidget(self.file_table, 1)
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(QLabel("👁 Preview"))
        self.preview_panel = PreviewPanel()
        preview_layout.addWidget(self.preview_panel, 1)
        main_splitter.addWidget(self.dir_tree)
        main_splitter.addWidget(file_widget)
        main_splitter.addWidget(preview_widget)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(2, 2)
        main_splitter.setSizes([250, 500, 350])
        layout.addWidget(main_splitter, 1)

    def _create_stats_bar(self, layout):
        stats_layout = QHBoxLayout()
        self.stat_total = self._make_stat_card("📊 Total Files", "0")
        self.stat_categories = {}
        stats_layout.addWidget(self.stat_total)
        layout.addLayout(stats_layout)
        self.stats_container = stats_layout

    def _create_status_label(self, layout):
        self.stats_label = QLabel("Open a folder to start browsing")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)
        self.batch_files_ready.connect(self._append_files_batch)
        self.scan_completed.connect(self._on_scan_completed)

    def _on_scan_completed(self, _dir_path: str):
        self._finalize_scan(self.files)

    def load_directory(self, dir_path: str | Path):
        """Load a directory into the tree"""
        self.current_dir = Path(dir_path)
        self.dir_label.setText(f"📂 {dir_path}")
        self.dir_tree.load_directory(self.current_dir)
        self.btn_refresh.setEnabled(True)
        self.scan_directory(self.current_dir)

    def scan_directory(self, dir_path: str | Path):
        """Scan directory and populate file list"""
        self._cancelled = False
        self._cancelling = False
        self.btn_refresh.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.btn_actions.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel.setVisible(True)
        self.status_message.emit("Scanning files...")
        self.file_table.setRowCount(0)
        self.files = []
        self.categories = {}

        batch_size = 100

        def scan_worker():
            files = []
            batch = []

            for f in self.scanner.scan(
                str(dir_path),
                progress_callback=lambda i, p: self.progress_updated.emit(i % 100),
            ):
                if self._cancelled:
                    return
                files.append(f)
                batch.append(f)
                if len(batch) >= batch_size:
                    try:
                        self.batch_files_ready.emit(batch)
                    except RuntimeError:
                        return
                    batch = []

            if self._cancelled:
                return

            if batch:
                try:
                    self.batch_files_ready.emit(batch)
                except RuntimeError:
                    return

            try:
                self.files = files
                self.categories = self._categorize_files(files)
            except RuntimeError:
                return

            if not self._cancelled:
                try:
                    self.scan_completed.emit(str(dir_path))
                except RuntimeError:
                    return

        Thread(target=scan_worker, daemon=True).start()

    def _append_files_batch(self, batch: list[FileInfo]):
        """Append a batch of files to the table (incremental)."""
        if not batch:
            return
        hidden = self.cb_show_hidden.isChecked()
        filtered = [f for f in batch if hidden or not f.name.startswith(".")]
        if not filtered:
            return

        self.file_table.setSortingEnabled(False)
        start_row = self.file_table.rowCount()
        self.file_table.setRowCount(start_row + len(filtered))

        for row_offset, f in enumerate(filtered):
            row = start_row + row_offset
            cat = get_category_name(f.path.suffix.lower())
            icon = CATEGORY_ICONS.get(cat, "📁")

            for col, key in enumerate(self._column_keys):
                if key == "name":
                    item = QTableWidgetItem(f"{icon}  {f.name}")
                    item.setData(Qt.UserRole, str(f.path))
                elif key == "size":
                    item = QTableWidgetItem(f.size_str)
                elif key == "type":
                    item = QTableWidgetItem(cat)
                elif key == "modified":
                    item = QTableWidgetItem(f.modified_time.strftime("%Y-%m-%d %H:%M"))
                elif key == "created":
                    created = getattr(f, "created_time", None)
                    item = QTableWidgetItem(created.strftime("%Y-%m-%d %H:%M") if created else "-")
                elif key == "path":
                    item = QTableWidgetItem(str(f.path))
                elif key == "extension":
                    item = QTableWidgetItem(f.extension.lower())
                elif key == "tags":
                    tags = self.tag_manager.get_tags(f.path)
                    tag_display = ", ".join(tags[:3]) if tags else ""
                    item = QTableWidgetItem(tag_display)
                    item.setToolTip("Tags: " + ", ".join(tags) if tags else "No tags")
                    if tags:
                        color = self.tag_manager.get_color(f.path)
                        if color:
                            item.setForeground(QColor(color))
                else:
                    item = QTableWidgetItem("")

                self.file_table.setItem(row, col, item)

        self.file_table.setSortingEnabled(True)
        self._update_stat("📊 Total Files", str(self.file_table.rowCount()))

    def _redisplay_files(self):
        """Rebuild the table from self.files (for column toggle, refresh, etc.)."""
        if not self.files:
            return
        self.file_table.setRowCount(0)
        self.file_table.setSortingEnabled(False)

        hidden = self.cb_show_hidden.isChecked()
        filtered = [f for f in self.files if hidden or not f.name.startswith(".")]
        self.file_table.setRowCount(len(filtered))

        for row, f in enumerate(filtered):
            cat = get_category_name(f.path.suffix.lower())
            icon = CATEGORY_ICONS.get(cat, "📁")

            for col, key in enumerate(self._column_keys):
                if key == "name":
                    item = QTableWidgetItem(f"{icon}  {f.name}")
                    item.setData(Qt.UserRole, str(f.path))
                elif key == "size":
                    item = QTableWidgetItem(f.size_str)
                elif key == "type":
                    item = QTableWidgetItem(cat)
                elif key == "modified":
                    item = QTableWidgetItem(f.modified_time.strftime("%Y-%m-%d %H:%M"))
                elif key == "created":
                    created = getattr(f, "created_time", None)
                    item = QTableWidgetItem(created.strftime("%Y-%m-%d %H:%M") if created else "-")
                elif key == "path":
                    item = QTableWidgetItem(str(f.path))
                elif key == "extension":
                    item = QTableWidgetItem(f.extension.lower())
                elif key == "tags":
                    tags = self.tag_manager.get_tags(f.path)
                    tag_display = ", ".join(tags[:3]) if tags else ""
                    item = QTableWidgetItem(tag_display)
                    item.setToolTip("Tags: " + ", ".join(tags) if tags else "No tags")
                    if tags:
                        color = self.tag_manager.get_color(f.path)
                        if color:
                            item.setForeground(QColor(color))
                else:
                    item = QTableWidgetItem("")

                self.file_table.setItem(row, col, item)

        self.file_table.setSortingEnabled(True)
        self._update_stat("📊 Total Files", str(len(filtered)))

    def _categorize_files(self, files: list[FileInfo]) -> dict[str, list[FileInfo]]:
        """Categorize files by type"""
        categories: dict[str, list[FileInfo]] = {}
        for f in files:
            cat = get_category_name(f.path.suffix.lower())
            categories.setdefault(cat, []).append(f)
        return categories

    @Slot()
    def _finalize_scan(self, files: list[FileInfo]):
        """Finalize scan — update stats, re-enable buttons."""
        self.file_table.setSortingEnabled(False)
        self.file_table.setSortingEnabled(True)

        # Category stats
        for cat in self.categories:
            cat_count = len(self.categories[cat])
            cat_size = sum(f.size_bytes for f in self.categories[cat])
            card_key = f"📁 {cat}"
            if card_key not in self.stat_cards:
                card = self._make_stat_card(card_key, f"{cat_count} files")
                self.stats_container.addWidget(card)
            self._update_stat(card_key, f"{cat_count} files ({get_file_size_str(cat_size)})")

        self.btn_refresh.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.btn_actions.setEnabled(True)

        total_size = sum(f.size_bytes for f in files)
        size_str = get_file_size_str(total_size)
        self.status_message.emit(f"✅ Scanned {len(files)} files ({size_str})")

        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)

    def _on_dir_selected(self, dir_path: str):
        """Handle directory selection from DirectoryTreeWidget"""
        path = Path(dir_path)
        if path.is_dir():
            self.current_dir = path
            self.dir_label.setText(f"📂 {dir_path}")
            self.scan_directory(path)

    @Slot()
    def _on_refresh(self):
        """Refresh current directory"""
        if self.current_dir:
            self.scan_directory(self.current_dir)

    @Slot()
    def _on_cancel(self):
        """Cancel scanning"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.status_message.emit("⏹️ Scan cancelled")

    @Slot()
    def _on_file_selected(self):
        """Handle file selection change — show preview, enable batch buttons"""
        selected = self.file_table.selectedItems()
        selected_rows = set()
        for item in selected:
            selected_rows.add(item.row())
        has_selection = len(selected_rows) > 0
        self.btn_actions.setEnabled(has_selection)

        if not selected:
            return

        row = selected[0].row()
        path_item = self.file_table.item(row, 0)
        if not path_item:
            return

        file_path = path_item.data(Qt.UserRole)
        if not file_path:
            return

        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return

        self.preview_panel.show_preview(path)

    # ── File Comparison ───────────────────────────────────────────────────

    @Slot()
    def _compare_files(self):
        """Open file comparison dialog for two selected files."""
        paths = self._get_selected_paths()
        if len(paths) < 2:
            self.status_message.emit("Select at least 2 files to compare")
            return
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QPushButton,
            QSplitter,
            QVBoxLayout,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle(f"📊 Compare: {paths[0].name} vs {paths[1].name}")
        dialog.setMinimumSize(800, 500)

        layout = QVBoxLayout(dialog)
        splitter = QSplitter(Qt.Horizontal)

        left = QTextEdit()
        left.setReadOnly(True)
        right = QTextEdit()
        right.setReadOnly(True)

        for p, widget in [(paths[0], left), (paths[1], right)]:
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                widget.setPlainText(text)
            except Exception:
                widget.setPlainText(f"[Cannot read {p.name}]")

        splitter.addWidget(left)
        splitter.addWidget(right)

        import difflib

        try:
            lines_a = paths[0].read_text(encoding="utf-8", errors="replace").splitlines()
            lines_b = paths[1].read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            lines_a, lines_b = [], []

        diff = list(
            difflib.unified_diff(
                lines_a, lines_b, fromfile=paths[0].name, tofile=paths[1].name, lineterm=""
            )
        )
        difflines = [line for line in diff if line.startswith("+") or line.startswith("-")]
        stats = (
            f"  Added: {sum(1 for line in difflines if line.startswith('+'))}  "
            f"Removed: {sum(1 for line in difflines if line.startswith('-'))}  "
            f"Total diff lines: {len(difflines)}"
        )

        btn_layout = QHBoxLayout()
        stats_label = QLabel(stats)
        btn_layout.addWidget(stats_label)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)

        layout.addWidget(splitter)
        layout.addLayout(btn_layout)
        dialog.exec()

    # ── Tag Automation ────────────────────────────────────────────────────

    @Slot()
    def _apply_auto_tags(self):
        """Apply auto-tag rules to selected files."""
        from filepilot.core.tag_rules import apply_rules_to_files

        paths = self._get_selected_paths()
        if not paths:
            self.status_message.emit("No files selected")
            return
        count = apply_rules_to_files(paths)
        self._refresh_tag_column()
        self.status_message.emit(f"Applied auto-tags to {count} file{'s' if count != 1 else ''}")

    @Slot()
    def _on_file_context_menu(self, pos):
        item = self.file_table.itemAt(pos)
        if not item:
            return
        row = item.row()
        path_item = self.file_table.item(row, 0)
        if not path_item:
            return
        file_path = path_item.data(Qt.UserRole)
        if not file_path:
            return

        menu = QMenu(self)
        menu.addAction("\U0001f3f7\ufe0f Add Tag...")
        menu.addAction("\U0001f5d1\ufe0f Remove Tag...")
        menu.addAction("\U0001f3a8 Change Color...")
        menu.addAction("\u274c Remove All Tags")
        menu.addSeparator()
        menu.addAction("\U0001f3af Apply Auto-Tags")
        menu.addAction("\U0001f4ca Compare Files...")
        action = menu.exec(self.file_table.viewport().mapToGlobal(pos))
        if action is None:
            return

        text = action.text()
        if "Add Tag" in text:
            tag, ok = QInputDialog.getText(self, "Add Tag", "Enter tag name:")
            if ok and tag.strip():
                self.tag_manager.add_tag(file_path, tag.strip())
                self._refresh_tag_column()
                self.status_message.emit(f"Added tag '{tag.strip()}' to {Path(file_path).name}")
        elif "Remove Tag" in text:
            tags = self.tag_manager.get_tags(file_path)
            if tags:
                tag, ok = QInputDialog.getItem(self, "Remove Tag", "Select tag:", tags)
                if ok and tag:
                    self.tag_manager.remove_tag(file_path, tag)
                    self._refresh_tag_column()
                    self.status_message.emit(f"Removed tag '{tag}' from {Path(file_path).name}")
        elif "Change Color" in text:
            from PySide6.QtWidgets import QColorDialog

            current = self.tag_manager.get_color(file_path) or "#888"
            qcolor = QColorDialog.getColor(QColor(current), self, "Pick a color")
            if qcolor.isValid():
                self.tag_manager.set_color(file_path, qcolor.name())
                self._refresh_tag_column()
                self.status_message.emit(f"Changed color for {Path(file_path).name}")
        elif "Remove All Tags" in text:
            self.tag_manager.remove_file(file_path)
            self._refresh_tag_column()
            self.status_message.emit(f"Removed all tags from {Path(file_path).name}")
        elif "Auto-Tags" in text:
            self._apply_auto_tags()
        elif "Compare" in text:
            self._compare_files()

    def _get_selected_paths(self) -> list[Path]:
        """Get list of Path objects for selected rows."""
        paths: list[Path] = []
        seen = set()
        for item in self.file_table.selectedItems():
            row = item.row()
            if row in seen:
                continue
            seen.add(row)
            path_item = self.file_table.item(row, 0)
            if path_item:
                fp = path_item.data(Qt.UserRole)
                if fp and Path(fp).exists():
                    paths.append(Path(fp))
        return paths

    @Slot()
    def _batch_copy(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        dest = QFileDialog.getExistingDirectory(self, "Copy to...")
        if not dest:
            return
        dest_path = Path(dest)
        import shutil

        copied = 0
        for p in paths:
            try:
                shutil.copy2(p, dest_path / p.name)
                copied += 1
            except Exception as e:
                self.status_message.emit(f"❌ Failed to copy {p.name}: {e}")
                return
        self.status_message.emit(
            f"✅ Copied {copied} file{'s' if copied != 1 else ''} to {dest_path.name}"
        )

    @Slot()
    def _batch_move(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        dest = QFileDialog.getExistingDirectory(self, "Move to...")
        if not dest:
            return
        dest_path = Path(dest)
        import shutil

        moved = 0
        for p in paths:
            try:
                shutil.move(str(p), str(dest_path / p.name))
                moved += 1
            except Exception as e:
                self.status_message.emit(f"❌ Failed to move {p.name}: {e}")
                return
        self.status_message.emit(
            f"✅ Moved {moved} file{'s' if moved != 1 else ''} to {dest_path.name}"
        )
        self.scan_directory(self.current_dir)

    @Slot()
    def _batch_delete(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete {len(paths)} file{'s' if len(paths) != 1 else ''}? (moves to Recycle Bin)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        from send2trash import send2trash

        deleted = 0
        for p in paths:
            try:
                send2trash(str(p))
                deleted += 1
            except Exception as e:
                self.status_message.emit(f"❌ Failed to delete {p.name}: {e}")
                return
        self.status_message.emit(f"🗑 Deleted {deleted} file{'s' if deleted != 1 else ''}")
        self.scan_directory(self.current_dir)

    def _refresh_tag_column(self):
        """Refresh tags column without re-scanning."""
        tag_col = self._col_index.get("tags")
        if tag_col is None:
            return
        for row in range(self.file_table.rowCount()):
            path_item = self.file_table.item(row, 0)
            if path_item:
                fp = path_item.data(Qt.UserRole)
                if fp:
                    tags = self.tag_manager.get_tags(fp)
                    tag_item = self.file_table.item(row, tag_col)
                    tag_display = ", ".join(tags[:3]) if tags else ""
                    if tag_item:
                        tag_item.setText(tag_display)
                        tag_item.setToolTip("Tags: " + ", ".join(tags) if tags else "No tags")
                        if tags:
                            color = self.tag_manager.get_color(fp)
                            tag_item.setForeground(QColor(color) if color else QColor("#888"))
                        else:
                            tag_item.setForeground(QColor("#888"))

    def _load_column_config(self):
        if self.state:
            keys = self.state.file_browser_columns
        else:
            from filepilot.core import config as _cfg

            keys = _cfg.load().get("file_browser_columns", DEFAULT_COLUMNS)
        self._column_keys = [k for k in keys if k in COLUMN_DEFS] or list(DEFAULT_COLUMNS)
        if "name" not in self._column_keys:
            self._column_keys.insert(0, "name")
        self._rebuild_column_headers()

    def _rebuild_column_headers(self):
        self._col_index = {k: i for i, k in enumerate(self._column_keys)}
        labels = [COLUMN_DEFS[k][0] for k in self._column_keys]
        self.file_table.setColumnCount(len(labels))
        self.file_table.setHorizontalHeaderLabels(labels)
        for i, k in enumerate(self._column_keys):
            self.file_table.horizontalHeader().setSectionResizeMode(i, COLUMN_DEFS[k][1])

    def _save_column_config(self):
        if self.state:
            self.state.set_file_browser_columns(list(self._column_keys))
        else:
            from filepilot.core import config as _cfg

            s = _cfg.load()
            s["file_browser_columns"] = list(self._column_keys)
            _cfg.save(s)

    @Slot()
    def _on_show_column_menu(self):
        menu = QMenu(self)
        actions = {}
        for key, (label, _) in COLUMN_DEFS.items():
            if key == "name":
                continue
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(key in self._column_keys)
            actions[key] = action

        chosen = menu.exec(self.btn_columns.mapToGlobal(self.btn_columns.rect().bottomLeft()))
        if chosen is None:
            return

        toggled_key = None
        for key, action in actions.items():
            if action == chosen:
                toggled_key = key
                break

        if toggled_key is None:
            return

        if toggled_key in self._column_keys:
            self._column_keys.remove(toggled_key)
        else:
            self._column_keys.append(toggled_key)

        self._rebuild_column_headers()
        self._save_column_config()

        if self.current_dir:
            self._redisplay_files()

    @Slot(int, int)
    def _on_file_double_click(self, row: int, column: int):
        """Handle file double-click — try to open externally"""
        import logging

        logger = logging.getLogger("filepilot.file_browser")

        path_item = self.file_table.item(row, 0)
        if path_item:
            file_path = Path(path_item.data(Qt.UserRole))
            if file_path.exists():
                try:
                    fp = str(file_path)
                    if sys.platform == "win32":
                        os.startfile(fp)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", fp])
                    else:
                        subprocess.Popen(["xdg-open", fp])
                    self.file_opened.emit(str(file_path))
                    if self.event_bus:
                        self.event_bus.open_file_requested.emit(str(file_path))
                except Exception as e:
                    logger.warning("Failed to open file %s: %s", file_path, e)
                    self.status_message.emit(f"Failed to open file: {file_path.name}")

    @Slot()
    def _on_export(self):
        """Export file list as JSON or CSV"""
        if not self.files:
            self.status_message.emit("No files to export")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export File List",
            str(Path.home() / "file_list.csv"),
            "CSV (*.csv);;JSON (*.json)",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            if path.suffix.lower() == ".json":
                data = [
                    {
                        "name": f.name,
                        "path": str(f.path),
                        "size": f.size_bytes,
                        "size_str": f.size_str,
                        "modified": f.modified_time.isoformat(),
                        "suffix": f.extension,
                    }
                    for f in self.files
                ]
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                with open(path, "w", newline="", encoding="utf-8") as fp:
                    writer = csv.writer(fp)
                    writer.writerow(["Name", "Path", "Size (bytes)", "Size", "Modified", "Type"])
                    for f in self.files:
                        writer.writerow(
                            [
                                f.name,
                                str(f.path),
                                f.size_bytes,
                                f.size_str,
                                f.modified_time.isoformat(),
                                f.extension,
                            ]
                        )
            self.status_message.emit(f"✅ Exported to {path.name}")
        except Exception as e:
            self.status_message.emit(f"❌ Export failed: {e}")

    @Slot()
    def _on_show_stats(self):
        """Show file statistics dialog for current directory."""
        if not self.current_dir:
            return

        from PySide6.QtWidgets import QDialog, QVBoxLayout

        from filepilot.ui.file_stats_panel import FileStatsPanel

        dialog = QDialog(self)
        dialog.setWindowTitle(f"📊 File Statistics — {self.current_dir.name}")
        dialog.setMinimumSize(900, 700)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        stats_panel = FileStatsPanel(scanner=self.scanner)
        layout.addWidget(stats_panel)

        stats_panel.analyze_directory(self.current_dir)
        dialog.exec()
