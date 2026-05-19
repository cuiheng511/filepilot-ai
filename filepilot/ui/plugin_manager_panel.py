"""Plugin Manager panel — manage file extractor plugins."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from filepilot.core.plugin_system import PluginManager
from filepilot.ui.base_panel import BasePanel


class PluginManagerPanel(BasePanel):
    """Plugin Manager panel — manage file extractor plugins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugin_manager = PluginManager()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("\U0001f50c Plugin Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel(
            "Manage file content extractor plugins. "
            "Install custom Python plugins in ~/.filepilot/plugins/ to extend supported file types."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Info card
        info = QLabel(f"Plugins directory: {self.plugin_manager.plugins_dir}")
        info.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(info)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_discover = QPushButton("\U0001f50d Discover Plugins")
        self.btn_discover.clicked.connect(self._on_discover)
        self.btn_install_sample = QPushButton("\U0001f4e5 Install Sample")
        self.btn_install_sample.clicked.connect(self._on_install_sample)
        self.btn_open_dir = QPushButton("\U0001f4c2 Open Plugins Dir")
        self.btn_open_dir.clicked.connect(self._on_open_dir)
        toolbar.addWidget(self.btn_discover)
        toolbar.addWidget(self.btn_install_sample)
        toolbar.addWidget(self.btn_open_dir)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Plugin list
        self.plugin_list = QListWidget()
        self.plugin_list.setAlternatingRowColors(True)
        layout.addWidget(self.plugin_list, 1)

        self.stats_label = QLabel("Click 'Discover Plugins' to scan for installed plugins")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.status_message.connect(self.stats_label.setText)

    def _refresh_plugins(self):
        """Refresh the plugin list."""
        self.plugin_list.clear()
        extractors = self.plugin_manager.get_all_extractors()

        for ext in extractors:
            item = QListWidgetItem(f"\U0001f4e6 {ext.display_name}")
            tooltip = f"Class: {ext.name}\nVersion: {ext.version}\nDescription: {ext.description}"
            if hasattr(ext, "extensions"):
                tooltip += f"\nExtensions: {', '.join(ext.extensions)}"
            item.setToolTip(tooltip)
            item.setData(Qt.UserRole, ext.name)
            self.plugin_list.addItem(item)

        self.stats_label.setText(f"{len(extractors)} extractor plugin(s) loaded")

    @Slot()
    def _on_discover(self):
        """Scan plugins directory for extractor plugins."""
        self.plugin_manager.reload()
        self._refresh_plugins()
        count = len(self.plugin_manager.get_all_extractors())
        self.status_message.emit(f"\u2705 Discovered {count} plugin(s)")

    @Slot()
    def _on_install_sample(self):
        """Install a sample plugin for demonstration."""
        path = PluginManager.install_sample_plugin()
        self.plugin_manager.reload()
        self._refresh_plugins()
        self.status_message.emit(f"\u2705 Sample plugin installed: {path.name}")

    @Slot()
    def _on_open_dir(self):
        """Open the plugins directory in file explorer."""
        plugins_dir = self.plugin_manager.plugins_dir
        try:
            plugins_dir.mkdir(parents=True, exist_ok=True)
            import subprocess
            import sys

            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(plugins_dir)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(plugins_dir)])
            else:
                subprocess.Popen(["xdg-open", str(plugins_dir)])
        except Exception as e:
            self.status_message.emit(f"\u274c Failed to open directory: {e}")
