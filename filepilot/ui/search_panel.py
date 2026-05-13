"""搜索面板 — 自然语言文件搜索"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.ui.base_panel import BasePanel


class SearchPanel(BasePanel):
    """搜索面板"""

    indexing_finished = Signal(int, str)

    def __init__(self, indexer: FileIndexer | None = None, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.indexer = indexer or FileIndexer()
        self.scanner = scanner or FileScanner()
        self.current_dir: Path | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title = QLabel("🔍 文件搜索")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "自然语言搜索本地文件。支持按文件名、内容、类型、日期搜索。\n"
            "例如：「上周修改的PDF文件」「找关于机器学习的文档」"
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词，如：找关于深度学习的PDF...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 2px solid #313244;
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #cba6f7;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)

        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #1e1e2e;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
        """)
        self.search_btn.clicked.connect(self._on_search)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # 搜索选项
        options_layout = QHBoxLayout()
        self.fuzzy_cb = QCheckBox("模糊搜索")
        self.fuzzy_cb.setChecked(True)
        self.fuzzy_cb.setStyleSheet("color: #a6adc8;")
        options_layout.addWidget(self.fuzzy_cb)

        self.content_cb = QCheckBox("搜索内容")
        self.content_cb.setChecked(True)
        self.content_cb.setStyleSheet("color: #a6adc8;")
        options_layout.addWidget(self.content_cb)

        options_layout.addStretch()

        self.index_btn = QPushButton("🗂️ 建立索引")
        self.index_btn.clicked.connect(self._on_index)
        options_layout.addWidget(self.index_btn)

        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.clicked.connect(self._clear_results)
        options_layout.addWidget(self.clear_btn)

        layout.addLayout(options_layout)

        # 进度条 + 取消按钮
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)

        self.btn_cancel = QPushButton("✕ 取消")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8; color: #1e1e2e;
                border: none; border-radius: 6px;
                padding: 6px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #eba0ac; }
        """)
        progress_layout.addWidget(self.btn_cancel)
        layout.addLayout(progress_layout)

        # 搜索结果
        self.result_list = QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #252538;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #313244;
                color: #cba6f7;
            }
            QListWidget::item:hover {
                background-color: #252538;
            }
        """)
        layout.addWidget(self.result_list, 1)

        # 状态
        self.stats_label = QLabel("请先打开文件夹并建立索引")
        self.stats_label.setStyleSheet("color: #585b70; font-size: 12px;")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        """连接信号"""
        self.status_message.connect(self._on_status_message)
        self.progress_updated.connect(self.progress_bar.setValue)
        self.indexing_finished.connect(self._on_indexing_finished)

    def index_directory(self, dir_path: str | Path):
        """索引目录"""
        self.current_dir = Path(dir_path)
        self._index_async(dir_path)

    @Slot()
    def _on_cancel(self):
        """取消当前操作"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        self.index_btn.setEnabled(True)
        self.status_message.emit("⏹️ 操作已取消")

    @Slot()
    def _on_search(self):
        """执行搜索"""
        query = self.search_input.text().strip()
        if not query:
            return

        # 检查索引状态
        stats = self.indexer.get_stats()
        if stats["indexed_files"] == 0:
            self.result_list.addItem(
                "⚠️ 索引为空，请先建立索引后再搜索"
            )
            return

        self._cancelled = False
        self._cancelling = False
        self.status_message.emit(f"正在搜索: {query} ...")
        self.search_btn.setEnabled(False)
        self.btn_cancel.setVisible(True)

        def search_worker():
            if self._cancelled:
                return
            # 执行搜索
            results = self.indexer.search(
                query,
                fuzzy=self.fuzzy_cb.isChecked(),
                limit=100,
            )

            if self._cancelled:
                return

            # 显示结果（在主线程）
            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self,
                "_display_results",
                Qt.QueuedConnection,
                Q_ARG(list, results),
                Q_ARG(str, query),
            )

        Thread(target=search_worker, daemon=True).start()

    @Slot()
    def _display_results(self, results: list[dict], query: str):
        """显示搜索结果"""
        self.result_list.clear()
        self.search_btn.setEnabled(True)

        if not results:
            item = QListWidgetItem(f"没有找到与「{query}」相关的结果")
            item.setForeground(Qt.gray)
            self.result_list.addItem(item)
            self.stats_label.setText("未找到匹配结果")
            return

        for r in results:
            score = r.get("score", 0)
            category = r.get("category", "其他")
            filename = r.get("filename", "未知")
            filepath = r.get("path", "")
            modified = r.get("modified", "")
            size_str = r.get("size_str", "")
            highlights = r.get("highlights", "")

            # 图标映射
            icon_map = {
                "PDF": "📕",
                "Markdown": "📝",
                "代码": "💻",
                "图片": "🖼️",
                "文档": "📄",
                "其他": "📁",
            }
            icon = icon_map.get(category, "📁")

            display_text = f"{icon}  {filename}"
            if highlights:
                display_text += f"\n   📌 {highlights[:100]}"
            display_text += f"\n   📂 {filepath}  |  {size_str}  |  {modified}  |  匹配度: {score:.0%}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, filepath)
            item.setToolTip(f"路径: {filepath}\n匹配度: {score:.0%}")
            self.result_list.addItem(item)

        self.stats_label.setText(f"找到 {len(results)} 个结果，搜索词: {query}")

    @Slot()
    def _on_index(self):
        """建立索引"""
        if not self.current_dir:
            self.result_list.addItem("⚠️ 请先在「文件浏览」中打开一个文件夹")
            return

        self._index_async(self.current_dir)

    def _index_async(self, dir_path: str | Path):
        """异步建立索引"""
        self._cancelled = False
        self._cancelling = False
        self.index_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel.setVisible(True)
        self.status_message.emit("正在扫描并建立索引...")

        def index_worker():
            # 一次扫描，结果复用
            files = []
            for f in self.scanner.scan(
                str(dir_path),
                progress_callback=lambda i, p: None,
            ):
                if self._cancelled:
                    from PySide6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(self, "_on_cancel_done", Qt.QueuedConnection)
                    return
                files.append(f)

            if self._cancelled:
                return

            total = len(files)

            # 建立索引
            indexed = self.indexer.index_files(
                files,
                progress_callback=lambda i, msg: self.progress_updated.emit(
                    int(i / total * 100) if total else 0
                ),
            )

            if not self._cancelled:
                self.indexing_finished.emit(indexed, str(dir_path))

        Thread(target=index_worker, daemon=True).start()

    @Slot()
    def _on_cancel_done(self):
        """取消索引"""
        if not self._cancelling:
            return
        self._cancelling = False
        self.index_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)
        self.status_message.emit("⏹️ 索引已取消")

    @Slot()
    def _on_indexing_finished(self, indexed: int, dir_path: str):
        """索引完成回调（主线程）"""
        status_msg = f"索引完成: 共 {indexed} 个文件已加入索引"
        self.status_message.emit(status_msg)
        self.index_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        stats = self.indexer.get_stats()
        self.stats_label.setText(
            f"📊 索引统计: {stats['indexed_files']} 个文件, "
            f"索引大小: {stats['index_size']}"
        )

    def _clear_results(self):
        """清空搜索结果"""
        self.result_list.clear()
        self.search_input.clear()
        self.stats_label.setText("就绪")

    @Slot()
    def _on_status_message(self, msg: str):
        """更新状态"""
        self.stats_label.setText(msg)
