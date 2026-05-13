"""FilePilot AI 主窗口"""

from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from filepilot.ui.file_browser import FileBrowserPanel
from filepilot.ui.search_panel import SearchPanel
from filepilot.ui.settings_dialog import SettingsDialog
from filepilot.ui.organize_panel import OrganizePanel
from filepilot.ui.duplicates_panel import DuplicatesPanel
from filepilot.ui.index_panel import IndexPanel
from filepilot.ui.summary_panel import SummaryPanel


class MainWindow(QMainWindow):
    """FilePilot AI 主窗口"""

    def __init__(self, services: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FilePilot AI — 智能文件管家")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # 状态
        self.current_dir: Path | None = None
        self.settings = self._load_settings()
        self.services = services or {}

        # 构建 UI
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

        # 应用样式
        self._apply_styles()

        # 键盘快捷键
        self._setup_shortcuts()

    def _setup_ui(self):
        """构建主界面"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航侧边栏
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        self.nav_list.setObjectName("navSidebar")
        font = QFont()
        font.setPointSize(11)
        self.nav_list.setFont(font)

        # 导航项
        self._nav_items = {
            "browse": self._add_nav_item("📂  文件浏览", "浏览和管理文件"),
            "search": self._add_nav_item("🔍  文件搜索", "自然语言搜索本地文件"),
            "organize": self._add_nav_item("📋  文件整理", "自动归类与重命名"),
            "duplicates": self._add_nav_item("🔗  查重工具", "查找重复文件"),
            "summary": self._add_nav_item("📝  摘要生成", "提取文件摘要"),
            "index": self._add_nav_item("🗂️  文件索引", "管理文件索引"),
        }

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # 右侧内容区域
        self.content_stack = QStackedWidget()

        # 各功能面板（注入服务实例，避免重复创建）
        scanner = self.services.get("scanner")
        indexer = self.services.get("indexer")
        organizer = self.services.get("organizer")
        finder = self.services.get("duplicate_finder")

        self.browse_panel = FileBrowserPanel(scanner=scanner)
        self.search_panel = SearchPanel(indexer=indexer, scanner=scanner)
        self.organize_panel = OrganizePanel(organizer=organizer, scanner=scanner)
        self.duplicates_panel = DuplicatesPanel(finder=finder, scanner=scanner)
        self.summary_panel = SummaryPanel(
            summarizer=self.services.get("summarizer"),
            local_ai=self.services.get("local_ai"),
            cloud_ai=self.services.get("cloud_ai"),
        )
        self.index_panel = IndexPanel(indexer=indexer, scanner=scanner)

        self.content_stack.addWidget(self.browse_panel)      # 0
        self.content_stack.addWidget(self.search_panel)      # 1
        self.content_stack.addWidget(self.organize_panel)    # 2
        self.content_stack.addWidget(self.duplicates_panel)  # 3
        self.content_stack.addWidget(self.summary_panel)     # 4
        self.content_stack.addWidget(self.index_panel)       # 5

        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.content_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)

        # 默认选中第一个
        self.nav_list.setCurrentRow(0)

    def _add_nav_item(self, text: str, tooltip: str) -> QListWidgetItem:
        """添加导航项"""
        item = QListWidgetItem(text)
        item.setToolTip(tooltip)
        item.setSizeHint(QSize(0, 45))
        self.nav_list.addItem(item)
        return item

    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        open_action = QAction("📂 打开文件夹...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_folder)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tool_menu = menubar.addMenu("工具(&T)")
        settings_action = QAction("⚙️ 设置...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._on_settings)
        tool_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于 FilePilot AI", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        self.btn_open = QPushButton("📂 打开文件夹")
        self.btn_open.clicked.connect(self._on_open_folder)
        toolbar.addWidget(self.btn_open)

        toolbar.addSeparator()

        self.btn_scan = QPushButton("🔄 扫描")
        self.btn_scan.clicked.connect(self._on_scan)
        self.btn_scan.setEnabled(False)
        toolbar.addWidget(self.btn_scan)

        self.btn_index = QPushButton("🗂️ 建立索引")
        self.btn_index.clicked.connect(self._on_index)
        self.btn_index.setEnabled(False)
        toolbar.addWidget(self.btn_index)

        toolbar.addSeparator()

        self.btn_theme = QPushButton("🌙")
        self.btn_theme.setToolTip("切换亮/暗主题")
        self.btn_theme.setCheckable(True)
        self.btn_theme.setChecked(True)
        self.btn_theme.clicked.connect(self._on_toggle_theme)
        toolbar.addWidget(self.btn_theme)

    def _setup_statusbar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(250)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

    def _apply_styles(self):
        """应用 CSS 样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QMenuBar {
                background-color: #181825;
                color: #cdd6f4;
                border-bottom: 1px solid #313244;
                padding: 2px;
            }
            QMenuBar::item:selected {
                background-color: #313244;
            }
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
            }
            QMenu::item:selected {
                background-color: #313244;
            }
            #navSidebar {
                background-color: #181825;
                border: none;
                border-right: 1px solid #313244;
                padding: 8px;
                outline: none;
            }
            #navSidebar::item {
                color: #cdd6f4;
                border-radius: 8px;
                padding: 10px 12px;
                margin: 2px 0px;
            }
            #navSidebar::item:selected {
                background-color: #313244;
                color: #cba6f7;
                font-weight: bold;
            }
            #navSidebar::item:hover:!selected {
                background-color: #252538;
            }
            QToolBar {
                background-color: #1e1e2e;
                border: none;
                border-bottom: 1px solid #313244;
                padding: 4px;
                spacing: 6px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #585b70;
            }
            QPushButton:disabled {
                background-color: #252538;
                color: #585b70;
            }
            QStatusBar {
                background-color: #181825;
                color: #a6adc8;
                border-top: 1px solid #313244;
                font-size: 12px;
            }
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: #cba6f7;
                border-radius: 4px;
            }
            QSplitter::handle {
                background-color: #313244;
                width: 1px;
            }
            QLabel#sectionTitle {
                color: #cdd6f4;
                font-size: 18px;
                font-weight: bold;
                padding: 12px 0;
            }
            QLabel#sectionDesc {
                color: #a6adc8;
                font-size: 13px;
                padding-bottom: 16px;
            }
        """)

    def _setup_shortcuts(self):
        """设置键盘快捷键 Ctrl+1~6 切换面板"""
        panel_actions = [
            ("Ctrl+1", "文件浏览", 0),
            ("Ctrl+2", "文件搜索", 1),
            ("Ctrl+3", "文件整理", 2),
            ("Ctrl+4", "查重工具", 3),
            ("Ctrl+5", "摘要生成", 4),
            ("Ctrl+6", "文件索引", 5),
        ]
        for shortcut, name, index in panel_actions:
            action = QAction(f"切换到{name}", self)
            action.setShortcut(shortcut)
            action.triggered.connect(lambda checked, i=index: self._switch_to_panel(i))
            self.addAction(action)

    def _switch_to_panel(self, index: int):
        """切换到指定面板"""
        self.content_stack.setCurrentIndex(index)
        self.nav_list.setCurrentRow(index)

    def _load_settings(self) -> dict:
        """加载设置（统一使用 app.load_settings）"""
        from filepilot.app import load_settings as _load
        settings = _load()
        # 补充 MainWindow 所需的默认值
        settings.setdefault("recent_dirs", [])
        return settings

    def _save_settings(self):
        """保存设置"""
        import json
        settings_path = Path.home() / ".filepilot" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            settings_path.write_text(
                json.dumps(self.settings, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    @Slot()
    def _on_nav_changed(self, index: int):
        """导航切换"""
        self.content_stack.setCurrentIndex(index)
        names = ["浏览", "搜索", "整理", "查重", "摘要", "索引"]
        if 0 <= index < len(names):
            self.status_label.setText(f"当前: {names[index]}")

    @Slot()
    def _on_open_folder(self):
        """打开文件夹"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择文件夹", str(self.current_dir or Path.home())
        )
        if dir_path:
            self.current_dir = Path(dir_path)
            self.status_label.setText(f"已打开: {dir_path}")
            self.btn_scan.setEnabled(True)
            self.btn_index.setEnabled(True)

            # 保存到最近目录
            recent = self.settings.get("recent_dirs", [])
            if str(dir_path) in recent:
                recent.remove(str(dir_path))
            recent.insert(0, str(dir_path))
            self.settings["recent_dirs"] = recent[:10]
            self._save_settings()

            # 通知浏览面板
            self.browse_panel.load_directory(dir_path)

    @Slot()
    def _on_scan(self):
        """扫描文件"""
        if self.current_dir:
            self.browse_panel.scan_directory(self.current_dir)

    @Slot()
    def _on_index(self):
        """建立索引"""
        if self.current_dir:
            self.index_panel.index_directory(self.current_dir)
            self.nav_list.setCurrentRow(5)  # 切换到索引面板

    @Slot()
    def _on_settings(self):
        """打开设置"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            self._save_settings()
            self.status_label.setText("设置已保存")

    @Slot()
    def _on_about(self):
        """关于对话框"""
        QMessageBox.about(
            self,
            "关于 FilePilot AI",
            "<h2>FilePilot AI v0.1.0</h2>"
            "<p>智能文件管家 — 自动整理、归类、搜索你的本地文件。</p>"
            "<p>功能：文件类型识别 · 自动重命名 · 自动归类<br>"
            "PDF/Markdown 摘要 · 文件索引 · 查重 · AI 搜索</p>"
            "<hr>"
            "<p>Built with ❤️ using PySide6 + Whoosh + Ollama</p>"
        )

    @Slot()
    def _on_toggle_theme(self, checked: bool):
        """切换亮/暗主题"""
        if checked:
            # 暗色主题
            self.btn_theme.setText("🌙")
            self._apply_styles()
        else:
            # 亮色主题
            self.btn_theme.setText("☀️")
            self.setStyleSheet(self._light_theme())
        self.settings["theme"] = "dark" if checked else "light"
        self._save_settings()

    def _light_theme(self) -> str:
        return """
            QMainWindow { background-color: #f5f5f5; }
            QMenuBar { background-color: #e8e8e8; color: #333; border-bottom: 1px solid #ddd; padding: 2px; }
            QMenuBar::item:selected { background-color: #d0d0d0; }
            QMenu { background-color: #f5f5f5; color: #333; border: 1px solid #ddd; }
            QMenu::item:selected { background-color: #d0d0d0; }
            #navSidebar { background-color: #e8e8e8; border: none; border-right: 1px solid #ddd; padding: 8px; }
            #navSidebar::item { color: #333; border-radius: 8px; padding: 10px 12px; margin: 2px 0px; }
            #navSidebar::item:selected { background-color: #d0d0d0; color: #6c5ce7; font-weight: bold; }
            #navSidebar::item:hover:!selected { background-color: #e0e0e0; }
            QToolBar { background-color: #e8e8e8; border: none; border-bottom: 1px solid #ddd; padding: 4px; spacing: 6px; }
            QPushButton { background-color: #e0e0e0; color: #333; border: 1px solid #ccc; border-radius: 6px; padding: 8px 16px; font-size: 13px; }
            QPushButton:hover { background-color: #d0d0d0; border-color: #bbb; }
            QPushButton:pressed { background-color: #c0c0c0; }
            QPushButton:disabled { background-color: #f0f0f0; color: #999; }
            QStatusBar { background-color: #e8e8e8; color: #666; border-top: 1px solid #ddd; font-size: 12px; }
            QSplitter::handle { background-color: #ddd; width: 1px; }
        """

    def _show_progress(self, visible: bool, value: int = 0, maximum: int = 100):
        """显示/隐藏进度条"""
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setValue(value)

    def _update_progress(self, value: int):
        """更新进度"""
        self.progress_bar.setValue(value)

    # ===== Placeholder panels =====

