"""文件浏览面板 — 树形目录 + 文件列表"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.utils.file_utils import FileCategory
from filepilot.ui.base_panel import BasePanel


class FileBrowserPanel(BasePanel):
    """文件浏览面板"""

    files_scanned = Signal(list)  # 扫描完成信号

    def __init__(self, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.current_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.scanner = scanner or FileScanner()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.path_label = QLabel("未选择文件夹")
        self.path_label.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 13px;
                padding: 8px 12px;
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
            }
        """)
        self.path_label.setWordWrap(True)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._on_refresh)

        self.export_btn = QPushButton("📥 导出")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)

        toolbar.addWidget(self.path_label, 1)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.export_btn)
        layout.addLayout(toolbar)

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

        # 分割器：左侧树 + 右侧表格
        splitter = QSplitter(Qt.Horizontal)

        # 左侧目录树
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("目录")
        self.tree.setMinimumWidth(220)
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px 8px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #313244;
                color: #cba6f7;
            }
            QTreeWidget::item:hover {
                background-color: #252538;
            }
        """)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        splitter.addWidget(self.tree)

        # 右侧文件表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["名称", "类型", "大小", "修改日期", "扩展名", "路径"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDropIndicatorShown(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                gridline-color: #313244;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px 10px;
            }
            QTableWidget::item:selected {
                background-color: #313244;
                color: #cba6f7;
            }
            QHeaderView::section {
                background-color: #181825;
                color: #a6adc8;
                border: none;
                border-bottom: 1px solid #313244;
                padding: 8px 10px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        splitter.addWidget(self.table)

        # 文件预览面板
        from PySide6.QtWidgets import QTextEdit
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(200)
        self.preview.setPlaceholderText("选择文件以预览内容...")
        self.preview.setStyleSheet("""
            QTextEdit {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                padding: 8px; font-size: 12px; font-family: monospace;
            }
        """)
        self.preview.setVisible(False)
        splitter.addWidget(self.preview)

        self.table.currentCellChanged.connect(self._on_row_selected)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([280, 600, 150])

        layout.addWidget(splitter, 1)

        # 底部统计
        self.stats_label = QLabel("就绪 - 选择文件夹开始浏览")
        self.stats_label.setStyleSheet("color: #585b70; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        """连接信号"""
        self.files_scanned.connect(self._on_files_scanned)
        self.status_message.connect(self._on_status_message)
        self.progress_updated.connect(self.progress_bar.setValue)

    def load_directory(self, dir_path: str):
        """加载目录（异步扫描）"""
        self.current_dir = Path(dir_path)
        self.path_label.setText(f"📂 {dir_path}")
        self.stats_label.setText("正在扫描...")

        # 更新目录树
        self._update_tree(dir_path)

        # 异步扫描
        self._scan_async(dir_path)

    def scan_directory(self, dir_path: str | Path):
        """扫描目录"""
        self.load_directory(str(dir_path))

    def _update_tree(self, dir_path: str):
        """更新目录树"""
        self.tree.clear()
        root = QTreeWidgetItem(self.tree, [Path(dir_path).name])
        root.setData(0, Qt.UserRole, dir_path)
        root.setExpanded(True)

        try:
            for entry in sorted(Path(dir_path).iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    child = QTreeWidgetItem(root, [entry.name])
                    child.setData(0, Qt.UserRole, str(entry))
        except (OSError, PermissionError):
            pass

    @Slot()
    def _on_cancel(self):
        """取消扫描"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.status_message.emit("⏹️ 正在取消扫描...")

    def _scan_async(self, dir_path: str):
        """异步扫描文件"""
        self._cancelled = False
        self._cancelling = False
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel.setVisible(True)

        def scan_worker():
            files = []
            for f in self.scanner.scan(
                dir_path,
                progress_callback=lambda i, p: self.progress_updated.emit(i % 100),
            ):
                if self._cancelled:
                    from PySide6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(self, "_on_cancel_done", Qt.QueuedConnection)
                    return
                files.append(f)

            self.files_scanned.emit(files)

        Thread(target=scan_worker, daemon=True).start()

    @Slot()
    def _on_cancel_done(self):
        """取消后恢复按钮状态"""
        if not self._cancelling:
            return
        self._cancelling = False
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)

    @Slot()
    def _on_files_scanned(self, files: list[FileInfo]):
        """扫描完成回调"""
        self.files = files
        self._populate_table(files)
        self.refresh_btn.setEnabled(True)
        self.export_btn.setEnabled(len(files) > 0)
        self.progress_bar.setVisible(False)

        stats = self.scanner.stats
        # 按类别统计大小
        cat_sizes: dict[str, int] = {}
        for f in files:
            cat_sizes[f.category.label] = cat_sizes.get(f.category.label, 0) + f.size_bytes
        total = sum(cat_sizes.values()) or 1
        top_cats = sorted(cat_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
        bar_parts = []
        for cat, size in top_cats:
            pct = size / total * 100
            bar_len = int(pct / 5)
            bar_parts.append(f"{cat} {'█' * bar_len} {pct:.0f}%")
        bar_text = " | ".join(bar_parts) if bar_parts else ""

        self.stats_label.setText(
            f"📊 {stats['scanned_count']} 个文件, {stats['total_size_str']}"
            + (f"  —  {bar_text}" if bar_text else "")
        )

    def _populate_table(self, files: list[FileInfo]):
        """填充文件列表"""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(files))

        for row, f in enumerate(files):
            # 名称
            name_item = QTableWidgetItem(f"{f.category.icon}  {f.name}")
            name_item.setData(Qt.UserRole, str(f.path))
            name_item.setToolTip(str(f.path))
            self.table.setItem(row, 0, name_item)

            # 类型
            type_item = QTableWidgetItem(f.category.label)
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, type_item)

            # 大小
            size_item = QTableWidgetItem(f.size_str)
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, size_item)

            # 修改日期
            date_item = QTableWidgetItem(f.modified_time.strftime("%Y-%m-%d %H:%M"))
            self.table.setItem(row, 3, date_item)

            # 扩展名
            ext_item = QTableWidgetItem(f.extension)
            ext_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, ext_item)

            # 路径
            path_item = QTableWidgetItem(str(f.path))
            path_item.setToolTip(str(f.path))
            self.table.setItem(row, 5, path_item)

        self.table.setSortingEnabled(True)

        # 按类型着色
        for row in range(self.table.rowCount()):
            type_item = self.table.item(row, 1)
            if type_item:
                cat_text = type_item.text()
                color = self._get_category_color(cat_text)
                if color:
                    type_item.setBackground(QColor(color).lighter(160))
                    type_item.setForeground(QColor("#1e1e2e"))

    def _get_category_color(self, category: str) -> str | None:
        """获取分类对应的颜色"""
        color_map = {
            "文档": "#89b4fa",
            "图片": "#a6e3a1",
            "视频": "#f38ba8",
            "音频": "#fab387",
            "代码": "#cba6f7",
            "压缩包": "#f9e2af",
            "PDF": "#f38ba8",
            "Markdown": "#89b4fa",
            "表格": "#a6e3a1",
            "数据": "#94e2d5",
            "其他": "#585b70",
        }
        return color_map.get(category)

    @Slot()
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """点击目录树"""
        dir_path = item.data(0, Qt.UserRole)
        if dir_path and Path(dir_path).is_dir():
            self.load_directory(dir_path)

    @Slot()
    def _on_refresh(self):
        """刷新当前目录"""
        if self.current_dir:
            self.load_directory(str(self.current_dir))

    @Slot()
    def _on_status_message(self, msg: str):
        """状态消息"""
        self.stats_label.setText(msg)

    # ── 拖拽支持 ──

    def dragEnterEvent(self, event):
        """接受文件夹拖入"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """允许拖入"""
        event.acceptProposedAction()

    def dropEvent(self, event):
        """处理拖入的文件/文件夹"""
        urls = event.mimeData().urls()
        if not urls:
            return
        # 取第一个路径
        path = Path(urls[0].toLocalFile())
        if path.is_dir():
            self.load_directory(str(path))
        elif path.is_file():
            self.load_directory(str(path.parent))

    # ── 文件预览 ──

    @Slot()
    def _on_row_selected(self, row, col, prev_row, prev_col):
        """行选中时预览文件内容"""
        if row < 0:
            self.preview.setVisible(False)
            return
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        file_path = Path(name_item.data(Qt.UserRole))
        if not file_path.is_file():
            self.preview.setVisible(False)
            return

        # 显示预览
        self.preview.setVisible(True)
        ext = file_path.suffix.lower()
        try:
            if ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'):
                from filepilot.extractors.image_extractor import ImageExtractor
                meta = ImageExtractor().extract_metadata(file_path)
                text = f"图片: {file_path.name}\n"
                text += f"尺寸: {meta.get('size', '?')}\n"
                text += f"格式: {meta.get('format', '?')}\n"
                if 'exif' in meta:
                    exif = meta['exif']
                    if 'DateTimeOriginal' in exif:
                        text += f"拍摄: {exif['DateTimeOriginal']}\n"
                self.preview.setPlainText(text)
            elif ext == '.pdf':
                from filepilot.extractors.pdf_extractor import PDFExtractor
                text = PDFExtractor().extract_text(file_path)
                self.preview.setPlainText(text[:3000] if text else "(无法提取 PDF 文本)")
            elif ext in ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.sh'):
                content = file_path.read_text(encoding='utf-8', errors='replace')
                self.preview.setPlainText(content[:3000])
            else:
                content = file_path.read_text(encoding='utf-8', errors='replace')
                self.preview.setPlainText(content[:3000] if content else "(空文件)")
        except Exception:
            self.preview.setPlainText("(无法预览)")

    # ── 导出功能 ──

    @Slot()
    def _on_export(self):
        """导出扫描结果为 CSV 或 JSON"""
        if not self.files:
            return

        from PySide6.QtWidgets import QFileDialog
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "导出扫描结果", "scan_results.json",
            "JSON 文件 (*.json);;CSV 文件 (*.csv)",
        )
        if not path:
            return

        import csv, json
        rows = [{
            "path": str(f.path), "name": f.name, "extension": f.extension,
            "size_bytes": f.size_bytes, "size_str": f.size_str,
            "category": f.category.label,
            "modified": f.modified_time.isoformat(),
        } for f in self.files]

        if path.endswith(".csv"):
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        else:
            Path(path).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stats_label.setText(f"✅ 已导出 {len(rows)} 条记录到 {path}")
