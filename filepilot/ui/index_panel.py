"""Index Management Panel — Build, update, and view index"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.core.worker import Worker
from filepilot.extractors.code_extractor import CodeExtractor
from filepilot.extractors.docx_extractor import DocxExtractor
from filepilot.extractors.markdown_extractor import MarkdownExtractor
from filepilot.extractors.pdf_extractor import PDFExtractor
from filepilot.extractors.pptx_extractor import PptxExtractor
from filepilot.extractors.xlsx_extractor import XlsxExtractor
from filepilot.i18n import t
from filepilot.ui.base_panel import BasePanel

_EXTRACTORS: dict[str, Any] = {
    ".py": CodeExtractor(),
    ".js": CodeExtractor(),
    ".jsx": CodeExtractor(),
    ".ts": CodeExtractor(),
    ".tsx": CodeExtractor(),
    ".java": CodeExtractor(),
    ".c": CodeExtractor(),
    ".cpp": CodeExtractor(),
    ".h": CodeExtractor(),
    ".hpp": CodeExtractor(),
    ".cs": CodeExtractor(),
    ".go": CodeExtractor(),
    ".rs": CodeExtractor(),
    ".rb": CodeExtractor(),
    ".php": CodeExtractor(),
    ".swift": CodeExtractor(),
    ".kt": CodeExtractor(),
    ".scala": CodeExtractor(),
    ".html": CodeExtractor(),
    ".css": CodeExtractor(),
    ".scss": CodeExtractor(),
    ".sql": CodeExtractor(),
    ".r": CodeExtractor(),
    ".m": CodeExtractor(),
    ".mm": CodeExtractor(),
    ".sh": CodeExtractor(),
    ".bat": CodeExtractor(),
    ".ps1": CodeExtractor(),
    ".md": MarkdownExtractor(),
    ".markdown": MarkdownExtractor(),
    ".pdf": PDFExtractor(),
    ".docx": DocxExtractor(),
    ".pptx": PptxExtractor(),
    ".xlsx": XlsxExtractor(),
}


class IndexPanel(BasePanel):
    """Index Management Panel"""

    indexing_finished = Signal()
    indexing_error = Signal(str)

    def __init__(
        self,
        indexer: FileIndexer | None = None,
        scanner: FileScanner | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.source_dir: Path | None = None
        self.indexer = indexer or FileIndexer()
        self.scanner = scanner or FileScanner()
        self.state = app_state
        self.event_bus = event_bus
        self._pool = QThreadPool.globalInstance()
        self._indexing = False
        self._cancelled = False

        self._setup_ui()
        self._connect_signals()
        self._refresh_stats()

    def update_services(
        self,
        scanner: FileScanner | None = None,
        indexer: FileIndexer | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
    ):
        """Update service references without recreating the panel"""
        if scanner is not None:
            self.scanner = scanner
        if indexer is not None:
            self.indexer = indexer
        if app_state is not None:
            self.state = app_state
        if event_bus is not None:
            self.event_bus = event_bus

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._create_title_section(layout)
        self._create_stat_cards(layout)
        self._create_directory_selection(layout)
        self._create_action_buttons(layout)
        self._create_progress_section(layout)
        self._create_splitter_with_table(layout)
        self._create_status_label(layout)

    def _create_title_section(self, layout):
        title = QLabel(t("index_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        desc = QLabel(
            "Manage Whoosh full-text search index. Build the index to enable fast "
            "full-text search and natural language retrieval.\n"
            "Supports incremental updates without rebuilding the entire index.",
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

    def _create_stat_cards(self, layout):
        stats_layout = QHBoxLayout()
        self.stat_indexed = self._make_stat_card("\U0001f4c4 Indexed Files", "\u2014")
        self.stat_size = self._make_stat_card("\U0001f4be Index Size", "\u2014")
        self.stat_location = self._make_stat_card("\U0001f4c1 Index Location", "\u2014")
        stats_layout.addWidget(self.stat_indexed)
        stats_layout.addWidget(self.stat_size)
        stats_layout.addWidget(self.stat_location)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

    def _create_directory_selection(self, layout):
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("\U0001f4c2 Folder to Index:"))
        self.dir_label = QLabel(t("index_dir_placeholder"))
        self.dir_label.setObjectName("pathLabel")
        self.dir_label.setWordWrap(True)
        self.btn_browse = QPushButton(t("index_browse"))
        self.btn_browse.clicked.connect(self._on_select_source)
        dir_layout.addWidget(self.dir_label, 1)
        dir_layout.addWidget(self.btn_browse)
        layout.addLayout(dir_layout)

    def _create_action_buttons(self, layout):
        action_layout = QHBoxLayout()
        self.btn_build = QPushButton(t("index_build"))
        self.btn_build.setObjectName("btnPrimary")
        self.btn_build.clicked.connect(self._on_build)
        self.btn_build.setEnabled(False)
        self.btn_update = QPushButton("\U0001f504 Incremental Update")
        self.btn_update.clicked.connect(self._on_update)
        self.btn_update.setEnabled(False)
        self.btn_clear = QPushButton(t("index_clear"))
        self.btn_clear.setObjectName("btnDanger")
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_clear.setEnabled(False)
        self.btn_refresh = QPushButton("\U0001f504 Refresh Stats")
        self.btn_refresh.clicked.connect(self._refresh_stats)
        action_layout.addWidget(self.btn_build)
        action_layout.addWidget(self.btn_update)
        action_layout.addWidget(self.btn_clear)
        action_layout.addWidget(self.btn_refresh)
        action_layout.addStretch()
        layout.addLayout(action_layout)

    def _create_progress_section(self, layout):
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressLabel")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)
        self.btn_cancel = QPushButton("\u2715 Cancel")
        self.btn_cancel.setObjectName("btnDanger")
        self.btn_cancel.clicked.connect(self._on_cancel_indexing)
        self.btn_cancel.setVisible(False)
        progress_layout.addWidget(self.btn_cancel)
        layout.addLayout(progress_layout)

    def _create_splitter_with_table(self, layout):
        splitter = QSplitter(Qt.Vertical)
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_label = QLabel(
            "\U0001f4a1 Tip: Select a folder first, then click Build Index.\n"
            "       After modifying files, just click Incremental Update.\n"
            "       The indexed file list will appear here.",
        )
        info_label.setObjectName("infoBox")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        splitter.addWidget(info_widget)
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(
            [
                t("index_file_header"),
                t("index_path_header"),
                t("index_category_header"),
                t("index_size_header"),
                t("index_date_header"),
            ],
        )
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._on_table_context_menu)
        splitter.addWidget(self.file_table)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

    def _create_status_label(self, layout):
        self.stats_label = QLabel(t("ready"))
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.progress_text.connect(self.progress_label.setText)
        self.status_message.connect(self.stats_label.setText)
        self.indexing_finished.connect(self._on_indexing_finished)
        self.indexing_error.connect(self._on_indexing_error)

    # ── Directory Selection ──

    @Slot()
    def _on_select_source(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            t("select_folder_to_index"),
            str(self.source_dir or Path.home()),
        )
        if dir_path:
            self.source_dir = Path(dir_path)
            self.dir_label.setText(f"\U0001f4c2 {dir_path}")
            self.dir_label.setProperty("selected", True)
            self.dir_label.style().unpolish(self.dir_label)
            self.dir_label.style().polish(self.dir_label)
            self.btn_build.setEnabled(True)
            self.btn_update.setEnabled(True)

    # ── Stats Refresh ──

    def _refresh_stats(self):
        """Refresh index statistics"""
        try:
            stats = self.indexer.get_stats()
            self._update_stat("\U0001f4c4 Indexed Files", str(stats["indexed_files"]))
            self._update_stat("\U0001f4be Index Size", stats["index_size"])
            self._update_stat("\U0001f4c1 Index Location", stats["index_dir"])
            self.btn_clear.setEnabled(stats["indexed_files"] > 0)
            self._load_indexed_files()
        except Exception:
            self._update_stat("\U0001f4c4 Indexed Files", "0")
            self._update_stat("\U0001f4be Index Size", "\u2014")
            self._update_stat("\U0001f4c1 Index Location", str(self.indexer.index_dir))
            self.btn_clear.setEnabled(False)

    def _load_indexed_files(self):
        """Load indexed file list into table"""
        try:
            files = self.indexer.get_all_indexed(limit=2000)
        except Exception:
            files = []

        self.file_table.setSortingEnabled(False)
        self.file_table.setRowCount(len(files))

        for row, f in enumerate(files):
            self.file_table.setItem(row, 0, QTableWidgetItem(f["filename"]))
            self.file_table.setItem(row, 1, QTableWidgetItem(f["path"]))
            self.file_table.setItem(row, 2, QTableWidgetItem(f.get("category", "")))
            self.file_table.setItem(row, 3, QTableWidgetItem(f.get("size_str", "")))
            self.file_table.setItem(row, 4, QTableWidgetItem(f.get("modified", "")))

        self.file_table.setSortingEnabled(True)

    # ── Build Index ──

    @Slot()
    def _on_build(self):
        if not self.source_dir:
            self.status_message.emit("\u26a0\ufe0f Please select a folder first")
            return
        if self._indexing:
            return

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            t("confirm_build_index"),
            f"Build full-text search index for {self.source_dir}.\n\n"
            "Existing index will be overwritten.\n"
            "This may take some time. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        self._start_indexing("Building index...", rebuild=True)

    @Slot()
    def _on_update(self):
        if not self.source_dir:
            self.status_message.emit("\u26a0\ufe0f Please select a folder first")
            return
        if self._indexing:
            return
        self._start_indexing("Updating index incrementally...", rebuild=False)

    @Slot()
    def _on_cancel_indexing(self):
        """Cancel indexing operation"""
        self._cancelled = True
        self._indexing = False
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_build.setEnabled(bool(self.source_dir))
        self.btn_update.setEnabled(bool(self.source_dir))
        self.btn_refresh.setEnabled(True)
        self.status_message.emit("\u23f9\ufe0f Index cancelled")

    def _start_indexing(self, status_text: str, rebuild: bool):
        """Start indexing thread"""
        self._cancelled = False
        self._indexing = True
        self.btn_build.setEnabled(False)
        self.btn_update.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.emit(status_text)

        _dir = self.source_dir

        def worker():
            try:
                if rebuild:
                    self._build_index(_dir)
                else:
                    self._update_index()

                if not self._cancelled:
                    self.indexing_finished.emit()
            except Exception as e:
                self.indexing_error.emit(str(e))

        w = Worker(worker)
        w.signals.finished.connect(lambda _: None)
        self._pool.start(w)

    def _extract_content(self, file_info: FileInfo) -> str:
        ext = file_info.extension.lower()
        extractor = _EXTRACTORS.get(ext)
        if extractor:
            try:
                return extractor.extract_text(file_info.path) or ""
            except Exception:
                pass
        text_exts = {
            ".txt",
            ".log",
            ".ini",
            ".cfg",
            ".toml",
            ".yaml",
            ".yml",
            ".json",
            ".xml",
            ".csv",
        }
        if ext in text_exts:
            try:
                return file_info.path.read_text(encoding="utf-8", errors="replace")[:5000]
            except Exception:
                pass
        return ""

    def _build_index(self, dir_path: Path):
        files = list(
            self.scanner.scan(
                str(dir_path),
                progress_callback=lambda i, p: None,
            )
        )
        if self._cancelled:
            return
        total = len(files)

        def on_progress(i: int, msg: str):
            pct = int(i / total * 100) if total else 0
            self.progress_updated.emit(pct)
            self.progress_text.emit(f"{i}/{total}")

        self.indexer.clear_index()
        self.indexer.index_files(
            files,
            content_extractor=self._extract_content,
            embedding_extractor=None,
            progress_callback=on_progress,
        )

    def _update_index(self):
        if not self.source_dir:
            return
        files = list(
            self.scanner.scan(
                str(self.source_dir),
                progress_callback=lambda i, p: None,
            )
        )
        if self._cancelled:
            return
        total = len(files)

        def on_progress(i: int, msg: str):
            pct = int(i / total * 100) if total else 0
            self.progress_updated.emit(pct)
            self.progress_text.emit(f"{i}/{total}")

        self.indexer.index_files(
            files,
            content_extractor=self._extract_content,
            embedding_extractor=None,
            progress_callback=on_progress,
            incremental=True,
        )

    @Slot()
    def _on_indexing_finished(self):
        """Indexing complete"""
        self._indexing = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_build.setEnabled(bool(self.source_dir))
        self.btn_update.setEnabled(bool(self.source_dir))
        self.btn_refresh.setEnabled(True)
        self._refresh_stats()
        stats = self.indexer.get_stats()
        self.status_message.emit(
            f"\u2705 Index complete: {stats['indexed_files']} files indexed, "
            f"size: {stats['index_size']}",
        )

    @Slot(str)
    def _on_indexing_error(self, error_msg: str):
        """Indexing error"""
        self._indexing = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_build.setEnabled(bool(self.source_dir))
        self.btn_update.setEnabled(bool(self.source_dir))
        self.btn_refresh.setEnabled(True)
        self.status_message.emit(f"\u274c Index error: {error_msg}")

    # ── Clear Index ──

    @Slot()
    def _on_clear(self):
        """Clear index"""
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.warning(
            self,
            t("confirm_clear_index"),
            "Are you sure you want to clear all index data?\n\n"
            "All indexed file records will be deleted. "
            "You will need to rebuild the index to search again.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.indexer.clear_index()
            self._refresh_stats()
            self.file_table.setRowCount(0)
            self.status_message.emit("\U0001f5d1\ufe0f Index cleared")
            self.btn_clear.setEnabled(False)
        except Exception as e:
            self.status_message.emit(f"\u274c Clear failed: {e}")

    # ── Table Context Menu ──

    @Slot()
    def _on_table_context_menu(self, pos):
        """Table right-click menu: remove from index"""
        row = self.file_table.rowAt(pos.y())
        if row < 0:
            return

        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setObjectName("contextMenu")

        remove_action = QAction("\U0001f5d1\ufe0f Remove from Index", self)
        remove_action.triggered.connect(lambda: self._remove_selected_from_index())
        menu.addAction(remove_action)

        refresh_action = QAction("\U0001f504 Refresh List", self)
        refresh_action.triggered.connect(self._load_indexed_files)
        menu.addAction(refresh_action)

        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def _remove_selected_from_index(self):
        """Remove selected files from index"""
        selected = self.file_table.selectionModel().selectedRows()
        if not selected:
            return

        removed = 0
        for index in selected:
            path_item = self.file_table.item(index.row(), 1)
            if path_item and path_item.text():
                try:
                    self.indexer.remove_from_index(path_item.text())
                    removed += 1
                except Exception:
                    pass

        self._load_indexed_files()
        self._refresh_stats()
        self.status_message.emit(f"\u2705 Removed {removed} files from index")

    # ── External Entry Point ──

    def index_directory(self, dir_path: str | Path):
        """Quick method for main window to call"""
        self.source_dir = Path(dir_path)
        self.dir_label.setText(f"\U0001f4c2 {dir_path}")
        self.dir_label.setProperty("selected", True)
        self.dir_label.style().unpolish(self.dir_label)
        self.dir_label.style().polish(self.dir_label)
        self.btn_build.setEnabled(True)
        self.btn_update.setEnabled(True)
        self._on_build()
