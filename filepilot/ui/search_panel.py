"""Search panel — natural language file search"""

import json
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.core.plugin_system import get_plugin_manager
from filepilot.core.tag_manager import TagManager
from filepilot.core.worker import Worker
from filepilot.extractors import (
    CodeExtractor,
    DocxExtractor,
    MarkdownExtractor,
    PDFExtractor,
    PptxExtractor,
    XlsxExtractor,
)
from filepilot.ui.base_panel import BasePanel

# Extractor mapping by extension
_EXTRACTORS = {
    ".pdf": PDFExtractor(),
    ".md": MarkdownExtractor(),
    ".markdown": MarkdownExtractor(),
    ".mdx": MarkdownExtractor(),
    ".py": CodeExtractor(),
    ".js": CodeExtractor(),
    ".ts": CodeExtractor(),
    ".jsx": CodeExtractor(),
    ".tsx": CodeExtractor(),
    ".java": CodeExtractor(),
    ".cpp": CodeExtractor(),
    ".c": CodeExtractor(),
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
    ".sql": CodeExtractor(),
    ".sh": CodeExtractor(),
    ".bash": CodeExtractor(),
    ".ps1": CodeExtractor(),
    ".bat": CodeExtractor(),
    ".pl": CodeExtractor(),
    ".lua": CodeExtractor(),
    ".r": CodeExtractor(),
    ".m": CodeExtractor(),
    ".dart": CodeExtractor(),
    ".vue": CodeExtractor(),
    ".svelte": CodeExtractor(),
    ".docx": DocxExtractor(),
    ".xlsx": XlsxExtractor(),
    ".pptx": PptxExtractor(),
}


class SearchPanel(BasePanel):
    """Search panel for natural language file search"""

    indexing_finished = Signal(int, str)
    search_results_ready = Signal(list, str)
    cancel_acknowledged = Signal()

    def __init__(
        self,
        indexer: FileIndexer | None = None,
        scanner: FileScanner | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.indexer = indexer or FileIndexer()
        self.scanner = scanner or FileScanner()
        self.state = app_state
        self.event_bus = event_bus
        self._pool = QThreadPool.globalInstance()
        self.current_dir: Path | None = None
        self._cancelled = False
        self._cancelling = False
        self.tag_manager = TagManager()

        self._setup_ui()
        self._connect_signals()

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
        """Build the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._create_title(layout)
        self._create_search_bar(layout)
        self._create_search_options(layout)
        self._create_progress_bar(layout)
        self._create_results_list(layout)
        self._create_status(layout)

    def _create_title(self, layout):
        title = QLabel("🔍 File Search")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        desc = QLabel(
            "Natural language search for local files. Supports search by file name, content, type, and date.\n"
            'Example: "PDF files modified last week" or "find documents about machine learning"',
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

    def _create_search_bar(self, layout):
        search_layout = QHBoxLayout()
        self.search_input = QComboBox()
        self.search_input.setObjectName("searchInput")
        self.search_input.setEditable(True)
        self.search_input.setInsertPolicy(QComboBox.NoInsert)
        self.search_input.setPlaceholderText(
            "Enter search keywords, e.g.: find PDFs about deep learning..."
        )
        self.search_input.lineEdit().returnPressed.connect(self._on_search)
        self.search_input.activated.connect(self._on_search)
        self.search_btn = QPushButton("🔍 Search")
        self.search_btn.setObjectName("btnSearch")
        self.search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        self._load_search_history()

    def _create_search_options(self, layout):
        options_layout = QHBoxLayout()
        self.fuzzy_cb = QCheckBox("Fuzzy search")
        self.fuzzy_cb.setChecked(True)
        options_layout.addWidget(self.fuzzy_cb)
        self.content_cb = QCheckBox("Search content")
        self.content_cb.setChecked(True)
        options_layout.addWidget(self.content_cb)
        options_layout.addWidget(QLabel("Tag:"))
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All")
        self.tag_filter.setMinimumWidth(120)
        self._refresh_tag_filter()
        options_layout.addWidget(self.tag_filter)
        options_layout.addWidget(QLabel("Saved:"))
        self.saved_combo = QComboBox()
        self.saved_combo.setMinimumWidth(140)
        self.saved_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.saved_combo.customContextMenuRequested.connect(self._on_saved_context_menu)
        self.saved_combo.activated.connect(self._on_load_saved_search)
        options_layout.addWidget(self.saved_combo)
        self._refresh_saved_searches()
        self.btn_save_search = QPushButton("💾 Save")
        self.btn_save_search.clicked.connect(self._on_save_search)
        self.btn_save_search.setEnabled(False)
        options_layout.addWidget(self.btn_save_search)
        options_layout.addStretch()
        self.index_btn = QPushButton("🗂️ Build Index")
        self.index_btn.clicked.connect(self._on_index)
        options_layout.addWidget(self.index_btn)
        self.export_btn = QPushButton("📤 Export Results")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        options_layout.addWidget(self.export_btn)
        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self._clear_results)
        options_layout.addWidget(self.clear_btn)
        self.clear_history_btn = QPushButton("🗑 Clear History")
        self.clear_history_btn.setToolTip("Clear search history")
        self.clear_history_btn.clicked.connect(self._clear_search_history)
        options_layout.addWidget(self.clear_history_btn)
        layout.addLayout(options_layout)

    def _create_progress_bar(self, layout):
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)
        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.setObjectName("btnDanger")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        progress_layout.addWidget(self.btn_cancel)
        layout.addLayout(progress_layout)

    def _create_results_list(self, layout):
        self.result_list = QListWidget()
        self.result_list.setAlternatingRowColors(True)
        layout.addWidget(self.result_list, 1)

    def _create_status(self, layout):
        self.stats_label = QLabel("Please open a folder and build the index first")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        """Connect signals"""
        self.status_message.connect(self._on_status_message)
        self.progress_updated.connect(self.progress_bar.setValue)
        self.indexing_finished.connect(self._on_indexing_finished)
        self.search_results_ready.connect(self._display_results)
        self.cancel_acknowledged.connect(self._on_cancel_done)

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

    def _load_search_history(self):
        """Load search history from settings and populate dropdown."""
        history: list[str] = []
        if self.state:
            history = self.state.search_history
        else:
            from filepilot.core import config

            history = list(config.load().get("search_history", []))
        self.search_input.clear()
        for q in history:
            self.search_input.addItem(q)

    def _save_search_history(self, query: str):
        """Append query to search history in settings (max 20)."""
        if self.state:
            self.state.add_search_history(query, 20)
            history = self.state.search_history
        else:
            from filepilot.core import config

            max_history = 20
            settings = config.load()
            history = list(settings.get("search_history", []))
            if query in history:
                history.remove(query)
            history.insert(0, query)
            settings["search_history"] = history[:max_history]
            config.save(settings)

        # Refresh dropdown items without clearing current text
        current_text = self.search_input.currentText()
        self.search_input.clear()
        for q in history[:max_history]:
            self.search_input.addItem(q)
        self.search_input.setEditText(current_text)

    @Slot()
    def _clear_search_history(self):
        """Clear all search history."""
        if self.state:
            self.state.set("search_history", [])
        else:
            from filepilot.core import config

            settings = config.load()
            settings["search_history"] = []
            config.save(settings)
        self.search_input.clear()
        self.status_message.emit("Search history cleared.")

    # ── Saved Searches ──────────────────────────────────────────────────────

    def _refresh_saved_searches(self):
        saved: list[dict] = []
        if self.state:
            saved = self.state.saved_searches
        else:
            from filepilot.core import config

            saved = config.load().get("saved_searches", [])
        current = self.saved_combo.currentText()
        self.saved_combo.blockSignals(True)
        self.saved_combo.clear()
        self.saved_combo.addItem("(saved searches)")
        for s in saved:
            self.saved_combo.addItem(s.get("name", "?"))
        self.saved_combo.blockSignals(False)
        idx = self.saved_combo.findText(current)
        if idx >= 0:
            self.saved_combo.setCurrentIndex(idx)

    @Slot()
    def _on_save_search(self):
        from PySide6.QtWidgets import QInputDialog

        query = self.search_input.currentText().strip()
        if not query:
            return
        name, ok = QInputDialog.getText(self, "Save Search", "Search name:", text=query)
        if not ok or not name.strip():
            return

        saved: list[dict] = []
        if self.state:
            saved = self.state.saved_searches
        else:
            from filepilot.core import config

            saved = config.load().get("saved_searches", [])
        entry = {
            "name": name.strip(),
            "query": query,
            "fuzzy": self.fuzzy_cb.isChecked(),
            "content_search": self.content_cb.isChecked(),
            "tag_filter": self.tag_filter.currentText()
            if self.tag_filter.currentText() != "All"
            else "",
        }
        for s in saved:
            if s["name"] == entry["name"]:
                s.update(entry)
                break
        else:
            saved.append(entry)

        if self.state:
            self.state.set_saved_searches(saved)
        else:
            from filepilot.core import config

            settings = config.load()
            settings["saved_searches"] = saved
            config.save(settings)
        self._refresh_saved_searches()
        self.status_message.emit(f"Saved search: {name.strip()}")

    @Slot()
    def _on_load_saved_search(self, index: int):
        if index <= 0:
            return
        saved: list[dict] = []
        if self.state:
            saved = self.state.saved_searches
        else:
            from filepilot.core import config

            saved = config.load().get("saved_searches", [])
        if index - 1 >= len(saved):
            return
        entry = saved[index - 1]
        self.search_input.setEditText(entry.get("query", ""))
        self.fuzzy_cb.setChecked(entry.get("fuzzy", True))
        self.content_cb.setChecked(entry.get("content_search", True))
        tag = entry.get("tag_filter", "")
        if tag:
            idx = self.tag_filter.findText(tag)
            if idx >= 0:
                self.tag_filter.setCurrentIndex(idx)
            else:
                self.tag_filter.setCurrentIndex(0)
        else:
            self.tag_filter.setCurrentIndex(0)
        self._on_search()

    @Slot()
    def _on_saved_context_menu(self, pos):
        index = self.saved_combo.currentIndex()
        if index <= 0:
            return
        saved: list[dict] = []
        if self.state:
            saved = self.state.saved_searches
        else:
            from filepilot.core import config

            saved = config.load().get("saved_searches", [])
        if index - 1 >= len(saved):
            return
        entry = saved[index - 1]

        from PySide6.QtWidgets import QInputDialog, QMenu

        menu = QMenu(self)
        rename_action = menu.addAction("✏ Rename")
        delete_action = menu.addAction("🗑 Delete")
        action = menu.exec(self.saved_combo.viewport().mapToGlobal(pos))
        if action is None:
            return

        if action == rename_action:
            new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=entry["name"])
            if ok and new_name.strip():
                entry["name"] = new_name.strip()
                if self.state:
                    self.state.set_saved_searches(saved)
                else:
                    from filepilot.core import config

                    config.save({"saved_searches": saved})
                self._refresh_saved_searches()
                self.status_message.emit(f"Renamed to: {new_name.strip()}")
        elif action == delete_action:
            saved.pop(index - 1)
            if self.state:
                self.state.set_saved_searches(saved)
            else:
                from filepilot.core import config

                settings = config.load()
                settings["saved_searches"] = saved
                config.save(settings)
            self._refresh_saved_searches()
            self.status_message.emit(f"Deleted: {entry['name']}")

    @Slot()
    def _on_search(self):
        """Execute search"""
        query = self.search_input.currentText().strip()
        if not query:
            return

        # Check index status
        stats = self.indexer.get_stats()
        if stats["indexed_files"] == 0:
            self.result_list.addItem(
                "⚠️ Index is empty. Please build the index first before searching.",
            )
            return  # Save to search history (after validation, before search)
        self._save_search_history(query)

        self._cancelled = False
        self._cancelling = False
        self.status_message.emit(f"Searching: {query} ...")
        self.search_btn.setEnabled(False)
        self.btn_cancel.setVisible(True)

        def search_worker():
            if self._cancelled:
                return

            # Check cache first
            from filepilot.core.search_cache import cache_results, get_cached_results

            cached = get_cached_results(query)
            if cached is not None:
                if not self._cancelled:
                    self.search_results_ready.emit(cached, query)
                return

            # Execute search
            results = self.indexer.search(
                query,
                fuzzy=self.fuzzy_cb.isChecked(),
                limit=100,
            )

            if self._cancelled:
                return

            cache_results(query, results)
            self.search_results_ready.emit(results, query)

        worker = Worker(search_worker)
        worker.signals.finished.connect(lambda _: None)
        self._pool.start(worker)

    def _refresh_tag_filter(self):
        current = self.tag_filter.currentText()
        self.tag_filter.clear()
        self.tag_filter.addItem("All")
        for tag in self.tag_manager.get_all_tags():
            self.tag_filter.addItem(tag)
        idx = self.tag_filter.findText(current)
        if idx >= 0:
            self.tag_filter.setCurrentIndex(idx)

    @Slot()
    def _display_results(self, results: list[dict], query: str):
        """Display search results"""
        self.result_list.clear()
        self.search_btn.setEnabled(True)
        self.btn_cancel.setVisible(False)
        self.btn_save_search.setEnabled(bool(results))
        self.export_btn.setEnabled(bool(results))

        selected_tag = self.tag_filter.currentText().strip()
        if selected_tag and selected_tag != "All":
            results = [
                r for r in results if self.tag_manager.has_tag(r.get("path", ""), selected_tag)
            ]

        if not results:
            item = QListWidgetItem(f'No results found for "{query}"')
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
                # Truncate on a space boundary to avoid breaking emoji/multi-byte chars
                hl = highlights
                if len(hl) > 100:
                    hl = hl[:100].rsplit(" ", 1)[0] + "…"
                display_text += f"\n   📌 {hl}"
            display_text += (
                f"\n   📂 {filepath}  |  {size_str}  |  {modified}  |  Match: {score:.0%}"
            )

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

    def _extract_file_content(self, file_info: FileInfo) -> str:
        """Extract searchable content from a file using registered extractors."""
        ext = file_info.extension.lower()
        extractor = _EXTRACTORS.get(ext)
        if extractor:
            try:
                return extractor.extract_text(file_info.path)  # type: ignore[no-any-return, attr-defined]
            except Exception:
                return ""
        # Try plugin extractors
        plugin_ext = get_plugin_manager().get_extractor_for(ext)
        if plugin_ext:
            try:
                text = plugin_ext.extract_text(file_info.path)
                if text:
                    return text
            except Exception as e:
                self.status_message.emit(f"⚠️ Plugin extractor error ({file_info.path.name}): {e}")
        # Fallback: try reading as text for small text files
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
                return ""
        return ""

    def _on_export(self):
        """Export search results as JSON or CSV"""
        results: list[dict] = []
        for i in range(self.result_list.count()):
            item = self.result_list.item(i)
            filepath = item.data(Qt.UserRole)
            if filepath:
                title = item.text().splitlines()[0]
                name = title.split("  ", 1)[1] if "  " in title else title
                results.append(
                    {
                        "name": name,
                        "path": filepath,
                        "text": item.toolTip(),
                    }
                )
        if not results:
            self.status_message.emit("No results to export")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Search Results",
            str(Path.home() / "search_results.json"),
            "JSON (*.json);;CSV (*.csv)",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            if path.suffix.lower() == ".json":
                path.write_text(
                    json.dumps(results, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                import csv

                with open(path, "w", newline="", encoding="utf-8") as fp:
                    writer = csv.DictWriter(fp, fieldnames=["name", "path", "text"])
                    writer.writeheader()
                    writer.writerows(results)
            self.status_message.emit(f"✅ Exported {len(results)} results")
        except Exception as e:
            self.status_message.emit(f"❌ Export failed: {e}")

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
                    self.cancel_acknowledged.emit()
                    return
                files.append(f)

            if self._cancelled:
                return

            total = len(files)

            # Build index
            indexed = self.indexer.index_files(
                files,
                content_extractor=self._extract_file_content,
                progress_callback=lambda i, msg: self.progress_updated.emit(
                    int(i / total * 100) if total else 0,
                ),
            )

            if not self._cancelled:
                self.indexing_finished.emit(indexed, str(dir_path))

        worker = Worker(index_worker)
        worker.signals.finished.connect(lambda _: None)
        self._pool.start(worker)

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
        from filepilot.core.search_cache import clear_search_cache

        clear_search_cache()
        status_msg = f"Indexing complete: {indexed} files indexed"
        self.status_message.emit(status_msg)
        self.index_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        stats = self.indexer.get_stats()
        self.stats_label.setText(
            f"📊 Index stats: {stats['indexed_files']} files, index size: {stats['index_size']}",
        )

        if self.event_bus:
            self.event_bus.index_completed.emit(dir_path)

    def _clear_results(self):
        """Clear search results"""
        self.result_list.clear()
        self.search_input.setEditText("")
        self.stats_label.setText("Ready")

    @Slot()
    def _on_status_message(self, msg: str):
        """Update status"""
        self.stats_label.setText(msg)
