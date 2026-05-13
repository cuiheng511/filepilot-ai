"""重复文件查找面板 — 扫描、分组展示、清理操作"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.ui.base_panel import BasePanel


class DuplicatesPanel(BasePanel):
    """重复文件查找面板"""

    def __init__(self, finder: DuplicateFinder | None = None, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.source_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.duplicate_groups: list[list[FileInfo]] = []
        self.finder = finder or DuplicateFinder()
        self.scanner = scanner or FileScanner()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── 标题 ──
        title = QLabel("🔗 重复文件查找")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "基于内容哈希精准查找重复文件，释放磁盘空间。\n"
            "算法：先按大小分组 → 部分哈希快速过滤 → 完整 SHA256 确认。"
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── 文件夹选择 ──
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("📂 扫描文件夹:"))
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

        # ── 选项与操作 ──
        action_layout = QHBoxLayout()

        self.cb_hash = QCheckBox("使用哈希校验 (更准确)")
        self.cb_hash.setChecked(True)
        self.cb_hash.setStyleSheet("color: #cdd6f4;")

        self.cb_similar_name = QCheckBox("查找文件名相似文件")
        self.cb_similar_name.setStyleSheet("color: #cdd6f4;")

        action_layout.addWidget(self.cb_hash)
        action_layout.addWidget(self.cb_similar_name)
        action_layout.addStretch()

        self.btn_scan = QPushButton("🔍 开始扫描")
        self.btn_scan.clicked.connect(self._on_scan)
        self.btn_scan.setEnabled(False)
        self.btn_scan.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8; color: #1e1e2e;
                border: none; border-radius: 6px;
                padding: 10px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #eba0ac; }
            QPushButton:disabled { background-color: #313244; color: #585b70; }
        """)
        action_layout.addWidget(self.btn_scan)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._clear_all)
        action_layout.addWidget(self.btn_clear)

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

        # ── 统计卡片 ──
        stats_layout = QHBoxLayout()
        self.stat_groups = self._make_stat_card("📦 重复组", "0")
        self.stat_files = self._make_stat_card("📄 重复文件", "0")
        self.stat_wasted = self._make_stat_card("💾 浪费空间", "0 B")
        self.stat_scanned = self._make_stat_card("📊 已扫描", "0 个文件")

        stats_layout.addWidget(self.stat_groups)
        stats_layout.addWidget(self.stat_files)
        stats_layout.addWidget(self.stat_wasted)
        stats_layout.addWidget(self.stat_scanned)
        layout.addLayout(stats_layout)

        # ── 结果树 + 操作 ──
        splitter = QSplitter(Qt.Vertical)

        # 上方：结果树
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["文件名", "路径", "大小", "修改日期"])
        self.result_tree.setAlternatingRowColors(True)
        self.result_tree.setAnimated(True)
        self.result_tree.setExpandsOnDoubleClick(True)
        self.result_tree.header().setStretchLastSection(True)
        self.result_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e2e; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                font-size: 13px;
            }
            QTreeWidget::item { padding: 6px 8px; border-radius: 4px; }
            QTreeWidget::item:selected { background-color: #313244; color: #cba6f7; }
            QTreeWidget::item:hover { background-color: #252538; }
            QHeaderView::section {
                background-color: #181825; color: #a6adc8;
                border: none; border-bottom: 1px solid #313244;
                padding: 8px 10px; font-weight: bold; font-size: 12px;
            }
        """)
        splitter.addWidget(self.result_tree)

        # 下方：操作按钮
        op_widget = QWidget()
        op_layout = QHBoxLayout(op_widget)
        op_layout.setContentsMargins(0, 4, 0, 0)

        self.btn_delete = QPushButton("🗑️ 删除选中的重复文件")
        self.btn_delete.clicked.connect(self._on_delete_selected)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8; color: #1e1e2e;
                border: none; border-radius: 6px;
                padding: 8px 20px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #eba0ac; }
            QPushButton:disabled { background-color: #313244; color: #585b70; }
        """)

        self.btn_select_all_dup = QPushButton("全选重复文件")
        self.btn_select_all_dup.clicked.connect(self._on_select_all_duplicates)
        self.btn_select_all_dup.setEnabled(False)

        self.btn_keep_first = QPushButton("每组保留第一个")
        self.btn_keep_first.clicked.connect(self._on_keep_first)
        self.btn_keep_first.setEnabled(False)

        op_layout.addWidget(self.btn_delete)
        op_layout.addWidget(self.btn_keep_first)
        op_layout.addWidget(self.btn_select_all_dup)
        op_layout.addStretch()
        splitter.addWidget(op_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 0)
        layout.addWidget(splitter, 1)

        # ── 底部状态 ──
        self.stats_label = QLabel("选择文件夹后开始扫描")
        self.stats_label.setStyleSheet("color: #585b70; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)

    # ── 文件夹选择 ──

    @Slot()
    def _on_select_source(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择要扫描的文件夹", str(self.source_dir or Path.home()))
        if dir_path:
            self.source_dir = Path(dir_path)
            self.dir_label.setText(f"📂 {dir_path}")
            self.dir_label.setStyleSheet(
                "color: #cdd6f4; padding: 6px 10px; background: #181825; "
                "border: 1px solid #313244; border-radius: 4px;"
            )
            self.btn_scan.setEnabled(True)

    # ── 扫描查重 ──

    @Slot()
    def _on_cancel(self):
        """取消扫描"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.status_message.emit("⏹️ 扫描已取消")

    @Slot()
    def _on_scan(self):
        if not self.source_dir:
            self.status_message.emit("⚠️ 请先选择文件夹")
            return

        self._cancelled = False
        self._cancelling = False
        self.btn_scan.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_select_all_dup.setEnabled(False)
        self.btn_keep_first.setEnabled(False)
        self.result_tree.clear()
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self._update_stat("📊 已扫描", "正在扫描...")
        self.status_message.emit("正在扫描文件...")

        def worker():
            # 1. 扫描文件（可取消）
            files = []
            for f in self.scanner.scan(
                str(self.source_dir),
                progress_callback=lambda i, p: self.progress_updated.emit(i % 100),
            ):
                if self._cancelled:
                    return
                files.append(f)

            if self._cancelled:
                return

            self.progress_updated.emit(50)

            # 2. 查找重复
            use_hash = self.cb_hash.isChecked()
            groups = self.finder.find_duplicates(
                files,
                use_hash=use_hash,
            )

            if self._cancelled:
                return

            # 3. 查找文件名相似
            similar_groups = []
            if self.cb_similar_name.isChecked():
                similar_groups = self.finder.find_similar_by_name(files)

            if not self._cancelled:
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_display_results",
                    Qt.QueuedConnection,
                    Q_ARG(list, groups),
                    Q_ARG(list, similar_groups),
                    Q_ARG(list, files),
                )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _display_results(self, groups: list[list[FileInfo]], similar_groups: list[list[FileInfo]], files: list = None):
        """显示查重结果"""
        if files is not None:
            self.files = files
        self.result_tree.clear()
        self.duplicate_groups = groups

        # ── 精确重复组 ──
        for i, group in enumerate(groups, 1):
            kept = group[0]
            wasted = sum(f.size_bytes for f in group[1:])
            wasted_str = self._format_bytes(wasted)

            # 组标题
            group_item = QTreeWidgetItem(self.result_tree)
            group_item.setText(
                0,
                f"📋 重复组 #{i}  ({len(group)} 个文件, 可释放 {wasted_str})"
            )
            group_item.setToolTip(0, f"保留: {kept.path}\n浪费空间: {wasted_str}")
            group_item.setExpanded(i <= 3)  # 默认展开前3组

            # 用粗体
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)

            # 组内文件
            for j, f in enumerate(group):
                child = QTreeWidgetItem(group_item)
                child.setText(0, f.name)
                child.setText(1, str(f.path))
                child.setText(2, f.size_str)
                child.setText(3, f.modified_time.strftime("%Y-%m-%d %H:%M"))
                child.setToolTip(0, str(f.path))

                # 第一个文件标为"保留"
                if j == 0:
                    child.setText(0, f"⭐ {f.name} (保留)")
                    child.setForeground(0, Qt.green)

                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked if j > 0 else Qt.Unchecked)
                child.setData(0, Qt.UserRole, str(f.path))

        # ── 相似文件名组 ──
        if similar_groups:
            sep = QTreeWidgetItem(self.result_tree)
            sep.setText(0, f"📎 文件名相似文件 ({len(similar_groups)} 组)")
            font = sep.font(0)
            font.setBold(True)
            sep.setFont(0, font)

            for i, group in enumerate(similar_groups, 1):
                sg = QTreeWidgetItem(sep)
                sg.setText(0, f"相似组 #{i} ({len(group)} 个文件)")
                sg.setExpanded(False)

                for f in group:
                    child = QTreeWidgetItem(sg)
                    child.setText(0, f.name)
                    child.setText(1, str(f.path))
                    child.setText(2, f.size_str)
                    child.setToolTip(0, str(f.path))
                    child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.Unchecked)
                    child.setData(0, Qt.UserRole, str(f.path))

        # ── 更新统计 ──
        stats = self.finder.get_duplicate_stats(groups)
        self._update_stat("📦 重复组", str(stats["groups"]))
        self._update_stat("📄 重复文件", str(stats["duplicate_files"]))
        self._update_stat("💾 浪费空间", stats["wasted_space_str"])
        self._update_stat("📊 已扫描", f"{len(self.files)} 个文件")

        self.btn_scan.setEnabled(True)
        self.progress_bar.setVisible(False)

        has_results = len(groups) > 0
        self.btn_delete.setEnabled(has_results)
        self.btn_select_all_dup.setEnabled(has_results)
        self.btn_keep_first.setEnabled(has_results)
        self.btn_cancel.setVisible(False)

        if has_results:
            self.status_message.emit(
                f"🔍 找到 {stats['groups']} 组重复文件，"
                f"共 {stats['duplicate_files']} 个重复文件，"
                f"可释放 {stats['wasted_space_str']}"
            )
        else:
            self.status_message.emit("✅ 未找到重复文件")

    # ── 操作处理 ──

    @Slot()
    def _on_delete_selected(self):
        """删除选中的重复文件"""
        selected_paths = self._get_checked_paths()
        if not selected_paths:
            self.status_message.emit("⚠️ 请勾选要删除的文件（记得保留每组至少一个）")
            return

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.warning(
            self,
            "确认删除",
            f"确定要删除 {len(selected_paths)} 个文件吗？\n\n"
            "文件将被移至回收站。此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        deleted = 0
        errors = 0
        for path_str in selected_paths:
            try:
                Path(path_str).unlink()
                deleted += 1
            except (OSError, PermissionError) as e:
                errors += 1

        # 重新扫描显示
        self.status_message.emit(f"✅ 已删除 {deleted} 个文件" + (f", {errors} 个失败" if errors else ""))
        self._on_scan()

    @Slot()
    def _on_select_all_duplicates(self):
        """全选所有重复文件（不选每组的第一个）"""
        for i in range(self.result_tree.topLevelItemCount()):
            group = self.result_tree.topLevelItem(i)
            if not group or not group.text(0).startswith("📋"):
                continue
            for j in range(1, group.childCount()):  # 从1开始，跳过保留的
                child = group.child(j)
                child.setCheckState(0, Qt.Checked)

    @Slot()
    def _on_keep_first(self):
        """每组只勾选保留第一个之外的文件"""
        self._on_select_all_duplicates()

    def _get_checked_paths(self) -> list[str]:
        """获取所有勾选的文件路径"""
        paths = []
        for i in range(self.result_tree.topLevelItemCount()):
            group = self.result_tree.topLevelItem(i)
            if not group:
                continue
            for j in range(group.childCount()):
                child = group.child(j)
                if child.checkState(0) == Qt.Checked:
                    path = child.data(0, Qt.UserRole)
                    if path:
                        paths.append(path)
        return paths

    @Slot()
    def _clear_all(self):
        """清空所有结果"""
        self.result_tree.clear()
        self.duplicate_groups = []
        self._update_stat("📦 重复组", "0")
        self._update_stat("📄 重复文件", "0")
        self._update_stat("💾 浪费空间", "0 B")
        self.btn_delete.setEnabled(False)
        self.btn_select_all_dup.setEnabled(False)
        self.btn_keep_first.setEnabled(False)
        self.stats_label.setText("就绪")

    def _format_bytes(self, size: int) -> str:
        """格式化字节数"""
        from filepilot.utils.file_utils import get_file_size_str
        return get_file_size_str(size)
