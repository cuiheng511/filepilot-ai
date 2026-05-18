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
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.tag_manager import TagManager
from filepilot.ui.base_panel import BasePanel
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

    def __init__(self, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.scanner = scanner or FileScanner()
        self.current_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.categories: dict[str, list[FileInfo]] = {}
        self.tag_manager = TagManager()
        self._column_keys: list[str] = []
        self._col_index: dict[str, int] = {}

        self._setup_ui()
        self._connect_signals()
        self._load_column_config()

    def update_services(self, scanner: FileScanner | None = None):
        """Update service references without recreating the panel"""
        if scanner is not None:
            self.scanner = scanner

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── Header ──
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

        # ── Toolbar ──
        toolbar_layout = QHBoxLayout()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self._on_refresh)
        self.btn_refresh.setEnabled(False)
        toolbar_layout.addWidget(self.btn_refresh)

        self.btn_export = QPushButton("📤 Export")
        self.btn_export.clicked.connect(self._on_export)
        self.btn_export.setEnabled(False)
        toolbar_layout.addWidget(self.btn_export)

        self.btn_stats = QPushButton("📊 Stats")
        self.btn_stats.clicked.connect(self._on_show_stats)
        self.btn_stats.setEnabled(False)
        toolbar_layout.addWidget(self.btn_stats)

        # Batch operations
        self.btn_copy = QPushButton("📋 Copy")
        self.btn_copy.clicked.connect(self._batch_copy)
        self.btn_copy.setEnabled(False)
        self.btn_copy.setToolTip("Copy selected files to another folder")
        toolbar_layout.addWidget(self.btn_copy)

        self.btn_move = QPushButton("✂ Move")
        self.btn_move.clicked.connect(self._batch_move)
        self.btn_move.setEnabled(False)
        self.btn_move.setToolTip("Move selected files to another folder")
        toolbar_layout.addWidget(self.btn_move)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.clicked.connect(self._batch_delete)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setToolTip("Delete selected files (to Recycle Bin)")
        toolbar_layout.addWidget(self.btn_delete)

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

        # ── Progress bar ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ── Main splitter: directory tree | file list | preview ──
        main_splitter = QSplitter(Qt.Horizontal)

        # Left: directory tree
        dir_widget = QWidget()
        dir_layout = QVBoxLayout(dir_widget)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.addWidget(QLabel("🗂 Directories"))

        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderLabels(["Name"])
        self.dir_tree.setAnimated(True)
        self.dir_tree.setIndentation(16)
        self.dir_tree.setRootIsDecorated(True)
        self.dir_tree.header().setStretchLastSection(True)
        self.dir_tree.itemClicked.connect(self._on_dir_clicked)
        dir_layout.addWidget(self.dir_tree, 1)

        # Center: file list table
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

        # Right: file preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(QLabel("👁 Preview"))

        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setPlaceholderText("Select a file to preview its content or metadata...")
        preview_layout.addWidget(self.preview_area, 1)

        main_splitter.addWidget(dir_widget)
        main_splitter.addWidget(file_widget)
        main_splitter.addWidget(preview_widget)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        main_splitter.setStretchFactor(2, 2)
        main_splitter.setSizes([250, 500, 350])

        layout.addWidget(main_splitter, 1)

        # ── Category stats bar ──
        stats_layout = QHBoxLayout()
        self.stat_total = self._make_stat_card("📊 Total Files", "0")
        self.stat_categories = {}

        stats_layout.addWidget(self.stat_total)
        layout.addLayout(stats_layout)
        self.stats_container = stats_layout

        # ── Status ──
        self.stats_label = QLabel("Open a folder to start browsing")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)

    def load_directory(self, dir_path: str | Path):
        """Load a directory into the tree"""
        self.current_dir = Path(dir_path)
        self.dir_label.setText(f"📂 {dir_path}")
        self.dir_tree.clear()

        root = QTreeWidgetItem(self.dir_tree)
        root.setText(0, self.current_dir.name)
        root.setData(0, Qt.UserRole, str(self.current_dir))
        root.setExpanded(True)

        self._populate_dir_tree(self.current_dir, root)
        self.btn_refresh.setEnabled(True)
        self.scan_directory(self.current_dir)

    def scan_directory(self, dir_path: str | Path):
        """Scan directory and populate file list"""
        self._cancelled = False
        self._cancelling = False
        self.btn_refresh.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.btn_stats.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel.setVisible(True)
        self.status_message.emit("Scanning files...")
        self.file_table.setRowCount(0)

        def scan_worker():
            files = []

            for f in self.scanner.scan(
                str(dir_path),
                progress_callback=lambda i, p: self.progress_updated.emit(i % 100),
            ):
                if self._cancelled:
                    return
                files.append(f)

            if self._cancelled:
                return

            self.files = files

            # Categorize
            self.categories = self._categorize_files(files)

            if not self._cancelled:
                from PySide6.QtCore import Q_ARG, QMetaObject, Qt

                QMetaObject.invokeMethod(
                    self,
                    "_display_files",
                    Qt.QueuedConnection,
                    Q_ARG(list, files),
                )

        Thread(target=scan_worker, daemon=True).start()

    def _populate_dir_tree(self, dir_path: Path, parent_item: QTreeWidgetItem):
        """Recursively populate directory tree"""
        try:
            for entry in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if entry.name.startswith(".") and not self.cb_show_hidden.isChecked():
                    continue
                if entry.is_dir():
                    child = QTreeWidgetItem(parent_item)
                    child.setText(0, f"📁 {entry.name}")
                    child.setData(0, Qt.UserRole, str(entry))
                    child.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        except PermissionError:
            pass

    def _categorize_files(self, files: list[FileInfo]) -> dict[str, list[FileInfo]]:
        """Categorize files by type"""
        categories: dict[str, list[FileInfo]] = {}
        for f in files:
            cat = get_category_name(f.path.suffix.lower())
            categories.setdefault(cat, []).append(f)
        return categories

    @Slot()
    def _display_files(self, files: list[FileInfo]):
        """Display file list in table"""
        self.file_table.setRowCount(0)
        self.file_table.setSortingEnabled(False)

        hidden = self.cb_show_hidden.isChecked()
        filtered = [f for f in files if hidden or not f.name.startswith(".")]
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
                    if created:
                        item = QTableWidgetItem(created.strftime("%Y-%m-%d %H:%M"))
                    else:
                        item = QTableWidgetItem("-")
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

        # Update stats
        self._update_stat("📊 Total Files", str(len(filtered)))

        # Category stats
        for cat in self.categories:
            cat_count = len(self.categories[cat])
            cat_size = sum(f.size_bytes for f in self.categories[cat])
            if cat not in self.stat_cards:
                card = self._make_stat_card(f"📁 {cat}", f"{cat_count} files")
                self.stats_container.addWidget(card)
            self._update_stat(f"📁 {cat}", f"{cat_count} files ({get_file_size_str(cat_size)})")

        self.btn_refresh.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.btn_stats.setEnabled(True)

        total_size = sum(f.size_bytes for f in files)
        size_str = get_file_size_str(total_size)
        self.status_message.emit(f"✅ Scanned {len(filtered)} files ({size_str})")

        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)

    @Slot()
    def _on_dir_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle directory tree click"""
        dir_path = item.data(0, Qt.UserRole)
        if dir_path and Path(dir_path).is_dir():
            if item.childCount() == 0 and item.data(0, Qt.UserRole):
                self._populate_dir_tree(Path(dir_path), item)
            self.current_dir = Path(dir_path)
            self.dir_label.setText(f"📂 {dir_path}")
            self.scan_directory(dir_path)

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
        self.btn_copy.setEnabled(has_selection)
        self.btn_move.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

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

        self._preview_file(path)

    def _preview_file(self, path: Path):
        """Preview file content or metadata"""
        cat = get_category_name(path.suffix.lower())
        stats_html = (
            f"<p>Size: {path.stat().st_size} bytes</p><p>Modified: {path.stat().st_mtime:.0f}</p>"
        )

        if cat == "Image":
            self.preview_area.setHtml(
                f"<p><b>🖼️ Image file:</b> {path.name}</p>"
                f"<p><i>File preview is not supported in text mode. "
                f"Open the file in an external viewer.</i></p>{stats_html}",
            )
        elif cat == "PDF":
            self.preview_area.setHtml(
                f"<p><b>📕 PDF file:</b> {path.name}</p>"
                f"<p><i>Use the 'AI Summary' panel to extract content from this PDF.</i></p>{stats_html}",
            )
        elif cat in ("Markdown", "Code", "Text"):
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                self.preview_area.setPlainText(content[:5000])
            except Exception:
                self.preview_area.setPlainText("[Error reading file]")
        else:
            # Binary/media/office files — stats only
            self.preview_area.setHtml(
                f"<p><b>📄 {path.name}</b></p>{stats_html}"
                f"<p><i>Preview not available for this file type.</i></p>",
            )

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
        add_action = menu.addAction("\U0001f3f7\ufe0f Add Tag...")
        remove_action = menu.addAction("\U0001f5d1\ufe0f Remove Tag...")
        color_action = menu.addAction("\U0001f3a8 Change Color...")
        clear_action = menu.addAction("\u274c Remove All Tags")
        action = menu.exec(self.file_table.viewport().mapToGlobal(pos))

        if action == add_action:
            tag, ok = QInputDialog.getText(self, "Add Tag", "Enter tag name:")
            if ok and tag.strip():
                self.tag_manager.add_tag(file_path, tag.strip())
                self._refresh_tag_column()
                self.status_message.emit(f"Added tag '{tag.strip()}' to {Path(file_path).name}")
        elif action == remove_action:
            tags = self.tag_manager.get_tags(file_path)
            if tags:
                tag, ok = QInputDialog.getItem(self, "Remove Tag", "Select tag:", tags)
                if ok and tag:
                    self.tag_manager.remove_tag(file_path, tag)
                    self._refresh_tag_column()
                    self.status_message.emit(f"Removed tag '{tag}' from {Path(file_path).name}")
        elif action == color_action:
            from PySide6.QtWidgets import QColorDialog

            current = self.tag_manager.get_color(file_path) or "#888"
            qcolor = QColorDialog.getColor(QColor(current), self, "Pick a color")
            if qcolor.isValid():
                self.tag_manager.set_color(file_path, qcolor.name())
                self._refresh_tag_column()
                self.status_message.emit(f"Changed color for {Path(file_path).name}")
        elif action == clear_action:
            self.tag_manager.remove_file(file_path)
            self._refresh_tag_column()
            self.status_message.emit(f"Removed all tags from {Path(file_path).name}")

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
        from filepilot.core import config

        settings = config.load()
        keys = settings.get("file_browser_columns", DEFAULT_COLUMNS)
        self._column_keys = [k for k in keys if k in COLUMN_DEFS]
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
        from filepilot.core import config

        settings = config.load()
        settings["file_browser_columns"] = list(self._column_keys)
        config.save(settings)

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
            self._display_files(self.files)

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
