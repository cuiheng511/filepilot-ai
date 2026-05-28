"""Plugin Manager panel — manage file extractor plugins."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
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
        self.btn_browse_registry = QPushButton("\U0001f310 Browse Registry")
        self.btn_browse_registry.clicked.connect(self._on_browse_registry)
        toolbar.addWidget(self.btn_discover)
        toolbar.addWidget(self.btn_install_sample)
        toolbar.addWidget(self.btn_browse_registry)
        toolbar.addWidget(self.btn_open_dir)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Tabs: Installed | Registry
        from PySide6.QtWidgets import QTabWidget

        self._tabs = QTabWidget()

        # Installed plugins tab
        self.plugin_list = QListWidget()
        self.plugin_list.setAlternatingRowColors(True)
        self._tabs.addTab(self.plugin_list, "Installed")

        # Registry tab
        self.registry_list = QListWidget()
        self.registry_list.setAlternatingRowColors(True)
        self.registry_list.itemDoubleClicked.connect(self._on_registry_install)
        self._tabs.addTab(self.registry_list, "Available (Registry)")

        layout.addWidget(self._tabs, 1)

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

    @Slot()
    def _on_browse_registry(self):
        """Fetch and display available plugins from the registry."""
        self._tabs.setCurrentIndex(1)
        self.registry_list.clear()
        self.registry_list.addItem("Loading registry...")
        self.status_message.emit("Fetching plugin registry...")

        from PySide6.QtCore import QTimer

        from filepilot.core.plugin_registry import PluginRegistry

        self._registry = PluginRegistry()

        def on_fetched(entries):
            QTimer.singleShot(0, lambda: self._display_registry(entries))

        self._registry.fetch_async(callback=on_fetched)

    def _display_registry(self, entries):
        """Display registry entries in the list."""
        self.registry_list.clear()

        if not entries:
            self.registry_list.addItem("No plugins available in registry.")
            self.status_message.emit("Registry is empty or unreachable")
            return

        for entry in entries:
            status = "Installed" if entry.installed else "Available"
            if not entry.url and not entry.installed:
                status = "Built-in sample"
            elif entry.url and not entry.sha256 and not entry.installed:
                status = "Untrusted"
            icon = "\u2705" if entry.installed else "\U0001f4e6"
            exts = ", ".join(entry.extensions) if entry.extensions else ""
            text = f"{icon} {entry.display_name} v{entry.version} [{status}]"
            if exts:
                text += f"  ({exts})"

            item = QListWidgetItem(text)
            item.setToolTip(
                f"Name: {entry.name}\n"
                f"Author: {entry.author}\n"
                f"Description: {entry.description}\n"
                f"Extensions: {exts}\n"
                f"Source: {entry.url or 'built-in'}\n"
                f"SHA256: {entry.sha256 or 'not pinned'}\n"
                f"Status: {status}\n\n"
                f"Double-click to install/uninstall"
            )
            item.setData(Qt.UserRole, entry.name)
            if entry.installed:
                item.setForeground(QColor("#4caf50"))
            elif entry.url and not entry.sha256:
                item.setForeground(QColor("#c62828"))
            self.registry_list.addItem(item)

        installed = sum(1 for e in entries if e.installed)
        self.status_message.emit(f"Registry: {len(entries)} plugins ({installed} installed)")

    @Slot()
    def _on_registry_install(self, item: QListWidgetItem):
        """Install or uninstall a plugin from the registry."""
        if not hasattr(self, "_registry"):
            return

        name = item.data(Qt.UserRole)
        if not name:
            return

        entry = next((e for e in self._registry.entries if e.name == name), None)
        if not entry:
            return

        if entry.installed:
            # Uninstall
            if self._registry.uninstall_plugin(entry):
                self.status_message.emit(f"Uninstalled: {entry.display_name}")
                self.plugin_manager.reload()
                self._refresh_plugins()
                self._display_registry(self._registry.entries)
            else:
                self.status_message.emit(f"Failed to uninstall: {entry.display_name}")
        else:
            # Install
            if not entry.url:
                self.status_message.emit(
                    f"{entry.display_name} is a built-in plugin. Use 'Install Sample' instead."
                )
                return
            if not entry.sha256:
                self.status_message.emit(
                    f"Refusing unpinned plugin: {entry.display_name}. Registry entry needs SHA256."
                )
                return
            reply = QMessageBox.warning(
                self,
                "Install Plugin",
                (
                    f"Install {entry.display_name} from the community registry?\n\n"
                    "Plugins are Python code and can access local files. "
                    f"Source: {entry.url}\n"
                    f"SHA256: {entry.sha256 or 'not pinned'}"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            self.status_message.emit(f"Installing {entry.display_name}...")
            if self._registry.install_plugin(entry):
                self.status_message.emit(f"Installed: {entry.display_name}")
                self.plugin_manager.reload()
                self._refresh_plugins()
                self._display_registry(self._registry.entries)
            else:
                self.status_message.emit(f"Failed to install: {entry.display_name}")
