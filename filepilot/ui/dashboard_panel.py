"""Dashboard panel — overview with recent activity, quick stats, and shortcuts"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.i18n import t
from filepilot.ui.base_panel import BasePanel


class DashboardPanel(BasePanel):
    """Dashboard panel — overview with recent activity, quick stats, and shortcuts"""

    open_folder = Signal(str)
    open_file = Signal(str)

    def __init__(
        self, app_state: AppState | None = None, event_bus: EventBus | None = None, parent=None
    ):
        super().__init__(parent)
        self.state = app_state
        self.event_bus = event_bus
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel(t("dashboard_title"))
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Quick stats row
        stats_layout = QHBoxLayout()
        self.stat_total_files = self._make_stat_card(t("dashboard_total_files"), "—")
        self.stat_total_size = self._make_stat_card(t("disk_total"), "—")
        self.stat_categories = self._make_stat_card(t("dashboard_categories"), "—")
        self.stat_tags = self._make_stat_card(t("dashboard_tags"), "—")
        stats_layout.addWidget(self.stat_total_files)
        stats_layout.addWidget(self.stat_total_size)
        stats_layout.addWidget(self.stat_categories)
        stats_layout.addWidget(self.stat_tags)
        layout.addLayout(stats_layout)

        # Main content: scrollable area with sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # Quick actions
        actions_section = self._create_section("⚡ Quick Actions")
        actions_layout = QHBoxLayout()
        self.btn_open_folder = QPushButton(t("dashboard_open_folder"))
        self.btn_scan = QPushButton(t("browse_scan"))
        self.btn_index = QPushButton(t("dashboard_build_index"))
        self.btn_find_duplicates = QPushButton(t("dashboard_find_duplicates"))
        actions_layout.addWidget(self.btn_open_folder)
        actions_layout.addWidget(self.btn_scan)
        actions_layout.addWidget(self.btn_index)
        actions_layout.addWidget(self.btn_find_duplicates)
        actions_layout.addStretch()
        actions_section.layout().addLayout(actions_layout)
        content_layout.addWidget(actions_section)

        # Recent folders
        self.recent_folders_section = self._create_section("📁 Recent Folders")
        self.recent_folders_list = QListWidget()
        self.recent_folders_list.setAlternatingRowColors(True)
        self.recent_folders_list.itemDoubleClicked.connect(self._on_folder_double_click)
        self.recent_folders_section.layout().addWidget(self.recent_folders_list)
        content_layout.addWidget(self.recent_folders_section)

        # Recent files
        self.recent_files_section = self._create_section("📄 Recent Files")
        self.recent_files_list = QListWidget()
        self.recent_files_list.setAlternatingRowColors(True)
        self.recent_files_list.itemDoubleClicked.connect(self._on_file_double_click)
        self.recent_files_section.layout().addWidget(self.recent_files_list)
        content_layout.addWidget(self.recent_files_section)

        # Keyboard shortcuts
        shortcuts_section = self._create_section("⌨️ Keyboard Shortcuts")
        shortcuts_grid = QGridLayout()
        shortcuts = [
            ("Ctrl+1..9", "Switch panels"),
            ("Ctrl+O", "Open folder"),
            ("Ctrl+Shift+F", "Global search"),
            ("Ctrl+,", "Settings"),
            ("Ctrl+Q", "Quit"),
            ("Ctrl+L", "Toggle dark/light theme"),
        ]
        for i, (key, desc) in enumerate(shortcuts):
            shortcuts_grid.addWidget(QLabel(f"<b>{key}</b>"), i, 0)
            shortcuts_grid.addWidget(QLabel(desc), i, 1)
        shortcuts_section.layout().addLayout(shortcuts_grid)
        content_layout.addWidget(shortcuts_section)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

    def _create_section(self, title: str) -> QFrame:
        """Create a collapsible section"""
        frame = QFrame()
        frame.setObjectName("dashboardSection")
        frame.setStyleSheet(
            "QFrame#dashboardSection {"
            "  background: rgba(255, 255, 255, 0.03);"
            "  border: 1px solid rgba(255, 255, 255, 0.08);"
            "  border-radius: 8px;"
            "  padding: 12px;"
            "}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        return frame

    def update_stats(
        self, total_files: int = 0, total_size: str = "—", categories: int = 0, tags: int = 0
    ):
        """Update dashboard statistics"""
        self._update_stat(t("dashboard_total_files"), f"{total_files:,}")
        self._update_stat(t("disk_total"), total_size)
        self._update_stat(t("dashboard_categories"), str(categories))
        self._update_stat(t("dashboard_tags"), str(tags))

    def update_recent_folders(self, folders: list[str]):
        """Update recent folders list"""
        self.recent_folders_list.clear()
        if not folders:
            item = QListWidgetItem(t("dashboard_no_recent_folders"))
            item.setForeground(Qt.gray)
            self.recent_folders_list.addItem(item)
            return
        for folder in folders[:10]:
            path = Path(folder)
            item = QListWidgetItem(f"📁 {path.name}")
            item.setToolTip(folder)
            item.setData(Qt.UserRole, folder)
            self.recent_folders_list.addItem(item)

    def update_recent_files(self, files: list[str]):
        """Update recent files list"""
        self.recent_files_list.clear()
        if not files:
            item = QListWidgetItem(t("dashboard_no_recent_files"))
            item.setForeground(Qt.gray)
            self.recent_files_list.addItem(item)
            return
        for file_path in files[:10]:
            path = Path(file_path)
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            except (OSError, FileNotFoundError):
                modified = t("dashboard_unknown")
            item = QListWidgetItem(f"📄 {path.name}")
            item.setToolTip(f"{file_path}\nModified: {modified}")
            item.setData(Qt.UserRole, file_path)
            self.recent_files_list.addItem(item)

    def _on_folder_double_click(self, item: QListWidgetItem):
        """Open double-clicked folder"""
        folder = item.data(Qt.UserRole)
        if folder:
            self.open_folder.emit(folder)
            if self.event_bus:
                self.event_bus.open_folder_requested.emit(folder)

    def _on_file_double_click(self, item: QListWidgetItem):
        """Open double-clicked file"""
        file_path = item.data(Qt.UserRole)
        if file_path:
            self.open_file.emit(file_path)
            if self.event_bus:
                self.event_bus.open_file_requested.emit(file_path)

    def set_current_dir(self, dir_path: str):
        """Set current directory for context — update recent folders and stats"""
        if not dir_path:
            return
        if self.state:
            self.state.add_recent_dir(dir_path)
        # Quick file count in the directory
        try:
            p = Path(dir_path)
            if p.is_dir():
                files = sum(1 for _ in p.rglob("*") if _.is_file())
                total_size = sum(
                    _.stat().st_size for _ in p.rglob("*") if _.is_file()
                )
                from filepilot.utils.file_utils import get_file_size_str
                self.update_stats(total_files=files, total_size=get_file_size_str(total_size))
        except (OSError, PermissionError):
            pass
