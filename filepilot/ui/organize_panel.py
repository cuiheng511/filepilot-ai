"""文件整理面板 — 自动归类、智能重命名"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from filepilot.core.file_organizer import (
    CategoryRule,
    DateRule,
    ExtensionRule,
    FileOrganizer,
    SizeRule,
)
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.ui.base_panel import BasePanel


class OrganizePanel(BasePanel):
    """文件整理面板"""

    RULE_MAP = {
        "category": CategoryRule,
        "date": DateRule,
        "extension": ExtensionRule,
        "size": SizeRule,
    }

    def __init__(self, organizer: FileOrganizer | None = None, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.source_dir: Path | None = None
        self.target_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.organizer = organizer or FileOrganizer()
        self.scanner = scanner or FileScanner()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── 标题 ──
        title = QLabel("📋 文件整理")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "选择源文件夹和目标文件夹，配置规则后一键整理文件。\n"
            "支持按类型、日期、扩展名、大小自动归类，以及智能重命名。"
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── 文件夹选择 ──
        dir_group = QGroupBox("文件夹")
        dir_layout = QVBoxLayout()
        dir_layout.setSpacing(8)

        # 源文件夹
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("📂 源文件夹:"))
        self.src_path_label = QLabel("未选择")
        self.src_path_label.setStyleSheet("color: #585b70; padding: 6px 10px; background: #181825; border: 1px solid #313244; border-radius: 4px;")
        self.src_path_label.setWordWrap(True)
        self.btn_src = QPushButton("浏览...")
        self.btn_src.clicked.connect(self._on_select_source)
        src_layout.addWidget(self.src_path_label, 1)
        src_layout.addWidget(self.btn_src)
        dir_layout.addLayout(src_layout)

        # 目标文件夹
        dst_layout = QHBoxLayout()
        dst_layout.addWidget(QLabel("🎯 目标文件夹:"))
        self.dst_path_label = QLabel("未选择（默认: 源文件夹/_organized）")
        self.dst_path_label.setStyleSheet("color: #585b70; padding: 6px 10px; background: #181825; border: 1px solid #313244; border-radius: 4px;")
        self.dst_path_label.setWordWrap(True)
        self.btn_dst = QPushButton("浏览...")
        self.btn_dst.clicked.connect(self._on_select_target)
        dst_layout.addWidget(self.dst_path_label, 1)
        dst_layout.addWidget(self.btn_dst)
        dir_layout.addLayout(dst_layout)

        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # ── 整理规则 ──
        rule_group = QGroupBox("整理规则")
        rule_layout = QHBoxLayout()
        rule_layout.setSpacing(16)

        self.cb_category = QCheckBox("📂 按文件类型归类")
        self.cb_category.setChecked(True)
        self.cb_date = QCheckBox("📅 按日期归类 (年/月)")
        self.cb_extension = QCheckBox("📎 按扩展名归类")
        self.cb_size = QCheckBox("📏 按文件大小归类")

        for cb in [self.cb_category, self.cb_date, self.cb_extension, self.cb_size]:
            cb.setStyleSheet("color: #cdd6f4; spacing: 8px;")

        rule_layout.addWidget(self.cb_category)
        rule_layout.addWidget(self.cb_date)
        rule_layout.addWidget(self.cb_extension)
        rule_layout.addWidget(self.cb_size)
        rule_layout.addStretch()
        rule_group.setLayout(rule_layout)
        layout.addWidget(rule_group)

        # ── 重命名设置 ──
        rename_layout = QHBoxLayout()
        rename_layout.addWidget(QLabel("✏️ 重命名模板:"))
        self.rename_input = QLineEdit()
        self.rename_input.setPlaceholderText("留空不重命名。支持: {name} {date} {time} {ext} {category}")
        self.rename_input.setStyleSheet("""
            QLineEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #cba6f7; }
        """)
        rename_layout.addWidget(self.rename_input, 1)

        self.template_btn = QPushButton("模板示例")
        self.template_btn.setToolTip(
            "可用变量:\n"
            "  {name}     — 原文件名\n"
            "  {date}     — 修改日期 (2024-01-15)\n"
            "  {time}     — 修改时间 (143022)\n"
            "  {ext}      — 扩展名 (pdf)\n"
            "  {category} — 文件类别 (文档)"
        )
        self.template_btn.clicked.connect(self._on_template_help)
        rename_layout.addWidget(self.template_btn)

        layout.addLayout(rename_layout)

        # ── 操作按钮 ──
        action_layout = QHBoxLayout()
        self.btn_preview = QPushButton("👁️ 预览整理")
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_preview.setEnabled(False)

        self.btn_execute = QPushButton("🚀 执行整理")
        self.btn_execute.clicked.connect(self._on_execute)
        self.btn_execute.setEnabled(False)
        self.btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #94e2d5; }
            QPushButton:disabled { background-color: #313244; color: #585b70; }
        """)

        self.btn_clear = QPushButton("清空结果")
        self.btn_clear.clicked.connect(self._clear_results)

        action_layout.addWidget(self.btn_preview)
        action_layout.addWidget(self.btn_execute)
        action_layout.addWidget(self.btn_clear)
        action_layout.addStretch()
        layout.addLayout(action_layout)

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

        # ── 结果表格 ──
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["源路径", "目标路径", "类别", "大小", "状态"])
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                gridline-color: #313244; font-size: 12px;
            }
            QTableWidget::item { padding: 4px 8px; }
            QTableWidget::item:selected { background-color: #313244; color: #cba6f7; }
            QHeaderView::section {
                background-color: #181825; color: #a6adc8;
                border: none; border-bottom: 1px solid #313244;
                padding: 6px 8px; font-weight: bold; font-size: 12px;
            }
        """)
        layout.addWidget(self.result_table, 1)

        # ── 状态栏 ──
        self.stats_label = QLabel("选择源文件夹后开始预览")
        self.stats_label.setStyleSheet("color: #585b70; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)

    # ── 文件夹选择 ──

    @Slot()
    def _on_select_source(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if dir_path:
            self.source_dir = Path(dir_path)
            self.src_path_label.setText(f"📂 {dir_path}")
            self.src_path_label.setStyleSheet("color: #cdd6f4; padding: 6px 10px; background: #181825; border: 1px solid #313244; border-radius: 4px;")

            # 默认目标 = 源文件夹/_organized
            if not self.target_dir:
                default_target = self.source_dir / "_organized"
                self.target_dir = default_target
                self.dst_path_label.setText(f"🎯 {default_target}")
                self.dst_path_label.setStyleSheet("color: #cdd6f4; padding: 6px 10px; background: #181825; border: 1px solid #313244; border-radius: 4px;")

            self.btn_preview.setEnabled(True)

    @Slot()
    def _on_select_target(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目标文件夹", str(self.target_dir or Path.home()))
        if dir_path:
            self.target_dir = Path(dir_path)
            self.dst_path_label.setText(f"🎯 {dir_path}")
            self.dst_path_label.setStyleSheet("color: #cdd6f4; padding: 6px 10px; background: #181825; border: 1px solid #313244; border-radius: 4px;")

    @Slot()
    def _on_template_help(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "重命名模板变量",
            "<b>可用变量:</b><br>"
            "<code>{name}</code>     — 原文件名<br>"
            "<code>{date}</code>     — 修改日期 (2024-01-15)<br>"
            "<code>{time}</code>     — 修改时间 (143022)<br>"
            "<code>{ext}</code>      — 扩展名 (pdf)<br>"
            "<code>{category}</code> — 文件类别 (文档)<br><br>"
            "<b>示例:</b><br>"
            "<code>{date}_{name}</code> → 2024-01-15_报告<br>"
            "<code>{category}/{name}</code> → 文档/报告<br>"
            "<code>{date}_{category}_{name}</code> → 2024-01-15_文档_报告"
        )

    # ── 获取选中的规则 ──

    def _get_selected_rules(self):
        rules = []
        if self.cb_category.isChecked():
            rules.append(CategoryRule())
        if self.cb_date.isChecked():
            rules.append(DateRule())
        if self.cb_extension.isChecked():
            rules.append(ExtensionRule())
        if self.cb_size.isChecked():
            rules.append(SizeRule())
        return rules if rules else [CategoryRule()]

    # ── 预览整理 ──

    @Slot()
    def _on_cancel(self):
        """取消操作"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.btn_preview.setEnabled(True)
        self.btn_execute.setEnabled(False)
        self.status_message.emit("⏹️ 操作已取消")

    @Slot()
    def _on_preview(self):
        if not self.source_dir:
            self.status_message.emit("⚠️ 请先选择源文件夹")
            return

        self._cancelled = False
        self._cancelling = False
        self.btn_preview.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_table.setRowCount(0)
        self.status_message.emit("正在扫描文件...")

        def worker():
            # 扫描文件（可取消）
            files = []
            for f in self.scanner.scan(
                str(self.source_dir),
                progress_callback=lambda i, p: self.progress_updated.emit(i % 100),
            ):
                if self._cancelled:
                    from PySide6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(self, "_on_cancel_done", Qt.QueuedConnection)
                    return
                files.append(f)

            if self._cancelled:
                return

            # 生成预览
            rules = self._get_selected_rules()
            rename = bool(self.rename_input.text().strip())
            pattern = self.rename_input.text().strip()

            operations = self.organizer.organize(
                files,
                target_root=str(self.target_dir or self.source_dir / "_organized"),
                rules=rules,
                dry_run=True,
                rename=rename,
                rename_pattern=pattern or None,
            )

            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self, "_display_preview",
                Qt.QueuedConnection,
                Q_ARG(list, operations),
                Q_ARG(list, files),
            )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _display_preview(self, operations: list[dict], files: list = None):
        """显示预览结果"""
        if files is not None:
            self.files = files
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(operations))

        for row, op in enumerate(operations):
            self.result_table.setItem(row, 0, QTableWidgetItem(op["source"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(op["destination"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(op["category"]))
            self.result_table.setItem(row, 3, QTableWidgetItem(op["size"]))

            status = QTableWidgetItem("📋 预览")
            status.setTextAlignment(Qt.AlignCenter)
            status.setForeground(Qt.gray)
            self.result_table.setItem(row, 4, status)

        self.result_table.setSortingEnabled(True)
        self.btn_preview.setEnabled(True)
        self.btn_execute.setEnabled(len(operations) > 0)
        self.progress_bar.setVisible(False)

        self.stats_label.setText(
            f"👁️ 预览: {len(operations)} 个文件将被整理，"
            f"目标: {self.target_dir or self.source_dir / '_organized'}"
        )

    # ── 执行整理 ──

    @Slot()
    def _on_cancel_done(self):
        """取消后恢复按钮状态"""
        if not self._cancelling:
            return
        self._cancelling = False
        self.btn_preview.setEnabled(True)
        self.btn_execute.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)

    @Slot()
    def _on_execute(self):
        if not self.source_dir or not self.files:
            return

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认整理",
            f"确定要整理 {len(self.files)} 个文件到\n"
            f"{self.target_dir or self.source_dir / '_organized'} 吗？\n\n"
            "此操作将移动文件，建议先备份。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._cancelled = False
        self._cancelling = False
        self.btn_execute.setEnabled(False)
        self.btn_preview.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.emit("正在执行整理...")

        def worker():
            rules = self._get_selected_rules()
            rename = bool(self.rename_input.text().strip())
            pattern = self.rename_input.text().strip()

            # 检查是否已取消（仅能在实际整理开始前取消）
            if self._cancelled:
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(self, "_on_cancel_done", Qt.QueuedConnection)
                return

            operations = self.organizer.organize(
                self.files,
                target_root=str(self.target_dir or self.source_dir / "_organized"),
                rules=rules,
                dry_run=False,
                rename=rename,
                rename_pattern=pattern or None,
                progress_callback=lambda i, name: self.progress_updated.emit(
                    int(i / len(self.files) * 100)
                ),
            )

            if not self._cancelled:
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_display_execution",
                    Qt.QueuedConnection,
                    Q_ARG(list, operations),
                )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _display_execution(self, operations: list[dict]):
        """显示执行结果"""
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(operations))

        done = 0
        for row, op in enumerate(operations):
            self.result_table.setItem(row, 0, QTableWidgetItem(op["source"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(op["destination"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(op["category"]))
            self.result_table.setItem(row, 3, QTableWidgetItem(op["size"]))

            is_dry = op.get("dry_run", False)
            status_text = "✅ 已移动" if not is_dry else "📋 预览"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            if not is_dry:
                status_item.setForeground(Qt.green)
                done += 1
            self.result_table.setItem(row, 4, status_item)

        self.result_table.setSortingEnabled(True)
        self.btn_execute.setEnabled(False)
        self.btn_preview.setEnabled(True)
        self.progress_bar.setVisible(False)

        stats = self.organizer.stats
        self.stats_label.setText(
            f"✅ 整理完成: {stats['organized_count']} 个文件已移动"
            + (f", {stats['errors']} 个错误" if stats["errors"] else "")
        )

    @Slot()
    def _clear_results(self):
        """清空结果"""
        self.result_table.setRowCount(0)
        self.btn_execute.setEnabled(False)
        self.stats_label.setText("就绪")
