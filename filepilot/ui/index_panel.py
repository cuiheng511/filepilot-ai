"""文件索引管理面板 — 构建、更新、查看索引"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from filepilot.core.file_scanner import FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.ui.base_panel import BasePanel


class IndexPanel(BasePanel):
    """文件索引管理面板"""

    def __init__(self, indexer: FileIndexer | None = None, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.source_dir: Path | None = None
        self.indexer = indexer or FileIndexer()
        self.scanner = scanner or FileScanner()
        self._indexing = False

        self._setup_ui()
        self._connect_signals()
        self._refresh_stats()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── 标题 ──
        title = QLabel("🗂️ 文件索引管理")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "管理 Whoosh 全文搜索索引。建立索引后可实现快速全文搜索和自然语言检索。\n"
            "支持增量更新，无需每次都重建完整索引。"
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── 统计卡片 ──
        stats_layout = QHBoxLayout()
        self.stat_indexed = self._make_stat_card("📄 已索引文件", "—")
        self.stat_size = self._make_stat_card("💾 索引大小", "—")
        self.stat_location = self._make_stat_card("📁 索引位置", "—")

        stats_layout.addWidget(self.stat_indexed)
        stats_layout.addWidget(self.stat_size)
        stats_layout.addWidget(self.stat_location)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # ── 文件夹选择 ──
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("📂 要索引的文件夹:"))
        self.dir_label = QLabel("未选择")
        self.dir_label.setStyleSheet(
            "color: #585b70; padding: 6px 10px; background: #181825; "
            "border: 1px solid #313244; border-radius: 4px;"
        )
        self.dir_label.setWordWrap(True)
        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._on_select_source)
        dir_layout.addWidget(self.dir_label, 1)
        dir_layout.addWidget(self.btn_browse)
        layout.addLayout(dir_layout)

        # ── 操作按钮 ──
        action_layout = QHBoxLayout()

        self.btn_build = QPushButton("🔨 建立索引")
        self.btn_build.clicked.connect(self._on_build)
        self.btn_build.setEnabled(False)
        self.btn_build.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa; color: #1e1e2e;
                border: none; border-radius: 6px;
                padding: 10px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #74c7ec; }
            QPushButton:disabled { background-color: #313244; color: #585b70; }
        """)

        self.btn_update = QPushButton("🔄 增量更新")
        self.btn_update.clicked.connect(self._on_update)
        self.btn_update.setEnabled(False)

        self.btn_clear = QPushButton("🗑️ 清空索引")
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_clear.setEnabled(False)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8; color: #1e1e2e;
                border: none; border-radius: 6px;
                padding: 10px 20px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #eba0ac; }
            QPushButton:disabled { background-color: #313244; color: #585b70; }
        """)

        self.btn_refresh = QPushButton("🔄 刷新统计")
        self.btn_refresh.clicked.connect(self._refresh_stats)

        action_layout.addWidget(self.btn_build)
        action_layout.addWidget(self.btn_update)
        action_layout.addWidget(self.btn_clear)
        action_layout.addWidget(self.btn_refresh)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # 进度条 + 进度文字 + 取消按钮
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)

        self.btn_cancel = QPushButton("✕ 取消")
        self.btn_cancel.clicked.connect(self._on_cancel_indexing)
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

        # ── 分割器：上方工具提示 + 下方已索引文件列表 ──
        splitter = QSplitter(Qt.Vertical)

        # 提示区域
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_label = QLabel(
            "💡 提示：先选择文件夹，点击「建立索引」扫描并索引所有文件。\n"
            "       之后修改文件后只需点击「增量更新」即可。\n"
            "       已索引文件列表将显示在此处。"
        )
        info_label.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: #181825; "
            "border: 1px solid #313244; border-radius: 8px; padding: 16px;"
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        splitter.addWidget(info_widget)

        # 已索引文件表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(
            ["文件名", "路径", "类别", "大小", "修改日期"]
        )
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._on_table_context_menu)
        self.file_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                gridline-color: #313244; font-size: 12px;
            }
            QTableWidget::item { padding: 4px 8px; }
            QTableWidget::item:selected {
                background-color: #313244; color: #cba6f7;
            }
            QHeaderView::section {
                background-color: #181825; color: #a6adc8;
                border: none; border-bottom: 1px solid #313244;
                padding: 6px 8px; font-weight: bold; font-size: 12px;
            }
        """)
        splitter.addWidget(self.file_table)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        # ── 底部状态 ──
        self.stats_label = QLabel("就绪 — 选择文件夹后建立索引")
        self.stats_label.setStyleSheet(
            "color: #585b70; font-size: 12px; padding: 4px 0;"
        )
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.progress_text.connect(self.progress_label.setText)
        self.status_message.connect(self.stats_label.setText)

    # ── 文件夹选择 ──

    @Slot()
    def _on_select_source(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择要索引的文件夹", str(self.source_dir or Path.home())
        )
        if dir_path:
            self.source_dir = Path(dir_path)
            self.dir_label.setText(f"📂 {dir_path}")
            self.dir_label.setStyleSheet(
                "color: #cdd6f4; padding: 6px 10px; background: #181825; "
                "border: 1px solid #313244; border-radius: 4px;"
            )
            self.btn_build.setEnabled(True)
            self.btn_update.setEnabled(True)

    # ── 统计刷新 ──

    def _refresh_stats(self):
        """刷新索引统计"""
        try:
            stats = self.indexer.get_stats()
            self._update_stat("📄 已索引文件", str(stats["indexed_files"]))
            self._update_stat("💾 索引大小", stats["index_size"])
            self._update_stat("📁 索引位置", stats["index_dir"])
            self.btn_clear.setEnabled(stats["indexed_files"] > 0)
            self._load_indexed_files()
        except Exception:
            self._update_stat("📄 已索引文件", "0")
            self._update_stat("💾 索引大小", "—")
            self._update_stat("📁 索引位置", str(self.indexer.index_dir))
            self.btn_clear.setEnabled(False)

    def _load_indexed_files(self):
        """加载已索引文件列表到表格"""
        try:
            files = self.indexer.get_all_indexed(limit=2000)
        except Exception:
            files = []

        self.file_table.setSortingEnabled(False)
        self.file_table.setRowCount(len(files))

        for row, f in enumerate(files):
            self.file_table.setItem(row, 0, QTableWidgetItem(f["filename"]))
            self.file_table.setItem(row, 1, QTableWidgetItem(f["path"]))
            self.file_table.setItem(row, 2, QTableWidgetItem(f.get("category", "")))
            self.file_table.setItem(row, 3, QTableWidgetItem(f.get("size_str", "")))
            self.file_table.setItem(row, 4, QTableWidgetItem(f.get("modified", "")))

        self.file_table.setSortingEnabled(True)

    # ── 建立索引 ──

    @Slot()
    def _on_build(self):
        if not self.source_dir:
            self.status_message.emit("⚠️ 请先选择文件夹")
            return
        if self._indexing:
            return

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "确认建立索引",
            f"将为 {self.source_dir} 下的所有文件建立全文搜索索引。\n\n"
            "如果已有索引将被覆盖重建。\n这可能需要一些时间，继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        self._start_indexing("正在建立索引...", rebuild=True)

    @Slot()
    def _on_update(self):
        if not self.source_dir:
            self.status_message.emit("⚠️ 请先选择文件夹")
            return
        if self._indexing:
            return
        self._start_indexing("正在增量更新索引...", rebuild=False)

    @Slot()
    def _on_cancel_indexing(self):
        """取消索引操作"""
        self._cancelled = True
        self._indexing = False
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_build.setEnabled(bool(self.source_dir))
        self.btn_update.setEnabled(bool(self.source_dir))
        self.btn_refresh.setEnabled(True)
        self.status_message.emit("⏹️ 索引已取消")

    def _start_indexing(self, status_text: str, rebuild: bool):
        """启动索引线程"""
        self._cancelled = False
        self._indexing = True
        self.btn_build.setEnabled(False)
        self.btn_update.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.emit(status_text)

        source = self.source_dir

        def worker():
            try:
                # 扫描文件
                self.progress_text.emit("正在扫描文件...")
                files = []
                for f in self.scanner.scan(
                    str(source),
                    progress_callback=lambda i, p: self.progress_updated.emit(i % 100),
                ):
                    if self._cancelled:
                        return
                    files.append(f)

                if self._cancelled:
                    return

                if rebuild:
                    self.indexer.clear_index()

                self.progress_updated.emit(0)
                self.progress_text.emit(f"正在索引 {len(files)} 个文件...")

                # 索引文件（可取消）
                for i, f in enumerate(files):
                    if self._cancelled:
                        return
                    self.indexer.index_file(f)
                    pct = int((i + 1) / len(files) * 90) + 10
                    self.progress_updated.emit(pct)
                    self.progress_text.emit(f"索引: {f.name}")

                if not self._cancelled:
                    from PySide6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(
                        self,
                        "_on_indexing_finished",
                        Qt.QueuedConnection,
                    )
            except Exception as e:
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self,
                    "_on_indexing_error",
                    Qt.QueuedConnection,
                    Q_ARG(str, str(e)),
                )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _on_indexing_finished(self):
        """索引完成"""
        self._indexing = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_build.setEnabled(bool(self.source_dir))
        self.btn_update.setEnabled(bool(self.source_dir))
        self.btn_refresh.setEnabled(True)
        self._refresh_stats()
        stats = self.indexer.get_stats()
        self.status_message.emit(
            f"✅ 索引完成: {stats['indexed_files']} 个文件已索引, "
            f"占用 {stats['index_size']}"
        )

    @Slot(str)
    def _on_indexing_error(self, error_msg: str):
        """索引出错"""
        self._indexing = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_build.setEnabled(bool(self.source_dir))
        self.btn_update.setEnabled(bool(self.source_dir))
        self.btn_refresh.setEnabled(True)
        self.status_message.emit(f"❌ 索引出错: {error_msg}")

    # ── 清空索引 ──

    @Slot()
    def _on_clear(self):
        """清空索引"""
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.warning(
            self,
            "确认清空索引",
            "确定要清空所有索引数据吗？\n\n"
            "所有已索引的文件记录将被删除，"
            "之后需要重新建立索引才能搜索。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.indexer.clear_index()
            self._refresh_stats()
            self.file_table.setRowCount(0)
            self.status_message.emit("🗑️ 索引已清空")
            self.btn_clear.setEnabled(False)
        except Exception as e:
            self.status_message.emit(f"❌ 清空失败: {e}")

    # ── 表格右键菜单 ──

    @Slot()
    def _on_table_context_menu(self, pos):
        """表格右键菜单：从索引中移除"""
        row = self.file_table.rowAt(pos.y())
        if row < 0:
            return

        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected { background-color: #313244; }
        """)

        remove_action = QAction("🗑️ 从索引中移除", self)
        remove_action.triggered.connect(lambda: self._remove_selected_from_index())
        menu.addAction(remove_action)

        refresh_action = QAction("🔄 刷新列表", self)
        refresh_action.triggered.connect(self._load_indexed_files)
        menu.addAction(refresh_action)

        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def _remove_selected_from_index(self):
        """移除选中的文件"""
        selected = self.file_table.selectionModel().selectedRows()
        if not selected:
            return

        removed = 0
        for index in selected:
            path_item = self.file_table.item(index.row(), 1)
            if path_item and path_item.text():
                try:
                    self.indexer.remove_from_index(path_item.text())
                    removed += 1
                except Exception:
                    pass

        self._load_indexed_files()
        self._refresh_stats()
        self.status_message.emit(f"✅ 已从索引中移除 {removed} 个文件")

    # ── 外部调用入口 ──

    def index_directory(self, dir_path: str | Path):
        """供主窗口调用的快捷方法"""
        self.source_dir = Path(dir_path)
        self.dir_label.setText(f"📂 {dir_path}")
        self.dir_label.setStyleSheet(
            "color: #cdd6f4; padding: 6px 10px; background: #181825; "
            "border: 1px solid #313244; border-radius: 4px;"
        )
        self.btn_build.setEnabled(True)
        self.btn_update.setEnabled(True)
        self._on_build()
