"""Tabbed file browser — multi-tab wrapper around FileBrowserPanel"""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.core.file_scanner import FileScanner
from filepilot.ui.file_browser import FileBrowserPanel


class TabbedFileBrowser(QWidget):
    """Multi-tab file browser wrapping FileBrowserPanel instances."""

    file_opened = Signal(str)

    def __init__(
        self,
        scanner: FileScanner | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._scanner = scanner
        self._state = app_state
        self._event_bus = event_bus

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs)

        # "+" button for new tab
        self.btn_new_tab = QPushButton("+")
        self.btn_new_tab.setFixedSize(28, 28)
        self.btn_new_tab.setToolTip("New tab (Ctrl+T)")
        self.btn_new_tab.clicked.connect(lambda: self._add_new_tab())
        self._tabs.setCornerWidget(self.btn_new_tab)

        # Keyboard shortcuts
        self._setup_shortcuts()

        # Open first tab
        self._add_new_tab()

    def _setup_shortcuts(self):
        new_tab = QAction("New Tab", self)
        new_tab.setShortcut("Ctrl+T")
        new_tab.triggered.connect(lambda: self._add_new_tab())
        self.addAction(new_tab)
        close_tab = QAction("Close Tab", self)
        close_tab.setShortcut("Ctrl+W")
        close_tab.triggered.connect(lambda: self._close_tab(self._tabs.currentIndex()))
        self.addAction(close_tab)

    def _active(self) -> FileBrowserPanel | None:
        widget = self._tabs.currentWidget()
        if isinstance(widget, FileBrowserPanel):
            return widget
        return None

    def _add_new_tab(self, dir_path: str | None = None) -> FileBrowserPanel:
        panel = FileBrowserPanel(
            scanner=self._scanner,
            app_state=self._state,
            event_bus=self._event_bus,
        )
        panel.file_opened.connect(self.file_opened.emit)
        if dir_path:
            title = Path(dir_path).name
            panel.load_directory(dir_path)
        else:
            title = "New Tab"
        idx = self._tabs.addTab(panel, title)
        self._tabs.setCurrentIndex(idx)
        return panel

    def _close_tab(self, index: int):
        if self._tabs.count() <= 1:
            self._add_new_tab()
        self._tabs.removeTab(index)

    def _on_tab_changed(self, index: int):
        panel = self._tabs.widget(index)
        if isinstance(panel, FileBrowserPanel):
            self._tabs.setTabText(index, panel.current_dir.name if panel.current_dir else "New Tab")

    def load_directory(self, dir_path: str | Path):
        active = self._active()
        if active:
            active.load_directory(dir_path)
        else:
            self._add_new_tab(str(dir_path))
        idx = self._tabs.currentIndex()
        self._tabs.setTabText(idx, Path(dir_path).name)

    def scan_directory(self, dir_path: str | Path):
        active = self._active()
        if active:
            active.scan_directory(dir_path)

    def update_services(
        self,
        scanner: FileScanner | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
    ):
        if scanner is not None:
            self._scanner = scanner
        if app_state is not None:
            self._state = app_state
        if event_bus is not None:
            self._event_bus = event_bus
        for i in range(self._tabs.count()):
            panel = self._tabs.widget(i)
            if isinstance(panel, FileBrowserPanel):
                panel.update_services(scanner=scanner, app_state=app_state, event_bus=event_bus)

    @property
    def files(self):
        active = self._active()
        return active.files if active else []

    @property
    def categories(self):
        active = self._active()
        return active.categories if active else {}
