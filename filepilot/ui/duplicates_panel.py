"""Deduplication panel — scan, group, and clean up duplicate files"""

import importlib
from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.app_state import AppState
from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.event_bus import EventBus
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.ui.base_panel import BasePanel


class DuplicatesPanel(BasePanel):
    """Duplicate file finder panel"""

    def __init__(
        self,
        finder: DuplicateFinder | None = None,
        scanner: FileScanner | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.source_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.duplicate_groups: list[list[FileInfo]] = []
        self.finder = finder or DuplicateFinder()
        self.scanner = scanner or FileScanner()
        self.state = app_state
        self.event_bus = event_bus

        self._setup_ui()
        self._connect_signals()

    def update_services(
        self,
        scanner: FileScanner | None = None,
        finder: DuplicateFinder | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
    ):
        """Update service references without recreating the panel"""
        if scanner is not None:
            self.scanner = scanner
        if finder is not None:
            self.finder = finder
        if app_state is not None:
            self.state = app_state
        if event_bus is not None:
            self.event_bus = event_bus

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._create_title_section(layout)
        self._create_folder_selection(layout)
        self._create_options_and_actions(layout)
        self._create_progress_bar(layout)
        self._create_stat_cards(layout)
        self._create_result_splitter(layout)
        self._create_status_bar(layout)

    def _create_title_section(self, layout):
        title = QLabel("🔗 Duplicate File Finder")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        desc = QLabel(
            "Find duplicate files based on content hash to free up disk space.\n"
            "Algorithm: group by size -> partial hash filter -> full SHA256 verification.",
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

    def _create_folder_selection(self, layout):
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("📂 Scan folder:"))
        self.dir_label = QLabel("Not selected")
        self.dir_label.setObjectName("pathLabel")
        self.dir_label.setWordWrap(True)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._on_select_source)
        dir_layout.addWidget(self.dir_label, 1)
        dir_layout.addWidget(self.btn_browse)
        layout.addLayout(dir_layout)

    def _create_options_and_actions(self, layout):
        action_layout = QHBoxLayout()
        self.cb_hash = QCheckBox("Use hash verification (more accurate)")
        self.cb_hash.setChecked(True)
        self.cb_similar_name = QCheckBox("Find similar file names")
        action_layout.addWidget(self.cb_hash)
        action_layout.addWidget(self.cb_similar_name)
        action_layout.addStretch()
        self.btn_scan = QPushButton("🔍 Start Scan")
        self.btn_scan.setObjectName("btnDanger")
        self.btn_scan.clicked.connect(self._on_scan)
        self.btn_scan.setEnabled(False)
        action_layout.addWidget(self.btn_scan)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear_all)
        action_layout.addWidget(self.btn_clear)
        layout.addLayout(action_layout)

    def _create_progress_bar(self, layout):
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)
        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.setObjectName("btnDanger")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        progress_layout.addWidget(self.btn_cancel)
        layout.addLayout(progress_layout)

    def _create_stat_cards(self, layout):
        stats_layout = QHBoxLayout()
        self.stat_groups = self._make_stat_card("📦 Duplicate Groups", "0")
        self.stat_files = self._make_stat_card("📄 Duplicate Files", "0")
        self.stat_wasted = self._make_stat_card("💾 Wasted Space", "0 B")
        self.stat_scanned = self._make_stat_card("📊 Scanned", "0 files")
        stats_layout.addWidget(self.stat_groups)
        stats_layout.addWidget(self.stat_files)
        stats_layout.addWidget(self.stat_wasted)
        stats_layout.addWidget(self.stat_scanned)
        layout.addLayout(stats_layout)

    def _create_result_splitter(self, layout):
        splitter = QSplitter(Qt.Vertical)
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["File Name", "Path", "Size", "Modified Date"])
        self.result_tree.setAlternatingRowColors(True)
        self.result_tree.setAnimated(True)
        self.result_tree.setExpandsOnDoubleClick(True)
        self.result_tree.header().setStretchLastSection(True)
        self.result_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        splitter.addWidget(self.result_tree)
        op_widget = QWidget()
        op_layout = QHBoxLayout(op_widget)
        op_layout.setContentsMargins(0, 4, 0, 0)
        self.btn_delete = QPushButton("🗑️ Delete Selected Duplicates")
        self.btn_delete.setObjectName("btnDanger")
        self.btn_delete.clicked.connect(self._on_delete_selected)
        self.btn_delete.setEnabled(False)
        self.btn_select_all_dup = QPushButton("Select All Duplicates")
        self.btn_select_all_dup.clicked.connect(self._on_select_all_duplicates)
        self.btn_select_all_dup.setEnabled(False)
        self.btn_keep_first = QPushButton("Keep First in Each Group")
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

    def _create_status_bar(self, layout):
        self.stats_label = QLabel("Select a folder and start scanning")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)

    # ── Folder selection ──

    @Slot()
    def _on_select_source(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select folder to scan", str(self.source_dir or Path.home())
        )
        if dir_path:
            self.source_dir = Path(dir_path)
            self.dir_label.setText(f"📂 {dir_path}")
            self.dir_label.setProperty("selected", True)
            self.dir_label.style().unpolish(self.dir_label)
            self.dir_label.style().polish(self.dir_label)
            self.btn_scan.setEnabled(True)

    # ── Scan for duplicates ──

    @Slot()
    def _on_cancel(self):
        """Cancel scanning"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.status_message.emit("⏹️ Scan cancelled")

    @Slot()
    def _on_scan(self):
        if not self.source_dir:
            self.status_message.emit("⚠️ Please select a folder first")
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
        self._update_stat("📊 Scanned", "Scanning...")
        self.status_message.emit("Scanning files...")

        def worker():
            # 1. Scan files (cancellable)
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

            # 2. Find duplicates
            use_hash = self.cb_hash.isChecked()
            groups = self.finder.find_duplicates(
                files,
                use_hash=use_hash,
            )

            if self._cancelled:
                return

            # 3. Find similar file names
            similar_groups = []
            if self.cb_similar_name.isChecked():
                similar_groups = self.finder.find_similar_by_name(files)

            if not self._cancelled:
                from PySide6.QtCore import Q_ARG, QMetaObject, Qt

                QMetaObject.invokeMethod(
                    self,
                    "_display_results",
                    Qt.QueuedConnection,
                    Q_ARG(list, groups),
                    Q_ARG(list, similar_groups),
                    Q_ARG(list, files),
                )

        Thread(target=worker, daemon=True).start()

    @Slot(list, list, list)
    def _display_results(
        self,
        groups: list[list[FileInfo]],
        similar_groups: list[list[FileInfo]],
        files: list | None = None,
    ):
        """Display deduplication results"""
        if files is not None:
            self.files = files
        self.result_tree.clear()
        self.duplicate_groups = groups

        # ── Exact duplicate groups ──
        for i, group in enumerate(groups, 1):
            kept = group[0]
            wasted = sum(f.size_bytes for f in group[1:])
            wasted_str = self._format_bytes(wasted)

            # Group header
            group_item = QTreeWidgetItem(self.result_tree)
            group_item.setText(
                0,
                f"📋 Duplicate Group #{i}  ({len(group)} files, {wasted_str} reclaimable)",
            )
            group_item.setToolTip(0, f"Keep: {kept.path}\nWasted space: {wasted_str}")
            group_item.setExpanded(i <= 3)  # Expand first 3 groups by default

            # Bold font
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)

            # Files in group
            for j, f in enumerate(group):
                child = QTreeWidgetItem(group_item)
                child.setText(0, f.name)
                child.setText(1, str(f.path))
                child.setText(2, f.size_str)
                child.setText(3, f.modified_time.strftime("%Y-%m-%d %H:%M"))
                child.setToolTip(0, str(f.path))

                # First file marked as "keep"
                if j == 0:
                    child.setText(0, f"⭐ {f.name} (keep)")
                    child.setForeground(0, Qt.green)

                if j == 0:
                    child.setFlags(child.flags() & ~Qt.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.Unchecked)
                else:
                    child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.Unchecked)
                child.setData(0, Qt.UserRole, str(f.path))

        # ── Similar file name groups ──
        if similar_groups:
            sep = QTreeWidgetItem(self.result_tree)
            sep.setText(0, f"📎 Similar File Names ({len(similar_groups)} groups)")
            font = sep.font(0)
            font.setBold(True)
            sep.setFont(0, font)

            for i, group in enumerate(similar_groups, 1):
                sg = QTreeWidgetItem(sep)
                sg.setText(0, f"Similar Group #{i} ({len(group)} files)")
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

        # ── Update stats ──
        stats = self.finder.get_duplicate_stats(groups)
        self._update_stat("📦 Duplicate Groups", str(stats["groups"]))
        self._update_stat("📄 Duplicate Files", str(stats["duplicate_files"]))
        self._update_stat("💾 Wasted Space", stats["wasted_space_str"])
        self._update_stat("📊 Scanned", f"{len(self.files)} files")

        self.btn_scan.setEnabled(True)
        self.progress_bar.setVisible(False)

        has_results = len(groups) > 0
        self.btn_delete.setEnabled(has_results)
        self.btn_select_all_dup.setEnabled(has_results)
        self.btn_keep_first.setEnabled(has_results)
        self.btn_cancel.setVisible(False)

        if has_results:
            self.status_message.emit(
                f"🔍 Found {stats['groups']} duplicate groups, "
                f"{stats['duplicate_files']} duplicate files, "
                f"can reclaim {stats['wasted_space_str']}",
            )
        else:
            self.status_message.emit("✅ No duplicates found")

    # ── Action handlers ──

    @Slot()
    def _on_delete_selected(self):
        """Delete selected duplicate files"""
        selected_paths = self._get_checked_paths()
        if not selected_paths:
            self.status_message.emit(
                "⚠️ Please check the files to delete (keep at least one per group)"
            )
            return

        try:
            send2trash = importlib.import_module("send2trash")
        except ImportError:
            self.status_message.emit("⚠️ Safe deletion is unavailable. Please install send2trash.")
            return

        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(selected_paths)} files?\n\n"
            "Files will be moved to the recycle bin. This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        deleted = 0
        errors = 0
        for path_str in selected_paths:
            try:
                send2trash.send2trash(path_str)
                deleted += 1
            except (OSError, PermissionError):
                errors += 1

        # Re-scan
        self.status_message.emit(
            f"✅ Deleted {deleted} files" + (f", {errors} failed" if errors else "")
        )
        self._on_scan()

    @Slot()
    def _on_select_all_duplicates(self):
        """Select all duplicate files (skip first in each group)"""
        for i in range(self.result_tree.topLevelItemCount()):
            group = self.result_tree.topLevelItem(i)
            if not group or not group.text(0).startswith("📋"):
                continue
            for j in range(1, group.childCount()):
                child = group.child(j)
                child.setCheckState(0, Qt.Checked)

    @Slot()
    def _on_keep_first(self):
        """Only check files beyond the first in each group"""
        self._on_select_all_duplicates()

    def _get_checked_paths(self) -> list[str]:
        """Get all checked file paths"""
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
        """Clear all results"""
        self.result_tree.clear()
        self.duplicate_groups = []
        self._update_stat("📦 Duplicate Groups", "0")
        self._update_stat("📄 Duplicate Files", "0")
        self._update_stat("💾 Wasted Space", "0 B")
        self.btn_delete.setEnabled(False)
        self.btn_select_all_dup.setEnabled(False)
        self.btn_keep_first.setEnabled(False)
        self.stats_label.setText("Ready")

    def _format_bytes(self, size: int) -> str:
        """Format byte size to human-readable string"""
        from filepilot.utils.file_utils import get_file_size_str

        return get_file_size_str(size)
