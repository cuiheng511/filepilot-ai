"""Settings dialog — AI engine and application configuration"""

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from filepilot.i18n import t


class SettingsDialog(QDialog):
    """Settings dialog"""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings — FilePilot AI")
        self.setMinimumSize(600, 450)
        self.resize(650, 500)

        self._settings = settings.copy()
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

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
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
        self.provider_combo.addItems([
            "Ollama (Local)",
            "llama.cpp / LM Studio (Local)",
            "OpenAI (Cloud)",
            "Anthropic Claude (Cloud)",
            "Custom OpenAI Compatible",
        ])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Common settings (shared across all Providers)
        common_group = QGroupBox(t("settings_model"))
        common_layout = QFormLayout()
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.addItems([
            "qwen2.5:7b", "qwen2.5:3b", "llama3.1:8b", "mistral:7b",
            "gpt-4o-mini", "gpt-4o", "claude-sonnet-4-20250514",
        ])
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

    def _parse_file_size(self, text: str) -> int:
        """Parse file size input, default to 500 on invalid input"""
        try:
            return int(text.strip()) if text.strip() else 500
        except (ValueError, AttributeError):
            return 500

    def _load_settings(self):
        """Load existing settings"""
        provider = self._settings.get("ai_provider", "ollama")
        provider_map = {"ollama": 0, "llamacpp": 1, "openai": 2, "anthropic": 3, "custom": 4}
        self.provider_combo.setCurrentIndex(provider_map.get(provider, 0))
        self.model_input.setCurrentText(self._settings.get("ai_model", "qwen2.5:7b"))
        self.api_base_input.setText(self._settings.get("ai_api_base", "http://localhost:11434"))
        self.api_key_input.setText(self._settings.get("ai_api_key", ""))
        self.max_file_size.setText(str(self._settings.get("max_file_size_mb", 500)))
        self.index_dir.setText(self._settings.get("index_dir", str(Path.home() / ".filepilot" / "index")))

    def get_settings(self) -> dict:
        """Get settings values"""
        provider_names = ["ollama", "llamacpp", "openai", "anthropic", "custom"]
        provider = provider_names[self.provider_combo.currentIndex()]
        return {
            "ai_mode": "local" if provider in ("ollama", "llamacpp") else "cloud",
            "ai_provider": provider,
            "ai_model": self.model_input.currentText(),
            "ai_api_base": self.api_base_input.text(),
            "ai_api_key": self.api_key_input.text(),
            "index_dir": self.index_dir.text(),
            "max_file_size_mb": self._parse_file_size(self.max_file_size.text()),
        }
