"""Settings dialog — AI engine and application configuration"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.i18n import SUPPORTED_LANGUAGES, set_language, t
from filepilot.ui.shortcut_editor import ShortcutEditor


class SettingsDialog(QDialog):
    """Settings dialog"""

    def __init__(
        self,
        settings: dict | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(t("settings_title"))
        self.setMinimumSize(680, 520)
        self.resize(760, 620)

        self.state = app_state
        self.event_bus = event_bus
        self._settings: dict[str, Any] = dict(settings or (app_state.raw if app_state else {}))
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
        tabs.addTab(ai_tab, t("settings_ai"))

        # General settings tab
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, t("settings_general"))

        # Shortcuts tab
        shortcuts_tab = self._create_shortcuts_tab()
        tabs.addTab(shortcuts_tab, t("settings_shortcuts"))

        # Scheduled tasks tab
        tasks_tab = self._create_tasks_tab()
        tabs.addTab(tasks_tab, t("settings_scheduled"))

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
        self.api_key_label = QLabel(t("settings_api_key"))
        common_layout.addRow(t("settings_model_label"), self.model_input)
        common_layout.addRow(t("settings_api_base"), self.api_base_input)
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
        """Create a consolidated application and system settings tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 12, 4)
        layout.setSpacing(16)

        preferences_group = QGroupBox("Preferences")
        preferences_layout = QFormLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([f"{v} ({k})" for k, v in SUPPORTED_LANGUAGES.items()])
        self.index_dir = QLineEdit(str(Path.home() / ".filepilot" / "index"))
        self.max_file_size = QLineEdit("500")
        self.max_file_size.setPlaceholderText("Unit: MB")
        preferences_layout.addRow("Language:", self.lang_combo)
        preferences_layout.addRow("Index storage path:", self.index_dir)
        preferences_layout.addRow("Max file size (MB):", self.max_file_size)
        preferences_group.setLayout(preferences_layout)
        layout.addWidget(preferences_group)

        system_group = QGroupBox("App & System")
        system_layout = QVBoxLayout()
        self.minimize_to_tray_cb = QCheckBox(t("minimize_to_tray"))
        self.close_to_tray_cb = QCheckBox(t("close_to_tray"))
        self.auto_start_cb = QCheckBox(t("auto_start"))
        system_layout.addWidget(self.minimize_to_tray_cb)
        system_layout.addWidget(self.close_to_tray_cb)
        system_layout.addWidget(self.auto_start_cb)
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        layout.addWidget(self._create_updates_group())

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

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
        self.btn_add_task = QPushButton(t("settings_add_task"))
        self.btn_remove_task = QPushButton(t("settings_remove_task"))
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
            lambda: self.btn_remove_task.setEnabled(len(self.task_list.selectedItems()) > 0)
        )

        return widget

    def _refresh_task_list(self):
        """Refresh the task list in settings dialog."""
        self.task_list.clear()
        tasks = self.scheduler.get_all_tasks()
        for task in tasks:
            from pathlib import Path

            status = "Enabled" if task.enabled else "Paused"
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
            lambda: dir_input.setText(QFileDialog.getExistingDirectory(dialog, "Select Directory"))
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

    def _create_updates_group(self) -> QGroupBox:
        """Create update management controls for the general tab."""
        from filepilot.updater import UpdateChecker

        updates_group = QGroupBox(t("settings_updates"))
        layout = QVBoxLayout(updates_group)
        layout.setSpacing(12)
        self.update_status_label = QLabel("Click 'Check for Updates' to check.")
        self.update_version_label = QLabel("")
        self.update_version_label.setWordWrap(True)
        layout.addWidget(self.update_version_label)
        layout.addWidget(self.update_status_label)

        # Progress bar (hidden initially)
        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        layout.addWidget(self.update_progress)

        # Buttons
        btn_layout = QHBoxLayout()
        self.check_update_btn = QPushButton(t("settings_check_updates"))
        self.check_update_btn.setObjectName("btnPrimary")
        self.download_update_btn = QPushButton(t("settings_download_install"))
        self.download_update_btn.setObjectName("btnSuccess")
        self.download_update_btn.setEnabled(False)
        self.download_update_btn.setVisible(False)
        btn_layout.addWidget(self.check_update_btn)
        btn_layout.addWidget(self.download_update_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._update_checker = UpdateChecker()
        self._update_download_path: Path | None = None

        self.check_update_btn.clicked.connect(self._on_check_updates)
        self.download_update_btn.clicked.connect(self._on_download_update)

        return updates_group

    def _on_check_updates(self):

        self.update_status_label.setText("Checking for updates...")
        self.check_update_btn.setEnabled(False)
        self.download_update_btn.setVisible(False)

        def _callback(result):
            QTimer.singleShot(0, lambda: self._on_update_result(result))

        self._update_checker.check_async(callback=_callback)

    def _on_update_result(self, result):
        from filepilot.updater import __version__ as current_ver

        self.check_update_btn.setEnabled(True)
        if result.error:
            self.update_status_label.setText(f"Check failed: {result.error}")
            self.download_update_btn.setVisible(False)
            return
        if result.has_update and result.release:
            self.update_status_label.setText(
                f"Update available: {result.release.version} (current: {current_ver})"
            )
            self.update_version_label.setText(
                f"{result.release.title}\n\n{result.release.body[:500]}"
            )
            self._update_download_url = result.release.download_url
            self.download_update_btn.setVisible(True)
            self.download_update_btn.setEnabled(True)
        else:
            self.update_status_label.setText(f"You're up to date! (v{current_ver})")
            self.update_version_label.setText("")
            self.download_update_btn.setVisible(False)

    def _on_download_update(self):
        if not hasattr(self, "_update_download_url") or not self._update_download_url:
            return
        from PySide6.QtWidgets import QFileDialog

        dest, _ = QFileDialog.getSaveFileName(
            self,
            t("settings_save_installer"),
            str(Path.home() / "Downloads" / t("settings_installer_name")),
            "All Files (*)",
        )
        if not dest:
            return

        self.download_update_btn.setEnabled(False)
        self.check_update_btn.setEnabled(False)
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)
        self.update_status_label.setText("Downloading...")

        def _progress(pct: int):
            QTimer.singleShot(0, lambda: self.update_progress.setValue(pct))

        def _download_thread():
            try:
                dl_path = self._update_checker.download(
                    self._update_download_url,
                    dest,
                    progress_callback=_progress,
                )
                QTimer.singleShot(0, lambda: self._on_download_finished(dl_path))
            except Exception as e:
                QTimer.singleShot(0, lambda err=e: self._on_download_error(str(err)))

        from threading import Thread

        Thread(target=_download_thread, daemon=True).start()

    def _on_download_finished(self, path: Path):
        self.update_progress.setValue(100)
        self.update_status_label.setText("Download complete!")
        self._update_download_path = path

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            t("settings_install_now"),
            "Download complete. Install now? The application will launch the installer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._update_checker.install(path)
            self.download_update_btn.setVisible(False)
            self.update_status_label.setText(
                "Installer launched. Please close FilePilot to complete."
            )

    def _on_download_error(self, error: str):
        self.update_progress.setVisible(False)
        self.download_update_btn.setEnabled(True)
        self.check_update_btn.setEnabled(True)
        self.update_status_label.setText(f"Download failed: {error}")

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

        # Tray / auto-start checkboxes
        self.minimize_to_tray_cb.setChecked(self._settings.get("minimize_to_tray", True))
        self.close_to_tray_cb.setChecked(self._settings.get("close_to_tray", True))
        self.auto_start_cb.setChecked(self._settings.get("auto_start", False))

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
                "minimize_to_tray": self.minimize_to_tray_cb.isChecked(),
                "close_to_tray": self.close_to_tray_cb.isChecked(),
                "auto_start": self.auto_start_cb.isChecked(),
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

        # Apply auto-start immediately
        old_auto = self._settings.get("auto_start", False)
        new_auto = self.auto_start_cb.isChecked()
        if old_auto != new_auto:
            from filepilot.auto_start import set_auto_start

            set_auto_start(new_auto)

        # Store new settings from controls
        self._settings = self.get_settings()

        # Persist via AppState
        if self.state:
            self.state.update(self._settings)
            self.state.save()

        # Notify via EventBus
        if self.event_bus:
            self.event_bus.settings_applied.emit(self._settings)

        super().accept()
