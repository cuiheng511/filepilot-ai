"""Search panel — natural language file search"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.ui.base_panel import BasePanel


class SearchPanel(BasePanel):
    """Search panel for natural language file search"""

    indexing_finished = Signal(int, str)

    def __init__(self, indexer: FileIndexer | None = None, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.indexer = indexer or FileIndexer()
        self.scanner = scanner or FileScanner()
        self.current_dir: Path | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Build the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("🔍 File Search")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Natural language search for local files. Supports search by file name, content, type, and date.\n"
            'Example: "PDF files modified last week" or "find documents about machine learning"'
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search keywords, e.g.: find PDFs about deep learning...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 2px solid #313244;
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #cba6f7;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)

        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #1e1e2e;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
        """)
        self.search_btn.clicked.connect(self._on_search)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # Search options
        options_layout = QHBoxLayout()
        self.fuzzy_cb = QCheckBox("Fuzzy search")
        self.fuzzy_cb.setChecked(True)
        self.fuzzy_cb.setStyleSheet("color: #a6adc8;")
        options_layout.addWidget(self.fuzzy_cb)

        self.content_cb = QCheckBox("Search content")
        self.content_cb.setChecked(True)
        self.content_cb.setStyleSheet("color: #a6adc8;")
        options_layout.addWidget(self.content_cb)

        options_layout.addStretch()

        self.index_btn = QPushButton("🗂️ Build Index")
        self.index_btn.clicked.connect(self._on_index)
        options_layout.addWidget(self.index_btn)

        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self._clear_results)
        options_layout.addWidget(self.clear_btn)

        layout.addLayout(options_layout)

        # Progress bar + cancel button
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)

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
        progress_layout.addWidget(self.btn_cancel)
        layout.addLayout(progress_layout)

        # Search results
        self.result_list = QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #252538;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #313244;
                color: #cba6f7;
            }
            QListWidget::item:hover {
                background-color: #252538;
            }
        """)
        layout.addWidget(self.result_list, 1)

        # Status
        self.stats_label = QLabel("Please open a folder and build the index first")
        self.stats_label.setStyleSheet("color: #585b70; font-size: 12px;")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        """Connect signals"""
        self.status_message.connect(self._on_status_message)
        self.progress_updated.connect(self.progress_bar.setValue)
        self.indexing_finished.connect(self._on_indexing_finished)

    def index_directory(self, dir_path: str | Path):
        """Index a directory"""
        self.current_dir = Path(dir_path)
        self._index_async(dir_path)

    @Slot()
    def _on_cancel(self):
        """Cancel current operation"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        self.index_btn.setEnabled(True)
        self.status_message.emit("⏹️ Operation cancelled")

    @Slot()
    def _on_search(self):
        """Execute search"""
        query = self.search_input.text().strip()
        if not query:
            return

        # Check index status
        stats = self.indexer.get_stats()
        if stats["indexed_files"] == 0:
            self.result_list.addItem(
                "⚠️ Index is empty. Please build the index first before searching."
            )
            return

        self._cancelled = False
        self._cancelling = False
        self.status_message.emit(f"Searching: {query} ...")
        self.search_btn.setEnabled(False)
        self.btn_cancel.setVisible(True)

        def search_worker():
            if self._cancelled:
                return
            # Execute search
            results = self.indexer.search(
                query,
                fuzzy=self.fuzzy_cb.isChecked(),
                limit=100,
            )

            if self._cancelled:
                return

            # Display results on main thread
            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self,
                "_display_results",
                Qt.QueuedConnection,
                Q_ARG(list, results),
                Q_ARG(str, query),
            )

        Thread(target=search_worker, daemon=True).start()

    @Slot()
    def _display_results(self, results: list[dict], query: str):
        """Display search results"""
        self.result_list.clear()
        self.search_btn.setEnabled(True)

        if not results:
            item = QListWidgetItem(f"No results found for \"{query}\"")
            item.setForeground(Qt.gray)
            self.result_list.addItem(item)
            self.stats_label.setText("No matching results")
            return

        for r in results:
            score = r.get("score", 0)
            category = r.get("category", "Other")
            filename = r.get("filename", "Unknown")
            filepath = r.get("path", "")
            modified = r.get("modified", "")
            size_str = r.get("size_str", "")
            highlights = r.get("highlights", "")

            # Icon mapping
            icon_map = {
                "PDF": "📕",
                "Markdown": "📝",
                "Code": "💻",
                "Image": "🖼️",
                "Document": "📄",
                "Other": "📁",
            }
            icon = icon_map.get(category, "📁")

            display_text = f"{icon}  {filename}"
            if highlights:
                display_text += f"\n   📌 {highlights[:100]}"
            display_text += f"\n   📂 {filepath}  |  {size_str}  |  {modified}  |  Match: {score:.0%}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, filepath)
            item.setToolTip(f"Path: {filepath}\nMatch: {score:.0%}")
            self.result_list.addItem(item)

        self.stats_label.setText(f"Found {len(results)} results for: {query}")

    @Slot()
    def _on_index(self):
        """Build index"""
        if not self.current_dir:
            self.result_list.addItem("⚠️ Please open a folder first in the File Browser")
            return

        self._index_async(self.current_dir)

    def _index_async(self, dir_path: str | Path):
        """Build index asynchronously"""
        self._cancelled = False
        self._cancelling = False
        self.index_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel.setVisible(True)
        self.status_message.emit("Scanning and building index...")

        def index_worker():
            # Single scan, reuse results
            files = []
            for f in self.scanner.scan(
                str(dir_path),
                progress_callback=lambda i, p: None,
            ):
                if self._cancelled:
                    from PySide6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(self, "_on_cancel_done", Qt.QueuedConnection)
                    return
                files.append(f)

            if self._cancelled:
                return

            total = len(files)

            # Build index
            indexed = self.indexer.index_files(
                files,
                progress_callback=lambda i, msg: self.progress_updated.emit(
                    int(i / total * 100) if total else 0
                ),
            )

            if not self._cancelled:
                self.indexing_finished.emit(indexed, str(dir_path))

        Thread(target=index_worker, daemon=True).start()

    @Slot()
    def _on_cancel_done(self):
        """Cancel indexing"""
        if not self._cancelling:
            return
        self._cancelling = False
        self.index_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)
        self.status_message.emit("⏹️ Indexing cancelled")

    @Slot()
    def _on_indexing_finished(self, indexed: int, dir_path: str):
        """Indexing finished callback (main thread)"""
        status_msg = f"Indexing complete: {indexed} files indexed"
        self.status_message.emit(status_msg)
        self.index_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        stats = self.indexer.get_stats()
        self.stats_label.setText(
            f"📊 Index stats: {stats['indexed_files']} files, "
            f"index size: {stats['index_size']}"
        )

    def _clear_results(self):
        """Clear search results"""
        self.result_list.clear()
        self.search_input.clear()
        self.stats_label.setText("Ready")

    @Slot()
    def _on_status_message(self, msg: str):
        """Update status"""
        self.stats_label.setText(msg)
