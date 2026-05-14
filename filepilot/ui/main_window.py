"""FilePilot AI Main Window"""

import contextlib
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import QAction, QDragEnterEvent, QDragLeaveEvent, QDropEvent, QFont, QResizeEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QWidget,
)

from filepilot.core.file_watcher import FileWatcher
from filepilot.i18n import t
from filepilot.styles.manager import ThemeManager
from filepilot.ui.duplicates_panel import DuplicatesPanel
from filepilot.ui.file_browser import FileBrowserPanel
from filepilot.ui.index_panel import IndexPanel
from filepilot.ui.notification import NotificationToast
from filepilot.ui.organize_panel import OrganizePanel
from filepilot.ui.search_panel import SearchPanel
from filepilot.ui.settings_dialog import SettingsDialog
from filepilot.ui.summary_panel import SummaryPanel


class MainWindow(QMainWindow):
    """FilePilot AI Main Window"""

    def __init__(self, services: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("app_name") + " — " + t("app_subtitle"))
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # State
        self.current_dir: Path | None = None
        self.settings = self._load_settings()
        self.services = services or {}

        # Enable drag-and-drop of folders
        self.setAcceptDrops(True)

        # File watcher for auto-indexing
        self._watcher: FileWatcher | None = None

        # Build UI
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

        # Initialize theme manager (applies QSS globally with hot-reload)
        themes_dir = Path(__file__).parent.parent / "styles" / "themes"
        self._theme_mgr = ThemeManager(themes_dir)
        self._theme_mgr.apply_theme("dark")
        self._theme_mgr.styles_reloaded.connect(
            lambda: self.status_label.setText("🎨 Styles reloaded")
        )

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _setup_ui(self):
        """Build the main interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left navigation sidebar
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setObjectName("navSidebar")
        font = QFont()
        font.setPointSize(11)
        self.nav_list.setFont(font)

        # Nav items
        self._nav_items = {
            "browse": self._add_nav_item(t("nav_browse"), t("browse_desc")),
            "search": self._add_nav_item(t("nav_search"), t("search_desc")),
            "organize": self._add_nav_item(t("nav_organize"), t("organize_desc")),
            "duplicates": self._add_nav_item(t("nav_duplicates"), t("duplicates_desc")),
            "summary": self._add_nav_item(t("nav_summary"), t("summary_desc")),
            "index": self._add_nav_item(t("nav_index"), t("index_desc")),
        }

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # Right content area
        self.content_stack = QStackedWidget()

        # Panels (inject service instances to avoid recreation)
        scanner = self.services.get("scanner")
        indexer = self.services.get("indexer")
        organizer = self.services.get("organizer")
        finder = self.services.get("duplicate_finder")

        self.browse_panel = FileBrowserPanel(scanner=scanner)
        self.search_panel = SearchPanel(indexer=indexer, scanner=scanner)
        self.organize_panel = OrganizePanel(organizer=organizer, scanner=scanner)
        self.duplicates_panel = DuplicatesPanel(finder=finder, scanner=scanner)
        self.summary_panel = SummaryPanel(
            summarizer=self.services.get("summarizer"),
            local_ai=self.services.get("local_ai"),
            cloud_ai=self.services.get("cloud_ai"),
        )
        self.index_panel = IndexPanel(indexer=indexer, scanner=scanner)

        self.content_stack.addWidget(self.browse_panel)      # 0
        self.content_stack.addWidget(self.search_panel)      # 1
        self.content_stack.addWidget(self.organize_panel)    # 2
        self.content_stack.addWidget(self.duplicates_panel)  # 3
        self.content_stack.addWidget(self.summary_panel)     # 4
        self.content_stack.addWidget(self.index_panel)       # 5

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.content_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)

        # Drop highlight overlay — positioned on top of central widget
        self.drop_overlay = QFrame(self.centralWidget())
        self.drop_overlay.setObjectName("dropOverlay")
        self.drop_overlay.setStyleSheet(
            "QFrame#dropOverlay {"
            "  border: 3px solid #4a9eff;"
            "  background: rgba(74, 158, 255, 0.06);"
            "  border-radius: 6px;"
            "  margin: 2px;"
            "}"
        )
        self.drop_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.drop_overlay.hide()

        # Default to first item
        self.nav_list.setCurrentRow(0)

        # Notification toast
        self._toast = NotificationToast(self.centralWidget())

        # File watcher — connect signals for auto-index
        self._watcher = self.services.get("watcher")
        if self._watcher:
            self._watcher.file_created.connect(self._on_file_changed)
            self._watcher.file_modified.connect(self._on_file_changed)
            self._watcher.file_deleted.connect(self._on_file_deleted)

    def resizeEvent(self, event: QResizeEvent):
        """Keep drop overlay geometry in sync with central widget"""
        super().resizeEvent(event)
        if hasattr(self, "drop_overlay"):
            self.drop_overlay.setGeometry(self.centralWidget().rect())

    def _add_nav_item(self, text: str, tooltip: str) -> QListWidgetItem:
        """Add a navigation item"""
        item = QListWidgetItem(text)
        item.setToolTip(tooltip)
        item.setSizeHint(QSize(0, 45))
        self.nav_list.addItem(item)
        return item

    def _setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        open_action = QAction("📂 Open Folder...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_folder)
        file_menu.addAction(open_action)

        # Recent folders submenu
        self._recent_menu = file_menu.addMenu("Recent Folders")
        self._refresh_recent_menu()

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tool_menu = menubar.addMenu("&Tools")
        settings_action = QAction("⚙️ Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._on_settings)
        tool_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About FilePilot AI", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _refresh_recent_menu(self):
        """Refresh the Recent Folders submenu from settings"""
        self._recent_menu.clear()

        recent = self.settings.get("recent_dirs", [])
        if not recent:
            empty = QAction("(none)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)
        else:
            for path in recent[:10]:
                name = Path(path).name
                action = QAction(f"📁 {name}  ({path})", self)
                action.triggered.connect(lambda checked, p=path: self._on_recent_folder(p))
                self._recent_menu.addAction(action)

    @Slot()
    def _on_recent_folder(self, path: str):
        """Open a recently used folder"""
        if path and Path(path).is_dir():
            self._open_directory(path)

    def _setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        self.btn_open = QPushButton(t("browse_scan"))
        self.btn_open.clicked.connect(self._on_open_folder)
        toolbar.addWidget(self.btn_open)

        toolbar.addSeparator()

        self.btn_scan = QPushButton(t("browse_scan"))
        self.btn_scan.clicked.connect(self._on_scan)
        self.btn_scan.setEnabled(False)
        toolbar.addWidget(self.btn_scan)

        self.btn_index = QPushButton(t("index_build"))
        self.btn_index.clicked.connect(self._on_index)
        self.btn_index.setEnabled(False)
        toolbar.addWidget(self.btn_index)

        toolbar.addSeparator()

        self.btn_theme = QPushButton("🌙")
        self.btn_theme.setToolTip("Toggle dark/light theme")
        self.btn_theme.setCheckable(True)
        self.btn_theme.setChecked(True)
        self.btn_theme.clicked.connect(self._on_toggle_theme)
        toolbar.addWidget(self.btn_theme)

    def _setup_statusbar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(250)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts Ctrl+1~6 to switch panels"""
        panel_actions = [
            ("Ctrl+1", "File Browser", 0),
            ("Ctrl+2", "File Search", 1),
            ("Ctrl+3", "File Organizer", 2),
            ("Ctrl+4", "Duplicate Finder", 3),
            ("Ctrl+5", "AI Summary", 4),
            ("Ctrl+6", "File Index", 5),
        ]
        for shortcut, name, index in panel_actions:
            action = QAction(f"Switch to {name}", self)
            action.setShortcut(shortcut)
            action.triggered.connect(lambda checked, i=index: self._switch_to_panel(i))
            self.addAction(action)

    def _switch_to_panel(self, index: int):
        """Switch to specified panel"""
        self.content_stack.setCurrentIndex(index)
        self.nav_list.setCurrentRow(index)

    def _load_settings(self) -> dict:
        """Load settings (unified via app.load_settings)"""
        from filepilot.app import load_settings as _load
        settings = _load()
        # Add MainWindow default values
        settings.setdefault("recent_dirs", [])
        return settings

    def _save_settings(self):
        """Save settings — API key stored in system keyring, rest in JSON"""
        import json

        from filepilot.app import _save_api_key_to_keyring

        settings_path = Path.home() / ".filepilot" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Save API key to system keyring, remove from JSON
        api_key = self.settings.get("ai_api_key", "")
        if api_key:
            _save_api_key_to_keyring(api_key)
        # Remove key from JSON payload (loaded via keyring on next startup)
        save_data = {k: v for k, v in self.settings.items() if k != "ai_api_key"}

        with contextlib.suppress(Exception):
            settings_path.write_text(
                json.dumps(save_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    @Slot()
    def _on_nav_changed(self, index: int):
        """Navigation changed"""
        self.content_stack.setCurrentIndex(index)
        names = ["Browse", "Search", "Organize", "Duplicates", "Summary", "Index"]
        if 0 <= index < len(names):
            self.status_label.setText(f"Current: {names[index]}")

    def _open_directory(self, dir_path: str):
        """Shared logic: open a directory and notify the browse panel"""
        self.current_dir = Path(dir_path)
        self.btn_scan.setEnabled(True)
        self.btn_index.setEnabled(True)

        # Save to recent directories
        recent = self.settings.get("recent_dirs", [])
        if dir_path in recent:
            recent.remove(dir_path)
        recent.insert(0, dir_path)
        self.settings["recent_dirs"] = recent[:10]
        self._save_settings()
        self._refresh_recent_menu()

        # Start watching for auto-index
        if self._watcher:
            self._watcher.watch(dir_path)

        # Notify browse panel
        self.browse_panel.load_directory(dir_path)

    @Slot()
    def _on_open_folder(self):
        """Open folder dialog"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", str(self.current_dir or Path.home())
        )
        if dir_path:
            self._open_directory(dir_path)
            self.status_label.setText(f"Opened: {dir_path}")

    def _on_file_changed(self, file_path: str):
        """Handle file created/modified — incremental index update"""
        from filepilot.core.file_scanner import FileInfo

        if not self.current_dir:
            return
        path = Path(file_path)
        if not path.exists() or not path.is_relative_to(self.current_dir):
            return
        # Only index supported file types
        import mimetypes

        from filepilot.core.file_scanner import (
            get_file_category,
            get_file_created_time,
            get_file_modified_time,
            get_file_size_str,
        )
        ext = path.suffix.lower()
        if ext and ext.lstrip(".").lower() in (
            "pdf", "md", "markdown", "mdx", "py", "js", "ts", "jsx", "tsx",
            "java", "cpp", "c", "h", "hpp", "cs", "go", "rs", "rb", "php",
            "swift", "kt", "scala", "sql", "sh", "bash", "ps1", "bat", "pl",
            "lua", "r", "m", "dart", "vue", "svelte", "docx", "xlsx", "pptx",
            "txt", "log", "ini", "cfg", "toml", "yaml", "yml", "json", "xml", "csv",
        ):
            try:
                stat = path.stat()
            except OSError:
                return
            info = FileInfo(
                path=path,
                name=path.name,
                extension=ext,
                size_bytes=stat.st_size,
                size_str=get_file_size_str(stat.st_size),
                category=get_file_category(path),
                mime_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream",
                modified_time=get_file_modified_time(path),
                created_time=get_file_created_time(path),
                is_directory=path.is_dir(),
            )
            self.index_panel.indexer.index_files(
                [info],
                content_extractor=self.search_panel._extract_file_content,
            )

    def _on_file_deleted(self, file_path: str):
        """Handle file deletion — remove from index"""
        if self.current_dir:
            path = Path(file_path)
            if path.is_relative_to(self.current_dir):
                self.index_panel.indexer.remove_from_index(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drag events — show drop highlight when URLs are detected"""
        if event.mimeData().hasUrls():
            self.drop_overlay.show()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        """Hide drop highlight when drag leaves window"""
        self.drop_overlay.hide()
        event.accept()

    def dropEvent(self, event: QDropEvent):
        """Handle dropped folder or single file — open directory in file browser"""
        self.drop_overlay.hide()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]

        for p in paths:
            if Path(p).is_dir():
                self._open_directory(p)
                self.status_label.setText(f"Opened: {p}")
                event.acceptProposedAction()
                return

        # No directory found — open parent directory of the first dropped file
        if len(paths) == 1 and Path(paths[0]).is_file():
            parent = Path(paths[0]).parent
            self._open_directory(str(parent))
            self.status_label.setText(f"📂 {parent.name}  (from dropped file: {Path(paths[0]).name})")
            event.acceptProposedAction()

    @Slot()
    def _on_scan(self):
        """Scan files"""
        if self.current_dir:
            self.browse_panel.scan_directory(self.current_dir)

    @Slot()
    def _on_index(self):
        """Build index"""
        if self.current_dir:
            self.index_panel.index_directory(self.current_dir)
            self.nav_list.setCurrentRow(5)  # Switch to index panel

    @Slot()
    def _on_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            self._save_settings()
            self._recreate_services()
            self.status_label.setText("Settings saved — AI engine updated")

    @Slot()
    def _on_about(self):
        """About dialog"""
        QMessageBox.about(
            self,
            "About FilePilot AI",
            "<h2>FilePilot AI v0.1.0</h2>"
            "<p>Smart file manager — automatically organize, categorize, and search your local files.</p>"
            "<p>Features: file type recognition, auto-rename, auto-categorize<br>"
            "PDF/Markdown summarization, file indexing, deduplication, AI search</p>"
            "<hr>"
            "<p>Built with ❤️ using PySide6 + Whoosh + Ollama</p>"
        )

    @Slot()
    def _on_toggle_theme(self, checked: bool):
        """Toggle dark/light theme"""
        theme = "dark" if checked else "light"
        self._theme_mgr.apply_theme(theme)
        self.btn_theme.setText("🌙" if checked else "☀️")
        self.settings["theme"] = theme
        self._save_settings()

    def _show_progress(self, visible: bool, value: int = 0, maximum: int = 100):
        """Show/hide progress bar"""
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setValue(value)

    def _update_progress(self, value: int):
        """Update progress"""
        self.progress_bar.setValue(value)

    def _notify(self, text: str, level: str = "info", duration_ms: int = 3000):
        """Show a non-blocking notification toast"""
        if hasattr(self, "_toast"):
            self._toast.show_message(text, level, duration_ms)

    def _recreate_services(self):
        """Update service instances after settings change (no panel recreation needed)"""
        from filepilot.app import create_services
        new_services = create_services(self.settings)
        self.services = new_services

        # Update watcher reference and reconnect signals
        old_watcher = self._watcher
        self._watcher = new_services.get("watcher")
        if old_watcher:
            with contextlib.suppress(RuntimeError, TypeError):
                old_watcher.file_created.disconnect(self._on_file_changed)
            with contextlib.suppress(RuntimeError, TypeError):
                old_watcher.file_modified.disconnect(self._on_file_changed)
            with contextlib.suppress(RuntimeError, TypeError):
                old_watcher.file_deleted.disconnect(self._on_file_deleted)
            old_watcher.stop()
        if self._watcher:
            self._watcher.file_created.connect(self._on_file_changed)
            self._watcher.file_modified.connect(self._on_file_changed)
            self._watcher.file_deleted.connect(self._on_file_deleted)
            if self.current_dir:
                self._watcher.watch(self.current_dir)
        self.browse_panel.update_services(scanner=new_services.get("scanner"))
        self.search_panel.update_services(
            scanner=new_services.get("scanner"),
            indexer=new_services.get("indexer"),
        )
        self.organize_panel.update_services(
            scanner=new_services.get("scanner"),
            organizer=new_services.get("organizer"),
        )
        self.duplicates_panel.update_services(
            scanner=new_services.get("scanner"),
            finder=new_services.get("duplicate_finder"),
        )
        self.summary_panel.update_services(
            summarizer=new_services.get("summarizer"),
            local_ai=new_services.get("local_ai"),
            cloud_ai=new_services.get("cloud_ai"),
        )
        self.index_panel.update_services(
            scanner=new_services.get("scanner"),
            indexer=new_services.get("indexer"),
        )

    # ===== Placeholder panels =====
