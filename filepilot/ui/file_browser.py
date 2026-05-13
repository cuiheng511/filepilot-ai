"""File browser panel — directory tree, file list, and preview"""
"""File browser panel — directory tree, file list, and preview"""

import json
import mimetypes
import csv
import io
from pathlib import Path
from threading import Thread
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
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
from filepilot.ui.base_panel import BasePanel


class FileBrowserPanel(BasePanel):
    """File browser panel — browse, scan, preview files"""

    def __init__(self, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.scanner = scanner or FileScanner()
        self.current_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.categories: dict[str, list[FileInfo]] = {}

        self._setup_ui()
        self._connect_signals()

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
        self.dir_label.setStyleSheet("color: #585b70; font-size: 12px; padding: 4px 8px;")
        header_layout.addWidget(self.dir_label)
        layout.addLayout(header_layout)

        desc = QLabel(
            "Browse files, preview content, and manage your folders. "
            "Drag and drop folders to open them."
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

        toolbar_layout.addStretch()

        self.cb_show_hidden = QCheckBox("Show hidden files")
        self.cb_show_hidden.setStyleSheet("color: #a6adc8;")
        self.cb_show_hidden.stateChanged.connect(self._on_refresh)
        toolbar_layout.addWidget(self.cb_show_hidden)

        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8; color: #1e1e2e;
                border: none; border-radius: 6px;
                padding: 6px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #eba0ac; }
        """)
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
        self.dir_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                font-size: 13px;
            }
            QTreeWidget::item { padding: 6px 8px; border-radius: 4px; }
            QTreeWidget::item:selected { background-color: #313244; color: #cba6f7; }
            QTreeWidget::item:hover { background-color: #252538; }
            QHeaderView::section {
                background-color: #181825; color: #a6adc8;
                border: none; border-bottom: 1px solid #313244;
                padding: 8px 10px; font-weight: bold; font-size: 12px;
            }
        """)
        self.dir_tree.itemClicked.connect(self._on_dir_clicked)
        dir_layout.addWidget(self.dir_tree, 1)

        # Center: file list table
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.addWidget(QLabel("📄 Files"))

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["Name", "Size", "Type", "Modified", "Path"])
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSortingEnabled(True)
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setStyleSheet("""
            QTableWidget {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                font-size: 13px; gridline-color: #252538;
            }
            QTableWidget::item { padding: 6px 10px; }
            QTableWidget::item:selected { background-color: #313244; color: #cba6f7; }
            QHeaderView::section {
                background-color: #181825; color: #a6adc8;
                border: none; border-bottom: 1px solid #313244;
                padding: 8px 10px; font-weight: bold; font-size: 12px;
            }
        """)
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
        self.preview_area.setStyleSheet("""
            QTextEdit {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                padding: 12px; font-size: 13px;
            }
        """)
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
        self.stats_label.setStyleSheet("color: #585b70; font-size: 12px; padding: 4px 0;")
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
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel.setVisible(True)
        self.status_message.emit("Scanning files...")
        self.file_table.setRowCount(0)

        def scan_worker():
            files = []
            total_estimate = 0

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
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_display_files", Qt.QueuedConnection, Q_ARG(list, files)
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
            ext = f.suffix.lower()
            if ext in (".pdf",):
                cat = "PDF"
            elif ext in (".md", ".markdown", ".mdx", ".rst"):
                cat = "Markdown"
            elif ext in (".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".sql", ".sh", ".bash", ".ps1", ".lua"):
                cat = "Code"
            elif ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"):
                cat = "Image"
            elif ext in (".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"):
                cat = "Office"
            elif ext in (".txt", ".log", ".cfg", ".ini", ".conf", ".yaml", ".yml", ".toml", ".json", ".xml"):
                cat = "Text"
            else:
                cat = "Other"
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
        icon_map = {
            "PDF": "📕", "Markdown": "📝", "Code": "💻",
            "Image": "🖼️", "Office": "📊", "Text": "📄", "Other": "📁",
        }

        for row, f in enumerate(filtered):
            ext = f.suffix.lower()
            cat = "Other"
            if ext in (".pdf",): cat = "PDF"
            elif ext in (".md", ".markdown", ".mdx", ".rst"): cat = "Markdown"
            elif ext in (".py", ".js", ".ts"): cat = "Code"
            elif ext in (".jpg", ".jpeg", ".png", ".gif"): cat = "Image"
            elif ext in (".docx", ".xlsx", ".pptx"): cat = "Office"
            elif ext in (".txt", ".log", ".cfg"): cat = "Text"

            icon = icon_map.get(cat, "📁")
            name_item = QTableWidgetItem(f"{icon}  {f.name}")
            name_item.setData(Qt.UserRole, str(f.path))

            size_item = QTableWidgetItem(f.size_str)
            type_item = QTableWidgetItem(cat)
            time_item = QTableWidgetItem(f.modified_time.strftime("%Y-%m-%d %H:%M"))
            path_item = QTableWidgetItem(str(f.path))

            self.file_table.setItem(row, 0, name_item)
            self.file_table.setItem(row, 1, size_item)
            self.file_table.setItem(row, 2, type_item)
            self.file_table.setItem(row, 3, time_item)
            self.file_table.setItem(row, 4, path_item)

        self.file_table.setSortingEnabled(True)

        # Update stats
        self._update_stat("📊 Total Files", str(len(filtered)))

        # Category stats
        for cat, flist in self.categories.items():
            key = f"📁 {cat}"

        self.btn_refresh.setEnabled(True)
        self.btn_export.setEnabled(True)

        total_size = sum(f.size_bytes for f in files)
        from filepilot.utils.file_utils import get_file_size_str
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
        """Handle file selection change — show preview"""
        selected = self.file_table.selectedItems()
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
        ext = path.suffix.lower()

        if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"):
            self.preview_area.setHtml(
                f"<p><b>Image file:</b> {path.name}</p>"
                f"<p><i>File preview is not supported in text mode. "
                f"Open the file in an external viewer.</i></p>"
                f"<p>Size: {path.stat().st_size} bytes</p>"
            )
        elif ext in (".pdf",):
            self.preview_area.setHtml(
                f"<p><b>PDF file:</b> {path.name}</p>"
                f"<p><i>Use the 'AI Summary' panel to extract content from this PDF.</i></p>"
                f"<p>Size: {path.stat().st_size} bytes</p>"
            )
        elif ext in (".md", ".markdown", ".mdx", ".rst"):
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                self.preview_area.setPlainText(content[:5000])
            except Exception:
                self.preview_area.setPlainText("[Error reading file]")
        else:
            # Try to preview as text
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                self.preview_area.setPlainText(content[:5000])
            except (UnicodeDecodeError, Exception):
                self.preview_area.setHtml(
                    f"<p><b>Binary file:</b> {path.name}</p>"
                    f"<p>Size: {path.stat().st_size} bytes</p>"
                    f"<p>Modified: {path.stat().st_mtime}</p>"
                )

    @Slot()
    def _on_file_double_click(self, row: int, column: int):
        """Handle file double-click — try to open externally"""
        path_item = self.file_table.item(row, 0)
        if path_item:
            file_path = Path(path_item.data(Qt.UserRole))
            if file_path.exists():
                import subprocess
                try:
                    subprocess.Popen(["xdg-open", str(file_path)], shell=True)
                except Exception:
                    pass

    @Slot()
    def _on_export(self):
        """Export file list as JSON or CSV"""
        if not self.files:
            self.status_message.emit("No files to export")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export File List",
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
                        "suffix": f.suffix,
                    }
                    for f in self.files
                ]
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                with open(path, "w", newline="", encoding="utf-8") as fp:
                    writer = csv.writer(fp)
                    writer.writerow(["Name", "Path", "Size (bytes)", "Size", "Modified", "Type"])
                    for f in self.files:
                        writer.writerow([
                            f.name, str(f.path), f.size_bytes, f.size_str,
                            f.modified_time.isoformat(), f.suffix,
                        ])
            self.status_message.emit(f"✅ Exported to {path.name}")
        except Exception as e:
            self.status_message.emit(f"❌ Export failed: {e}")
