"""Settings dialog — AI engine and application configuration"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from filepilot.i18n import SUPPORTED_LANGUAGES, set_language, t
from filepilot.ui.shortcut_editor import ShortcutEditor


class SettingsDialog(QDialog):
    """Settings dialog"""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings — FilePilot AI")
        self.setMinimumSize(600, 450)
        self.resize(650, 500)

        self._settings = settings.copy()
        from filepilot.i18n import _current_lang

        self._current_lang = _current_lang
        self.setObjectName("SettingsDialog")
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Build the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Tabs
        tabs = QTabWidget()

        # AI settings tab
        ai_tab = self._create_ai_tab()
        tabs.addTab(ai_tab, "🤖 AI Engine")

        # General settings tab
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "⚙️ General")

        # Shortcuts tab
        shortcuts_tab = self._create_shortcuts_tab()
        tabs.addTab(shortcuts_tab, "⌨️ Shortcuts")

        # Scheduled tasks tab
        tasks_tab = self._create_tasks_tab()
        tabs.addTab(tasks_tab, "⏰ Scheduled Tasks")

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_ai_tab(self) -> QWidget:
        """Create AI settings tab (supports multiple Providers)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # AI Provider selection
        provider_group = QGroupBox(t("settings_provider"))
        provider_layout = QVBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(
            [
                "Ollama (Local)",
                "llama.cpp / LM Studio (Local)",
                "OpenAI (Cloud)",
                "Anthropic Claude (Cloud)",
                "Custom OpenAI Compatible",
            ]
        )
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Common settings (shared across all Providers)
        common_group = QGroupBox(t("settings_model"))
        common_layout = QFormLayout()
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.addItems(
            [
                "qwen2.5:7b",
                "qwen2.5:3b",
                "llama3.1:8b",
                "mistral:7b",
                "gpt-4o-mini",
                "gpt-4o",
                "claude-sonnet-4-20250514",
            ]
        )
        self.model_input.setCurrentText(self._settings.get("ai_model", "qwen2.5:7b"))
        self.api_base_input = QLineEdit()
        self.api_base_input.setPlaceholderText("http://localhost:11434")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_label = QLabel("API Key:")
        common_layout.addRow("Model:", self.model_input)
        common_layout.addRow("API Base URL:", self.api_base_input)
        common_layout.addRow(self.api_key_label, self.api_key_input)
        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        layout.addStretch()

        # Initialize default values
        provider = self._settings.get("ai_provider", "ollama")
        provider_map = {"ollama": 0, "llamacpp": 1, "openai": 2, "anthropic": 3, "custom": 4}
        self.provider_combo.setCurrentIndex(provider_map.get(provider, 0))
        self.api_key_input.setText(self._settings.get("ai_api_key", ""))

        return widget

    def _on_provider_changed(self, index: int):
        """Update default values when provider changes"""
        defaults = [
            ("http://localhost:11434", "qwen2.5:7b", False),
            ("http://localhost:8080", "default", False),
            ("https://api.openai.com/v1", "gpt-4o-mini", True),
            ("https://api.anthropic.com", "claude-sonnet-4-20250514", True),
            ("", "", True),
        ]
        url, model, need_key = defaults[index]
        self.api_base_input.setText(url)
        self.model_input.setCurrentText(model)
        self.api_key_input.setVisible(need_key)
        self.api_key_label.setVisible(need_key)

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Language settings
        lang_group = QGroupBox("Language / 语言")
        lang_layout = QFormLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([f"{v} ({k})" for k, v in SUPPORTED_LANGUAGES.items()])
        lang_layout.addRow("Language:", self.lang_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # Index settings
        index_group = QGroupBox("Index Settings")
        index_layout = QFormLayout()
        self.index_dir = QLineEdit(str(Path.home() / ".filepilot" / "index"))
        index_layout.addRow("Index storage path:", self.index_dir)
        index_group.setLayout(index_layout)
        layout.addWidget(index_group)

        # File scan settings
        scan_group = QGroupBox("File Scanning")
        scan_layout = QFormLayout()
        self.max_file_size = QLineEdit("500")
        self.max_file_size.setPlaceholderText("Unit: MB")
        scan_layout.addRow("Max file size (MB):", self.max_file_size)
        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)

        layout.addStretch()
        return widget

    def _create_shortcuts_tab(self) -> QWidget:
        """Create shortcuts customization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        overrides = self._settings.get("shortcuts", {})
        self.shortcut_editor = ShortcutEditor(overrides)
        layout.addWidget(self.shortcut_editor)

        return widget

    def _create_tasks_tab(self) -> QWidget:
        """Create scheduled tasks management tab"""

        from filepilot.core.task_scheduler import TaskScheduler

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        desc = QLabel(
            "Schedule automatic file scanning, indexing, duplicate finding, and organization.\n"
            "Tasks run in the background at specified times."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Toolbar
        toolbar_layout = QVBoxLayout()
        self.task_list = QListWidget()
        self.task_list.setAlternatingRowColors(True)
        toolbar_layout.addWidget(self.task_list, 1)

        btn_layout = QVBoxLayout()
        self.btn_add_task = QPushButton("➕ Add Task")
        self.btn_remove_task = QPushButton("❌ Remove Selected")
        self.btn_remove_task.setEnabled(False)
        btn_layout.addWidget(self.btn_add_task)
        btn_layout.addWidget(self.btn_remove_task)
        btn_layout.addStretch()
        toolbar_layout.addLayout(btn_layout)

        layout.addLayout(toolbar_layout, 1)

        self.scheduler = TaskScheduler()
        self._refresh_task_list()

        self.btn_add_task.clicked.connect(self._on_add_task)
        self.btn_remove_task.clicked.connect(self._on_remove_task)
        self.task_list.itemSelectionChanged.connect(
            lambda: self.btn_remove_task.setEnabled(
                len(self.task_list.selectedItems()) > 0
            )
        )

        return widget

    def _refresh_task_list(self):
        """Refresh the task list in settings dialog."""
        self.task_list.clear()
        tasks = self.scheduler.get_all_tasks()
        for task in tasks:
            from pathlib import Path

            status = "✅" if task.enabled else "⏸️"
            item = QListWidgetItem(
                f"{status} [{task.task_type.upper()}] {Path(task.directory).name} "
                f"- {task.schedule_type} at {task.schedule_time}"
            )
            item.setToolTip(
                f"ID: {task.task_id}\n"
                f"Directory: {task.directory}\n"
                f"Schedule: {task.schedule_type} at {task.schedule_time}\n"
                f"Enabled: {task.enabled}\n"
                f"Last Run: {task.last_run or 'Never'}"
            )
            item.setData(Qt.UserRole, task.task_id)
            self.task_list.addItem(item)

    def _on_add_task(self):
        """Add a new scheduled task via dialog."""
        from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QTimeEdit


        dialog = QDialog(self)
        dialog.setWindowTitle("Add Scheduled Task")
        dialog_layout = QFormLayout(dialog)

        type_combo = QComboBox()
        type_combo.addItems(["Scan", "Index", "Duplicate Finder", "Organize"])
        dialog_layout.addRow("Task Type:", type_combo)

        dir_layout = QVBoxLayout()
        dir_input = QLineEdit()
        dir_input.setPlaceholderText("Select directory...")
        dir_browse = QPushButton("Browse")
        dir_browse.clicked.connect(
            lambda: dir_input.setText(
                QFileDialog.getExistingDirectory(dialog, "Select Directory")
            )
        )
        dir_layout.addWidget(dir_input)
        dir_layout.addWidget(dir_browse)
        dialog_layout.addRow("Directory:", dir_layout)

        schedule_combo = QComboBox()
        schedule_combo.addItems(["Daily", "Weekly", "Monthly"])
        dialog_layout.addRow("Schedule:", schedule_combo)

        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        dialog_layout.addRow("Time:", time_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addRow(buttons)

        if dialog.exec():
            type_map = {
                "Scan": "scan",
                "Index": "index",
                "Duplicate Finder": "dedup",
                "Organize": "organize",
            }
            schedule_map = {"Daily": "daily", "Weekly": "weekly", "Monthly": "monthly"}
            self.scheduler.add_task(
                task_type=type_map[type_combo.currentText()],
                directory=dir_input.text().strip(),
                schedule_type=schedule_map[schedule_combo.currentText()],
                schedule_time=time_edit.time().toString("HH:mm"),
            )
            self._refresh_task_list()

    def _on_remove_task(self):
        """Remove selected task."""
        for item in self.task_list.selectedItems():
            task_id = item.data(Qt.UserRole)
            if task_id:
                self.scheduler.remove_task(task_id)
        self._refresh_task_list()

    def _parse_file_size(self, text: str) -> int:
        """Parse file size input, default to 500 on invalid input"""
        try:
            return int(text.strip()) if text.strip() else 500
        except (ValueError, AttributeError):
            return 500

    def _get_supported_lang_keys(self) -> list[str]:
        """Return list of supported language keys in combo order"""
        return list(SUPPORTED_LANGUAGES.keys())

    def _load_settings(self):
        """Load existing settings"""
        provider = self._settings.get("ai_provider", "ollama")
        provider_map = {"ollama": 0, "llamacpp": 1, "openai": 2, "anthropic": 3, "custom": 4}
        self.provider_combo.setCurrentIndex(provider_map.get(provider, 0))
        self.model_input.setCurrentText(self._settings.get("ai_model", "qwen2.5:7b"))
        self.api_base_input.setText(self._settings.get("ai_api_base", "http://localhost:11434"))
        self.api_key_input.setText(self._settings.get("ai_api_key", ""))
        self.max_file_size.setText(str(self._settings.get("max_file_size_mb", 500)))
        self.index_dir.setText(
            self._settings.get("index_dir", str(Path.home() / ".filepilot" / "index"))
        )
        # Set language combo
        current_lang = self._settings.get("language", "en")
        lang_items = [f"{v} ({k})" for k, v in SUPPORTED_LANGUAGES.items()]
        if current_lang in SUPPORTED_LANGUAGES:
            lang_label = f"{SUPPORTED_LANGUAGES[current_lang]} ({current_lang})"
            idx = lang_items.index(lang_label)
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)

    def get_settings(self) -> dict:
        """Get settings values, preserving keys not exposed in the dialog."""
        provider_names = ["ollama", "llamacpp", "openai", "anthropic", "custom"]
        provider = provider_names[self.provider_combo.currentIndex()]
        result = dict(self._settings)
        result.update(
            {
                "ai_mode": "local" if provider in ("ollama", "llamacpp") else "cloud",
                "ai_provider": provider,
                "ai_model": self.model_input.currentText(),
                "ai_api_base": self.api_base_input.text(),
                "ai_api_key": self.api_key_input.text(),
                "index_dir": self.index_dir.text(),
                "max_file_size_mb": self._parse_file_size(self.max_file_size.text()),
                "language": list(SUPPORTED_LANGUAGES.keys())[self.lang_combo.currentIndex()],
                "shortcuts": self.shortcut_editor.get_overrides()
            if hasattr(self, "shortcut_editor")
            else self._settings.get("shortcuts", {}),
            }
        )
        return result

    def accept(self):
        """Apply settings and close"""
        # Apply language change immediately
        new_lang = list(SUPPORTED_LANGUAGES.keys())[self.lang_combo.currentIndex()]
        if new_lang != self._current_lang:
            set_language(new_lang)
            self._current_lang = new_lang

        # Store new settings from controls
        self._settings = self.get_settings()

        super().accept()
