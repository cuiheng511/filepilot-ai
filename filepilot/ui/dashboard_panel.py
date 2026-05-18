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

from filepilot.ui.base_panel import BasePanel


class DashboardPanel(BasePanel):
    """Dashboard panel — overview with recent activity, quick stats, and shortcuts"""

    open_folder = Signal(str)
    open_file = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("🏠 Dashboard")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Quick stats row
        stats_layout = QHBoxLayout()
        self.stat_total_files = self._make_stat_card("📊 Total Files", "—")
        self.stat_total_size = self._make_stat_card("💾 Total Size", "—")
        self.stat_categories = self._make_stat_card("📁 Categories", "—")
        self.stat_tags = self._make_stat_card("🏷️ Tags", "—")
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
        self.btn_open_folder = QPushButton("📂 Open Folder")
        self.btn_scan = QPushButton("🔄 Scan Files")
        self.btn_index = QPushButton("📇 Build Index")
        self.btn_find_duplicates = QPushButton("🔍 Find Duplicates")
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
        self._update_stat("📊 Total Files", f"{total_files:,}")
        self._update_stat("💾 Total Size", total_size)
        self._update_stat("📁 Categories", str(categories))
        self._update_stat("🏷️ Tags", str(tags))

    def update_recent_folders(self, folders: list[str]):
        """Update recent folders list"""
        self.recent_folders_list.clear()
        if not folders:
            item = QListWidgetItem("No recent folders")
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
            item = QListWidgetItem("No recent files")
            item.setForeground(Qt.gray)
            self.recent_files_list.addItem(item)
            return
        for file_path in files[:10]:
            path = Path(file_path)
            try:
                modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            except (OSError, FileNotFoundError):
                modified = "unknown"
            item = QListWidgetItem(f"📄 {path.name}")
            item.setToolTip(f"{file_path}\nModified: {modified}")
            item.setData(Qt.UserRole, file_path)
            self.recent_files_list.addItem(item)

    def _on_folder_double_click(self, item: QListWidgetItem):
        """Open double-clicked folder"""
        folder = item.data(Qt.UserRole)
        if folder:
            self.open_folder.emit(folder)

    def _on_file_double_click(self, item: QListWidgetItem):
        """Open double-clicked file"""
        file_path = item.data(Qt.UserRole)
        if file_path:
            self.open_file.emit(file_path)

    def set_current_dir(self, dir_path: str):
        """Set current directory for context"""
        pass
