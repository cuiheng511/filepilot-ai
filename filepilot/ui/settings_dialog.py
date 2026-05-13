"""设置对话框 — AI 引擎和应用配置"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置 — FilePilot AI")
        self.setMinimumSize(600, 450)
        self.resize(650, 500)

        self._settings = settings.copy()
        self._setup_ui()
        self._load_settings()

        # 样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QGroupBox {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                margin-top: 16px;
                padding: 20px 16px 16px 16px;
                font-size: 14px;
                font-weight: bold;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                color: #cba6f7;
            }
            QLabel {
                color: #a6adc8;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #cba6f7;
            }
            QComboBox {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox:focus {
                border-color: #cba6f7;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                selection-background-color: #313244;
            }
            QRadioButton {
                color: #cdd6f4;
                font-size: 13px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QTabWidget::pane {
                background-color: #1e1e2e;
                border: none;
                padding: 16px;
            }
            QTabBar::tab {
                background-color: #181825;
                color: #a6adc8;
                border: none;
                padding: 12px 24px;
                font-size: 13px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e2e;
                color: #cba6f7;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #252538;
            }
        """)

    def _setup_ui(self):
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 标签页
        tabs = QTabWidget()

        # AI 设置页
        ai_tab = self._create_ai_tab()
        tabs.addTab(ai_tab, "🤖 AI 引擎")

        # 通用设置页
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "⚙️ 通用")

        layout.addWidget(tabs)

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """)
        layout.addWidget(buttons)

    def _create_ai_tab(self) -> QWidget:
        """创建 AI 设置页（支持多 Provider）"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # AI Provider 选择
        provider_group = QGroupBox("AI Provider")
        provider_layout = QVBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "Ollama (本地)",
            "llama.cpp / LM Studio (本地)",
            "OpenAI (云端)",
            "Anthropic Claude (云端)",
            "自定义 OpenAI 兼容",
        ])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # 通用设置（所有 Provider 共用）
        common_group = QGroupBox("模型设置")
        common_layout = QFormLayout()
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.addItems([
            "qwen2.5:7b", "qwen2.5:3b", "llama3.1:8b", "mistral:7b",
            "gpt-4o-mini", "gpt-4o", "claude-sonnet-4-20250514",
        ])
        self.model_input.setCurrentText(self._settings.get("ai_model", "qwen2.5:7b"))
        self.api_base_input = QLineEdit("http://localhost:11434")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        common_layout.addRow("模型:", self.model_input)
        common_layout.addRow("API 地址:", self.api_base_input)
        common_layout.addRow("API Key:", self.api_key_input)
        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        layout.addStretch()

        # 初始化默认值
        provider = self._settings.get("ai_provider", "ollama")
        provider_map = {"ollama": 0, "llamacpp": 1, "openai": 2, "anthropic": 3, "custom": 4}
        self.provider_combo.setCurrentIndex(provider_map.get(provider, 0))
        self.api_key_input.setText(self._settings.get("ai_api_key", ""))

        return widget

    def _on_provider_changed(self, index: int):
        """Provider 切换时更新默认值"""
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
        self.api_key_input.parent().findChild(QLabel).setVisible(need_key) if self.api_key_input.parent() else None

    def _create_general_tab(self) -> QWidget:
        """创建通用设置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # 索引设置
        index_group = QGroupBox("索引设置")
        index_layout = QFormLayout()
        self.index_dir = QLineEdit(str(Path.home() / ".filepilot" / "index"))
        index_layout.addRow("索引存储路径:", self.index_dir)
        index_group.setLayout(index_layout)
        layout.addWidget(index_group)

        # 文件扫描设置
        scan_group = QGroupBox("文件扫描")
        scan_layout = QFormLayout()
        self.max_file_size = QLineEdit("500")
        self.max_file_size.setPlaceholderText("单位: MB")
        scan_layout.addRow("最大文件大小 (MB):", self.max_file_size)
        scan_group.setLayout(scan_layout)
        layout.addWidget(scan_group)

        layout.addStretch()
        return widget

    def _load_settings(self):
        """加载现有设置"""
        provider = self._settings.get("ai_provider", "ollama")
        provider_map = {"ollama": 0, "llamacpp": 1, "openai": 2, "anthropic": 3, "custom": 4}
        self.provider_combo.setCurrentIndex(provider_map.get(provider, 0))
        self.model_input.setCurrentText(self._settings.get("ai_model", "qwen2.5:7b"))
        self.api_base_input.setText(self._settings.get("ai_api_base", "http://localhost:11434"))
        self.api_key_input.setText(self._settings.get("ai_api_key", ""))
        self.index_dir.setText(self._settings.get("index_dir", str(Path.home() / ".filepilot" / "index")))

    def get_settings(self) -> dict:
        """获取设置值"""
        provider_names = ["ollama", "llamacpp", "openai", "anthropic", "custom"]
        provider = provider_names[self.provider_combo.currentIndex()]
        return {
            "ai_mode": "local" if provider in ("ollama", "llamacpp") else "cloud",
            "ai_provider": provider,
            "ai_model": self.model_input.currentText(),
            "ai_api_base": self.api_base_input.text(),
            "ai_api_key": self.api_key_input.text(),
            "index_dir": self.index_dir.text(),
            "max_file_size_mb": int(self.max_file_size.text() or "500"),
        }
