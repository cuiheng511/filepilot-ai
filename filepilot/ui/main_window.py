"""FilePilot AI Main Window"""

import contextlib
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Slot
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QFont,
    QResizeEvent,
)
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

from filepilot import __version__
from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.core.file_watcher import FileWatcher
from filepilot.core.service_container import ServiceContainer
from filepilot.i18n import t
from filepilot.styles.manager import ThemeManager
from filepilot.ui.dashboard_panel import DashboardPanel
from filepilot.ui.duplicates_panel import DuplicatesPanel
from filepilot.ui.favorites_panel import FavoritesPanel
from filepilot.ui.index_panel import IndexPanel
from filepilot.ui.notification import NotificationToast
from filepilot.ui.organize_panel import OrganizePanel
from filepilot.ui.plugin_manager_panel import PluginManagerPanel
from filepilot.ui.search_panel import SearchPanel
from filepilot.ui.settings_dialog import SettingsDialog
from filepilot.ui.shortcut_editor import DEFAULT_SHORTCUTS
from filepilot.ui.summary_panel import SummaryPanel
from filepilot.ui.tabbed_browser import TabbedFileBrowser
from filepilot.ui.tags_panel import TagsPanel


class MainWindow(QMainWindow):
    """FilePilot AI Main Window"""

    def __init__(
        self, services: ServiceContainer | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("app_name") + " — " + t("app_subtitle"))
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Core infrastructure
        self.state = AppState(self._load_settings(), self)
        self.services: ServiceContainer = services or ServiceContainer()
        self.event_bus = EventBus(self)
        self.current_dir: Path | None = None
        self._file_index_times: dict[str, float] = {}
        self._INDEX_DEBOUNCE_SEC = 2.0

        # Enable drag-and-drop of folders
        self.setAcceptDrops(True)

        # File watcher for auto-indexing
        self._watcher: FileWatcher | None = self.services.watcher

        # Build UI
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

        # Initialize theme manager (applies QSS globally with hot-reload)
        themes_dir = Path(__file__).parent.parent / "styles" / "themes"
        self._theme_mgr = ThemeManager(themes_dir)
        self._theme_mgr.apply_theme(self.state.theme)
        self._theme_mgr.styles_reloaded.connect(
            lambda: self.status_label.setText("🎨 Styles reloaded"),
        )

        # Connect event bus signals
        self._connect_event_bus()

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

        # Nav items with category grouping
        self._nav_items = {}
        self._nav_item_indices = {}
        self._nav_key_to_row: dict[str, int] = {}
        self._nav_row_to_stack_index: dict[int, int] = {}
        self._stack_index_to_nav_row: dict[int, int] = {}
        self._panel_indices: dict[str, int] = {}

        # ── Dashboard ──
        self._add_nav_item("🏠 Dashboard", "Overview and quick actions", "dashboard", 0)

        # ── Browse group ──
        self._add_nav_separator("📂 Browse")
        self._add_nav_item(t("nav_browse"), t("browse_desc"), "browse", 1)
        self._add_nav_item("⭐ Favorites", "Quick access to saved directories", "favorites", 2)

        # ── Search group ──
        self._add_nav_separator("🔍 Search")
        self._add_nav_item(t("nav_search"), t("search_desc"), "search", 3)
        self._add_nav_item("\U0001f3f7\ufe0f Tags", "File tags and color markers", "tags", 4)

        # ── Tools group ──
        self._add_nav_separator("🛠 Tools")
        self._add_nav_item(t("nav_organize"), t("organize_desc"), "organize", 5)
        self._add_nav_item(t("nav_duplicates"), t("duplicates_desc"), "duplicates", 6)
        self._add_nav_item(t("nav_summary"), t("summary_desc"), "summary", 7)
        self._add_nav_item(t("nav_index"), t("index_desc"), "index", 8)

        # ── Settings group ──
        self._add_nav_separator("⚙️ Settings")
        self._add_nav_item("\U0001f50c Plugins", "Extractor plugin manager", "plugins", 9)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # Right content area
        self.content_stack = QStackedWidget()

        # Panels (inject service instances from ServiceContainer)
        svc = self.services

        self.dashboard_panel = DashboardPanel(app_state=self.state, event_bus=self.event_bus)
        self.browse_panel = TabbedFileBrowser(
            scanner=svc.scanner, app_state=self.state, event_bus=self.event_bus
        )
        self.search_panel = SearchPanel(
            indexer=svc.indexer, scanner=svc.scanner, app_state=self.state, event_bus=self.event_bus
        )
        self.organize_panel = OrganizePanel(
            organizer=svc.organizer,
            scanner=svc.scanner,
            app_state=self.state,
            event_bus=self.event_bus,
        )
        self.duplicates_panel = DuplicatesPanel(
            finder=svc.duplicate_finder,
            scanner=svc.scanner,
            app_state=self.state,
            event_bus=self.event_bus,
        )
        self.summary_panel = SummaryPanel(
            summarizer=svc.summarizer,
            local_ai=svc.local_ai,
            cloud_ai=svc.cloud_ai,
            app_state=self.state,
            event_bus=self.event_bus,
        )
        self.index_panel = IndexPanel(
            indexer=svc.indexer, scanner=svc.scanner, app_state=self.state, event_bus=self.event_bus
        )
        self.favorites_panel = FavoritesPanel(app_state=self.state, event_bus=self.event_bus)
        self.tags_panel = TagsPanel()
        self.plugin_manager_panel = PluginManagerPanel()

        self.content_stack.addWidget(self.dashboard_panel)  # 0 - Dashboard
        self.content_stack.addWidget(self.browse_panel)  # 1 - Browse
        self.content_stack.addWidget(self.favorites_panel)  # 2 - Favorites
        self.content_stack.addWidget(self.search_panel)  # 3 - Search
        self.content_stack.addWidget(self.tags_panel)  # 4 - Tags
        self.content_stack.addWidget(self.organize_panel)  # 5 - Organize
        self.content_stack.addWidget(self.duplicates_panel)  # 6 - Duplicates
        self.content_stack.addWidget(self.summary_panel)  # 7 - Summary
        self.content_stack.addWidget(self.index_panel)  # 8 - Index
        self.content_stack.addWidget(self.plugin_manager_panel)  # 9 - Plugins

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
            "}",
        )
        self.drop_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.drop_overlay.hide()

        # Default to first item
        self.nav_list.setCurrentRow(0)

        # Notification toast
        self._toast = NotificationToast(self.centralWidget())

        # File watcher — connect signals for auto-index
        svc = self.services
        self._watcher = svc.watcher
        if self._watcher:
            self._watcher.file_created.connect(self._on_file_changed, Qt.QueuedConnection)
            self._watcher.file_modified.connect(self._on_file_changed, Qt.QueuedConnection)
            self._watcher.file_deleted.connect(self._on_file_deleted, Qt.QueuedConnection)

        # Track recently opened files
        self.browse_panel.file_opened.connect(self._on_file_opened)

        # Favorites panel — navigate to directory
        self.favorites_panel.navigate_to_directory.connect(lambda path: self._open_directory(path))

        # Dashboard panel — quick actions
        self.dashboard_panel.open_folder.connect(lambda path: self._open_directory(path))
        self.dashboard_panel.open_file.connect(self._on_open_file)
        self.dashboard_panel.btn_open_folder.clicked.connect(self._on_open_folder)
        self.dashboard_panel.btn_scan.clicked.connect(self._on_scan)
        self.dashboard_panel.btn_index.clicked.connect(self._on_index)
        self.dashboard_panel.btn_find_duplicates.clicked.connect(
            lambda: self._switch_to_panel(self._panel_indices.get("duplicates", 6))
        )

        # Initialize dashboard with recent data
        self.dashboard_panel.update_recent_folders(self.state.recent_dirs)
        self.dashboard_panel.update_recent_files(self.state.recent_files)

        # Connect AppState signals
        self.state.theme_changed.connect(self._on_theme_changed)
        self.state.recent_dirs_changed.connect(self._refresh_recent_menu)
        self.state.recent_files_changed.connect(self._refresh_recent_files_menu)

    def resizeEvent(self, event: QResizeEvent):
        """Keep drop overlay geometry in sync with central widget"""
        super().resizeEvent(event)
        if hasattr(self, "drop_overlay"):
            self.drop_overlay.setGeometry(self.centralWidget().rect())

    def closeEvent(self, event: QCloseEvent):
        """Cancel background operations on close."""
        if hasattr(self, "browse_panel"):
            for i in range(self.browse_panel._tabs.count()):
                panel = self.browse_panel._tabs.widget(i)
                if hasattr(panel, "_cancelled"):
                    panel._cancelled = True
        event.accept()

    def _connect_event_bus(self):
        """Wire event bus signals to handlers."""
        self.event_bus.open_folder_requested.connect(self._open_directory)
        self.event_bus.global_search_requested.connect(self._on_global_search)
        self.event_bus.theme_toggled.connect(self._on_toggle_theme)
        self.event_bus.settings_applied.connect(self._on_settings_applied)

    def _add_nav_item(
        self,
        text: str,
        tooltip: str,
        panel_key: str | None = None,
        stack_index: int | None = None,
    ) -> QListWidgetItem:
        """Add a navigation item"""
        item = QListWidgetItem(text)
        item.setToolTip(tooltip)
        item.setSizeHint(QSize(0, 45))
        self.nav_list.addItem(item)
        nav_row = self.nav_list.count() - 1
        self._nav_item_indices[text] = nav_row
        if panel_key is not None:
            self._nav_items[panel_key] = item
            self._nav_key_to_row[panel_key] = nav_row
        if stack_index is not None:
            self._nav_row_to_stack_index[nav_row] = stack_index
            self._stack_index_to_nav_row[stack_index] = nav_row
            if panel_key is not None:
                self._panel_indices[panel_key] = stack_index
        return item

    def _add_nav_separator(self, text: str):
        """Add a category separator in navigation"""
        item = QListWidgetItem(text)
        item.setSizeHint(QSize(0, 30))
        item.setFlags(Qt.NoItemFlags)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        item.setFont(font)
        self.nav_list.addItem(item)

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

        # Recent files submenu
        self._recent_files_menu = file_menu.addMenu(t("menu_recent_files"))
        self._refresh_recent_files_menu()

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

    def _refresh_recent_menu(self, _dummy=None):
        """Refresh the Recent Folders submenu from settings"""
        self._recent_menu.clear()

        recent = self.state.recent_dirs
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

    def _refresh_recent_files_menu(self, _dummy=None):
        """Refresh the Recent Files submenu from settings"""
        self._recent_files_menu.clear()

        recent = self.state.recent_files
        if not recent:
            empty = QAction("(none)", self)
            empty.setEnabled(False)
            self._recent_files_menu.addAction(empty)
        else:
            for path in recent:
                name = Path(path).name
                parent = Path(path).parent.name
                action = QAction(f"📄 {name}  ({parent})", self)
                action.setToolTip(path)
                action.triggered.connect(lambda checked, p=path: self._on_recent_file(p))
                self._recent_files_menu.addAction(action)

    @Slot()
    def _on_recent_file(self, path: str):
        """Open a recently used file"""
        if not path:
            return
        p = Path(path)
        if not p.exists():
            self.status_label.setText("File no longer exists: " + p.name)
            # Remove from recent files
            recent = self.state.recent_files
            recent = [x for x in recent if x != path]
            self.state.raw["recent_files"] = recent
            self.state.save()
            return
        try:
            fp = str(p)
            if sys.platform == "win32":
                os.startfile(fp)
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", fp])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", fp])
            self.status_label.setText("Opened: " + p.name)
        except Exception as e:
            self.status_label.setText(f"Failed to open: {e}")

    @Slot()
    def _on_file_opened(self, file_path: str):
        """Record a file as recently opened"""
        self.state.add_recent_file(file_path)
        self.state.save()

    def _setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        self.btn_open = QPushButton("📂 Open Folder")
        self.btn_open.clicked.connect(self._on_open_folder)
        toolbar.addWidget(self.btn_open)

        toolbar.addSeparator()

        self.btn_scan = QPushButton("🔄 Scan")
        self.btn_scan.clicked.connect(self._on_scan)
        self.btn_scan.setEnabled(False)
        toolbar.addWidget(self.btn_scan)

        self.btn_index = QPushButton("📇 Index")
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
        """Setup keyboard shortcuts to switch panels — load from config if available."""
        user_overrides = self.state.shortcuts

        shortcut_panels = {
            "File Browser": "browse",
            "File Search": "search",
            "File Organizer": "organize",
            "Duplicate Finder": "duplicates",
            "AI Summary": "summary",
            "File Index": "index",
            "Favorites": "favorites",
            "Tags": "tags",
            "Plugins": "plugins",
        }

        for name, default_key in DEFAULT_SHORTCUTS.items():
            shortcut = user_overrides.get(name, default_key)
            panel_key = shortcut_panels.get(name)
            stack_index = self._panel_indices.get(panel_key or "", 0)
            action = QAction(f"Switch to {name}", self)
            action.setObjectName(f"shortcut_{name.replace(' ', '_')}")
            action.setShortcut(shortcut)
            action.triggered.connect(lambda checked, i=stack_index: self._switch_to_panel(i))
            self.addAction(action)

        # Global search shortcut (Ctrl+Shift+F)
        search_action = QAction("Global Search", self)
        search_action.setShortcut("Ctrl+Shift+F")
        search_action.triggered.connect(self._on_global_search)
        self.addAction(search_action)

        # Theme toggle shortcut (Ctrl+L)
        theme_action = QAction("Toggle Theme", self)
        theme_action.setShortcut("Ctrl+L")
        theme_action.triggered.connect(
            lambda: self._on_toggle_theme(not self.btn_theme.isChecked())
        )
        self.addAction(theme_action)

    def _on_global_search(self):
        """Switch to search panel and focus search input"""
        search_index = self._panel_indices.get("search", 3)
        self._switch_to_panel(search_index)
        if hasattr(self.search_panel, "search_input"):
            self.search_panel.search_input.setFocus()

    def _switch_to_panel(self, index: int):
        """Switch to specified panel"""
        self.content_stack.setCurrentIndex(index)
        nav_row = self._stack_index_to_nav_row.get(index)
        if nav_row is not None and self.nav_list.currentRow() != nav_row:
            self.nav_list.setCurrentRow(nav_row)

    def _load_settings(self) -> dict:
        """Load settings (delegates to app.load_settings)"""
        from filepilot.app import load_settings as _load

        return _load()

    @Slot()
    def _on_nav_changed(self, index: int):
        """Navigation changed"""
        # Skip separator items (non-selectable)
        item = self.nav_list.item(index)
        if item and not (item.flags() & Qt.ItemIsEnabled):
            return

        stack_index = self._nav_row_to_stack_index.get(index)
        if stack_index is None:
            return

        self.content_stack.setCurrentIndex(stack_index)
        names = [
            "Dashboard",
            "Browse",
            "Favorites",
            "Search",
            "Tags",
            "Organize",
            "Duplicates",
            "Summary",
            "Index",
            "Plugins",
        ]
        if 0 <= stack_index < len(names) and hasattr(self, "status_label"):
            self.status_label.setText(f"Current: {names[stack_index]}")

    def _open_directory(self, dir_path: str):
        """Shared logic: open a directory and notify the browse panel"""
        self.current_dir = Path(dir_path)
        self._file_index_times.clear()
        self.btn_scan.setEnabled(True)
        self.btn_index.setEnabled(True)

        # Save to recent directories via AppState
        self.state.add_recent_dir(dir_path)
        self.state.save()
        self.state.current_dir = dir_path

        # Start watching for auto-index
        if self._watcher:
            self._watcher.watch(dir_path)

        # Notify browse panel
        self.browse_panel.load_directory(dir_path)

        # Update favorites panel with current directory
        self.favorites_panel.set_current_dir(dir_path)

        # Update dashboard with recent folders
        self.dashboard_panel.update_recent_folders(self.state.recent_dirs)

        # Update dashboard stats from browse panel
        if hasattr(self.browse_panel, "files"):
            total = len(self.browse_panel.files)
            self.dashboard_panel.update_stats(
                total_files=total,
                total_size="—",
                categories=len(getattr(self.browse_panel, "categories", {})),
                tags=self.tags_panel.tag_manager.get_tag_count(),
            )

    @Slot()
    def _on_open_folder(self):
        """Open folder dialog"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            str(self.current_dir or Path.home()),
        )
        if dir_path:
            self._open_directory(dir_path)
            self.status_label.setText(f"Opened: {dir_path}")

    @Slot()
    def _on_open_file(self, file_path: str):
        """Open a file from dashboard"""
        p = Path(file_path)
        if not p.exists():
            self.status_label.setText("File no longer exists: " + p.name)
            return
        try:
            fp = str(p)
            if sys.platform == "win32":
                os.startfile(fp)
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", fp])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", fp])
            self.status_label.setText("Opened: " + p.name)
        except Exception as e:
            self.status_label.setText(f"Failed to open: {e}")

    def _on_file_changed(self, file_path: str):
        """Handle file created/modified — incremental index update"""
        now = time.time()
        last = self._file_index_times.get(file_path, 0)
        if now - last < self._INDEX_DEBOUNCE_SEC:
            return
        self._file_index_times[file_path] = now

        from filepilot.core.file_scanner import FileScanner

        if not self.current_dir:
            return
        path = Path(file_path)
        if not path.exists() or not path.is_relative_to(self.current_dir):
            return
        # Only index supported file types
        ext = path.suffix.lower()
        if ext and ext.lstrip(".").lower() in (
            "pdf",
            "md",
            "markdown",
            "mdx",
            "py",
            "js",
            "ts",
            "jsx",
            "tsx",
            "java",
            "cpp",
            "c",
            "h",
            "hpp",
            "cs",
            "go",
            "rs",
            "rb",
            "php",
            "swift",
            "kt",
            "scala",
            "sql",
            "sh",
            "bash",
            "ps1",
            "bat",
            "pl",
            "lua",
            "r",
            "m",
            "dart",
            "vue",
            "svelte",
            "docx",
            "xlsx",
            "pptx",
            "txt",
            "log",
            "ini",
            "cfg",
            "toml",
            "yaml",
            "yml",
            "json",
            "xml",
            "csv",
        ):
            try:
                info = FileScanner.create_file_info(path)
            except OSError:
                return
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
            self.status_label.setText(
                f"📂 {parent.name}  (from dropped file: {Path(paths[0]).name})"
            )
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
            self._switch_to_panel(self._panel_indices.get("index", 8))

    @Slot()
    def _on_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(app_state=self.state, event_bus=self.event_bus, parent=self)
        if dialog.exec():
            self.state.update(dialog.get_settings())
            self.state.save()
            self._recreate_services()
            self.status_label.setText("Settings saved — AI engine updated")

    def _on_settings_applied(self, settings: dict):
        """Handle settings applied via event bus."""
        self.state.update(settings)
        self.state.save()
        self._recreate_services()

    @Slot()
    def _on_about(self):
        """About dialog"""
        QMessageBox.about(
            self,
            "About FilePilot AI",
            f"<h2>FilePilot AI v{__version__}</h2>"
            "<p>Smart file manager — organize, categorize, and search your local files.</p>"
            "<p>Features: file type recognition, auto-rename, auto-categorize<br>"
            "PDF/Markdown summarization, file indexing, deduplication, AI search</p>"
            "<hr>"
            "<p>Built with ❤️ using PySide6 + Whoosh + Ollama</p>",
        )

    @Slot()
    def _on_toggle_theme(self, checked: bool):
        """Toggle dark/light theme"""
        theme = "dark" if checked else "light"
        self._theme_mgr.apply_theme(theme)
        self.btn_theme.setText("🌙" if checked else "☀️")
        self.state.theme = theme
        self.state.save()

    @Slot()
    def _on_theme_changed(self, theme: str):
        """React to theme change from AppState."""
        is_dark = theme == "dark"
        self._theme_mgr.apply_theme(theme)
        self.btn_theme.setChecked(is_dark)
        self.btn_theme.setText("🌙" if is_dark else "☀️")

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
        from filepilot.app import create_service_container

        svc = create_service_container(self.state.raw)
        self.services = svc

        # Update watcher reference and reconnect signals
        old_watcher = self._watcher
        self._watcher = svc.watcher
        if old_watcher:
            with contextlib.suppress(RuntimeError, TypeError):
                old_watcher.file_created.disconnect(self._on_file_changed)
            with contextlib.suppress(RuntimeError, TypeError):
                old_watcher.file_modified.disconnect(self._on_file_changed)
            with contextlib.suppress(RuntimeError, TypeError):
                old_watcher.file_deleted.disconnect(self._on_file_deleted)
            old_watcher.stop()
        if self._watcher:
            self._watcher.file_created.connect(self._on_file_changed, Qt.QueuedConnection)
            self._watcher.file_modified.connect(self._on_file_changed, Qt.QueuedConnection)
            self._watcher.file_deleted.connect(self._on_file_deleted, Qt.QueuedConnection)
            if self.current_dir:
                self._watcher.watch(self.current_dir)
        self.browse_panel.update_services(scanner=svc.scanner)
        self.search_panel.update_services(scanner=svc.scanner, indexer=svc.indexer)
        self.organize_panel.update_services(scanner=svc.scanner, organizer=svc.organizer)
        self.duplicates_panel.update_services(scanner=svc.scanner, finder=svc.duplicate_finder)
        self.summary_panel.update_services(
            summarizer=svc.summarizer,
            local_ai=svc.local_ai,
            cloud_ai=svc.cloud_ai,
        )
        self.index_panel.update_services(scanner=svc.scanner, indexer=svc.indexer)

        # Refresh dashboard with recent data
        self.dashboard_panel.update_recent_folders(self.state.recent_dirs)
        self.dashboard_panel.update_recent_files(self.state.recent_files)

    # ===== Placeholder panels =====
