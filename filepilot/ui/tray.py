"""System Tray — Background watcher with system tray icon and notifications"""

import logging
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from filepilot.core.file_watcher import FileWatcher
from filepilot.core.indexer import FileIndexer
from filepilot.i18n import t
from filepilot.ui.notification import NotificationToast

logger = logging.getLogger("filepilot.tray")


class SystemTrayManager(QObject):
    """System tray manager with background file watcher and notifications.

    Provides:
    - System tray icon with context menu (open, settings, exit)
    - Background directory monitoring via FileWatcher
    - Incremental index updates on file changes
    - Toast notifications for file events
    """

    activated = Signal(bool)

    def __init__(self, main_window=None, services: dict | None = None, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._services = services or {}
        self._watcher: FileWatcher | None = None
        self._indexer: FileIndexer | None = None
        self._toast: NotificationToast | Callable[[str, str, int], None] | None = None
        self._tray_icon: QSystemTrayIcon | None = None
        self._watched_dirs: list[str] = []
        self._paused_dirs: list[str] = []

        self._setup_tray()
        self._setup_watcher()

    def _setup_tray(self):
        """Create system tray icon and context menu"""
        self._tray_icon = QSystemTrayIcon(self)

        # Try to load app icon
        icon_path = Path(__file__).parent.parent / "resources" / "app.ico"
        if icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            self._tray_icon.setIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))

        self._tray_icon.setToolTip(t("tray_tooltip"))

        # Context menu
        menu = QMenu()

        open_action = QAction(t("browse_title"), self)
        open_action.triggered.connect(self._on_show_window)
        menu.addAction(open_action)

        settings_action = QAction("⚙️ " + t("settings_title"), self)
        settings_action.triggered.connect(self._on_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        pause_action = QAction(t("tray_pause"), self)
        pause_action.setCheckable(True)
        pause_action.toggled.connect(self._on_toggle_watching)
        menu.addAction(pause_action)

        exit_action = QAction("✕ " + t("close"), self)
        exit_action.triggered.connect(self._on_exit)
        menu.addAction(exit_action)

        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _setup_watcher(self):
        """Setup file watcher and indexer from services"""
        self._watcher = self._services.get("watcher")
        self._indexer = self._services.get("indexer")
        self._toast = self._services.get("toast")

        if self._watcher:
            self._watcher.file_created.connect(self._on_file_event, Qt.QueuedConnection)
            self._watcher.file_modified.connect(self._on_file_event, Qt.QueuedConnection)
            self._watcher.file_deleted.connect(self._on_file_deleted, Qt.QueuedConnection)
            self._watcher.error_occurred.connect(self._on_error, Qt.QueuedConnection)

    def show(self):
        """Show the system tray icon"""
        if self._tray_icon:
            self._tray_icon.show()

    def hide(self):
        """Hide the system tray icon"""
        if self._tray_icon:
            self._tray_icon.hide()

    def is_visible(self) -> bool:
        """Check if tray icon is visible"""
        return self._tray_icon.isVisible() if self._tray_icon else False

    def watch_directory(self, dir_path: str):
        """Start watching a directory in background"""
        if self._watcher and str(dir_path) not in self._watched_dirs:
            self._watcher.watch(dir_path)
            self._watched_dirs.append(str(dir_path))
            logger.info("Now watching: %s", dir_path)
            self._show_toast(f"📂 Watching: {Path(dir_path).name}", "info", 2000)

    def unwatch_directory(self, dir_path: str):
        """Stop watching a directory"""
        if self._watcher:
            self._watcher.unwatch(dir_path)
            self._watched_dirs = [d for d in self._watched_dirs if d != str(dir_path)]

    def unwatch_all(self):
        """Stop watching all directories"""
        if self._watcher:
            self._watcher.unwatch_all()
            self._watched_dirs.clear()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon click"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_show_window()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            pass  # Context menu already shown

    def _on_show_window(self):
        """Restore/show the main window"""
        if self._main_window:
            self._main_window.show()
            self._main_window.raise_()
            self._main_window.activateWindow()

    def _on_settings(self):
        """Open settings dialog"""
        if self._main_window:
            self._main_window._on_settings()

    def _on_toggle_watching(self, paused: bool):
        """Toggle background watching"""
        if paused:
            self._paused_dirs = self._watched_dirs[:]
            self.unwatch_all()
            self._show_toast(t("tray_watching_paused"), "warning", 2000)
        else:
            # Re-watch previously watched directories
            for dir_path in self._paused_dirs[:]:
                self.watch_directory(dir_path)
            self._paused_dirs.clear()
            self._show_toast(t("tray_watching_resumed"), "info", 2000)

    def _on_file_event(self, file_path: str):
        """Handle file created/modified event"""
        from filepilot.core.file_scanner import FileScanner

        if self._indexer:
            try:
                path = Path(file_path)
                info = FileScanner.create_file_info(path)
                # Extract and index incrementally
                self._indexer.index_files([info])
            except Exception as e:
                logger.debug("Failed to index file %s: %s", file_path, e)
        else:
            # No indexer — skip auto-indexing
            logger.debug("No indexer available, skipping auto-index for: %s", file_path)

        # Debounce: only show toast if at least 3 seconds since last one
        now = time.time()
        if getattr(self, "_last_toast_time", 0) + 3 < now:
            self._last_toast_time = now
            self._show_toast(f"📄 Indexed: {Path(file_path).name}", "info", 1500)

    def _on_file_deleted(self, file_path: str):
        """Handle file deletion"""
        from contextlib import suppress

        if self._indexer:
            with suppress(Exception):
                self._indexer.remove_from_index(file_path)

    def _on_error(self, message: str):
        """Handle watcher errors"""
        logger.error("FileWatcher error: %s", message)
        self._show_toast(f"⚠️ {message}", "error", 3000)

    def _show_toast(self, text: str, level: str = "info", duration_ms: int = 3000):
        """Show a notification through either a toast widget or callback."""
        if not self._toast:
            return
        if callable(self._toast):
            self._toast(text, level, duration_ms)
        else:
            self._toast.show_message(text, level, duration_ms)

    def _on_exit(self):
        """Exit application"""
        self.unwatch_all()
        if self._main_window:
            self._main_window.close()
        QApplication.quit()
