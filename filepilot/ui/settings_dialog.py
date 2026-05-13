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
        """创建 AI 设置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # AI 模式
        mode_group = QGroupBox("AI 模式")
        mode_layout = QVBoxLayout()
        self.local_radio = QRadioButton("本地模式 (Ollama)")
        self.local_radio.setToolTip("使用本地运行的 Ollama 模型，数据不出本机")
        self.cloud_radio = QRadioButton("云端模式 (OpenAI API)")
        self.cloud_radio.setToolTip("使用 OpenAI 兼容 API，需要 API Key")
        self.hybrid_radio = QRadioButton("混合模式 (优先本地，回退云端)")
        self.hybrid_radio.setToolTip("优先使用本地模型，不可用时自动切换云端")

        mode_layout.addWidget(self.local_radio)
        mode_layout.addWidget(self.cloud_radio)
        mode_layout.addWidget(self.hybrid_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Ollama 设置
        ollama_group = QGroupBox("Ollama 本地模型")
        ollama_layout = QFormLayout()
        self.ollama_model = QComboBox()
        self.ollama_model.setEditable(True)
        self.ollama_model.addItems([
            "qwen2.5:7b",
            "qwen2.5:3b",
            "llama3.1:8b",
            "mistral:7b",
            "gemma2:9b",
        ])
        self.ollama_model.setCurrentText(
            self._settings.get("ollama_model", "qwen2.5:7b")
        )
        self.ollama_url = QLineEdit("http://localhost:11434")
        ollama_layout.addRow("模型:", self.ollama_model)
        ollama_layout.addRow("API 地址:", self.ollama_url)
        ollama_group.setLayout(ollama_layout)
        layout.addWidget(ollama_group)

        # OpenAI 设置
        openai_group = QGroupBox("OpenAI 云端 API")
        openai_layout = QFormLayout()
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("sk-...")
        self.openai_key.setText(self._settings.get("openai_key", ""))
        self.openai_model = QComboBox()
        self.openai_model.setEditable(True)
        self.openai_model.addItems([
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ])
        self.openai_model.setCurrentText(
            self._settings.get("openai_model", "gpt-4o-mini")
        )
        self.openai_url = QLineEdit("https://api.openai.com/v1")
        openai_layout.addRow("API Key:", self.openai_key)
        openai_layout.addRow("模型:", self.openai_model)
        openai_layout.addRow("API 地址:", self.openai_url)
        openai_group.setLayout(openai_layout)
        layout.addWidget(openai_group)

        layout.addStretch()
        return widget

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
        mode = self._settings.get("ai_mode", "local")
        if mode == "local":
            self.local_radio.setChecked(True)
        elif mode == "cloud":
            self.cloud_radio.setChecked(True)
        else:
            self.hybrid_radio.setChecked(True)

    def get_settings(self) -> dict:
        """获取设置值"""
        # 确定 AI 模式
        if self.local_radio.isChecked():
            ai_mode = "local"
        elif self.cloud_radio.isChecked():
            ai_mode = "cloud"
        else:
            ai_mode = "hybrid"

        return {
            "ai_mode": ai_mode,
            "ollama_model": self.ollama_model.currentText(),
            "ollama_url": self.ollama_url.text(),
            "openai_key": self.openai_key.text(),
            "openai_model": self.openai_model.currentText(),
            "openai_url": self.openai_url.text(),
            "index_dir": self.index_dir.text(),
            "max_file_size_mb": int(self.max_file_size.text() or "500"),
        }
