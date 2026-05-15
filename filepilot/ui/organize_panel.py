"""Organize Panel — Auto-classify, smart rename, batch regex rename"""

import re
from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from filepilot.i18n import t
from filepilot.ui.base_panel import BasePanel


class OrganizePanel(BasePanel):
    """File Organize Panel"""

    RULE_MAP = {
        "category": CategoryRule,
        "date": DateRule,
        "extension": ExtensionRule,
        "size": SizeRule,
    }

    def __init__(
        self,
        organizer: FileOrganizer | None = None,
        scanner: FileScanner | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.source_dir: Path | None = None
        self.target_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.organizer = organizer or FileOrganizer()
        self.scanner = scanner or FileScanner()

        self._setup_ui()
        self._connect_signals()

    def update_services(
        self, scanner: FileScanner | None = None, organizer: FileOrganizer | None = None
    ):
        """Update service references without recreating the panel"""
        if scanner is not None:
            self.scanner = scanner
        if organizer is not None:
            self.organizer = organizer

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── Title ──
        title = QLabel("\U0001f4cb File Organizer")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Select source and target folders, configure rules, and organize files.\n"
            "Supports auto-classification by type, date, extension, size, and smart renaming.",
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── Directory Selection ──
        dir_group = QGroupBox("Folders")
        dir_layout = QVBoxLayout()
        dir_layout.setSpacing(8)

        # Source folder
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("\U0001f4c2 Source Folder:"))
        self.src_path_label = QLabel("Not selected")
        self.src_path_label.setObjectName("pathLabel")
        self.src_path_label.setWordWrap(True)
        self.btn_src = QPushButton("Browse...")
        self.btn_src.clicked.connect(self._on_select_source)
        src_layout.addWidget(self.src_path_label, 1)
        src_layout.addWidget(self.btn_src)
        dir_layout.addLayout(src_layout)

        # Target folder
        dst_layout = QHBoxLayout()
        dst_layout.addWidget(QLabel("\U0001f3af Target Folder:"))
        self.dst_path_label = QLabel("Not selected (default: source_folder/_organized)")
        self.dst_path_label.setObjectName("pathLabel")
        self.dst_path_label.setWordWrap(True)
        self.btn_dst = QPushButton("Browse...")
        self.btn_dst.clicked.connect(self._on_select_target)
        dst_layout.addWidget(self.dst_path_label, 1)
        dst_layout.addWidget(self.btn_dst)
        dir_layout.addLayout(dst_layout)

        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # ── Organize Rules ──
        rule_group = QGroupBox("Organize Rules")
        rule_layout = QHBoxLayout()
        rule_layout.setSpacing(16)

        self.cb_category = QCheckBox("\U0001f4c2 By File Type")
        self.cb_category.setChecked(True)
        self.cb_date = QCheckBox("\U0001f4c5 By Date (Year/Month)")
        self.cb_extension = QCheckBox("\U0001f4ce By Extension")
        self.cb_size = QCheckBox("\U0001f4cf By File Size")

        rule_layout.addWidget(self.cb_category)
        rule_layout.addWidget(self.cb_date)
        rule_layout.addWidget(self.cb_extension)
        rule_layout.addWidget(self.cb_size)
        rule_layout.addStretch()
        rule_group.setLayout(rule_layout)
        layout.addWidget(rule_group)

        # ── Rename Settings ──
        rename_layout = QHBoxLayout()
        rename_layout.addWidget(QLabel("\u270f\ufe0f Rename Template:"))
        self.rename_input = QLineEdit()
        self.rename_input.setPlaceholderText(
            "Leave empty for no rename. Supports: {name} {date} {time} {ext} {category}"
        )
        rename_layout.addWidget(self.rename_input, 1)

        self.template_btn = QPushButton("Template Help")
        self.template_btn.setToolTip(
            "Available variables:\n"
            "  {name}     \u2014 Original filename\n"
            "  {date}     \u2014 Modified date (2024-01-15)\n"
            "  {time}     \u2014 Modified time (143022)\n"
            "  {ext}      \u2014 Extension (pdf)\n"
            "  {category} \u2014 File category (Document)",
        )
        self.template_btn.clicked.connect(self._on_template_help)
        rename_layout.addWidget(self.template_btn)

        layout.addLayout(rename_layout)

        # ── Batch Regex Rename ──
        regex_group = QGroupBox("\U0001f504 Batch Regex Rename")
        regex_layout = QVBoxLayout()
        regex_layout.setSpacing(8)

        regex_pattern_layout = QHBoxLayout()
        regex_pattern_layout.addWidget(QLabel("Pattern:"))
        self.regex_pattern_input = QLineEdit()
        self.regex_pattern_input.setPlaceholderText(r"e.g., ^(\d{4})-(\d{2})-(\d{2})_")
        regex_pattern_layout.addWidget(self.regex_pattern_input, 1)
        regex_layout.addLayout(regex_pattern_layout)

        regex_replacement_layout = QHBoxLayout()
        regex_replacement_layout.addWidget(QLabel("Replace:"))
        self.regex_replacement_input = QLineEdit()
        self.regex_replacement_input.setPlaceholderText(r"e.g., \2/\3/\1_")
        regex_replacement_layout.addWidget(self.regex_replacement_input, 1)
        regex_layout.addLayout(regex_replacement_layout)

        regex_options_layout = QHBoxLayout()
        self.regex_case_cb = QCheckBox("Case insensitive")
        self.regex_preview_btn = QPushButton("Preview")
        self.regex_preview_btn.clicked.connect(self._on_regex_preview)
        self.regex_execute_btn = QPushButton("Execute")
        self.regex_execute_btn.setObjectName("btnSuccess")
        self.regex_execute_btn.clicked.connect(self._on_regex_execute)
        self.regex_execute_btn.setEnabled(False)
        regex_options_layout.addWidget(self.regex_case_cb)
        regex_options_layout.addStretch()
        regex_options_layout.addWidget(self.regex_preview_btn)
        regex_options_layout.addWidget(self.regex_execute_btn)
        regex_layout.addLayout(regex_options_layout)

        regex_group.setLayout(regex_layout)
        layout.addWidget(regex_group)

        # ── Action Buttons ──
        action_layout = QHBoxLayout()
        self.btn_preview = QPushButton(t("organize_preview"))
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_preview.setEnabled(False)

        self.btn_execute = QPushButton(t("organize_execute"))
        self.btn_execute.setObjectName("btnSuccess")
        self.btn_execute.clicked.connect(self._on_execute)
        self.btn_execute.setEnabled(False)

        self.btn_clear = QPushButton("Clear Results")
        self.btn_clear.clicked.connect(self._clear_results)

        self.btn_undo = QPushButton(t("organize_undo"))
        self.btn_undo.setObjectName("btnWarning")
        self.btn_undo.clicked.connect(self._on_undo)
        self.btn_undo.setEnabled(False)

        action_layout.addWidget(self.btn_preview)
        action_layout.addWidget(self.btn_execute)
        action_layout.addWidget(self.btn_undo)
        action_layout.addWidget(self.btn_clear)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Progress bar + cancel button
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)

        self.btn_cancel = QPushButton("\u2715 Cancel")
        self.btn_cancel.setObjectName("btnDanger")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        progress_layout.addWidget(self.btn_cancel)
        layout.addLayout(progress_layout)

        # ── Results Table ──
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(
            ["Source Path", "Target Path", "Category", "Size", "Status"]
        )
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        layout.addWidget(self.result_table, 1)

        # ── Status Bar ──
        self.stats_label = QLabel("Select a source folder to start preview")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)

    # ── Directory Selection ──

    @Slot()
    def _on_select_source(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if dir_path:
            self.source_dir = Path(dir_path)
            self.src_path_label.setText(f"\U0001f4c2 {dir_path}")
            self.src_path_label.setProperty("selected", True)
            self.src_path_label.style().unpolish(self.src_path_label)
            self.src_path_label.style().polish(self.src_path_label)

            # Default target = source folder/_organized
            if not self.target_dir:
                default_target = self.source_dir / "_organized"
                self.target_dir = default_target
                self.dst_path_label.setText(f"\U0001f3af {default_target}")
                self.dst_path_label.setProperty("selected", True)
                self.dst_path_label.style().unpolish(self.dst_path_label)
                self.dst_path_label.style().polish(self.dst_path_label)

            self.btn_preview.setEnabled(True)

    @Slot()
    def _on_select_target(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Target Folder", str(self.target_dir or Path.home())
        )
        if dir_path:
            self.target_dir = Path(dir_path)
            self.dst_path_label.setText(f"\U0001f3af {dir_path}")
            self.dst_path_label.setProperty("selected", True)
            self.dst_path_label.style().unpolish(self.dst_path_label)
            self.dst_path_label.style().polish(self.dst_path_label)

    @Slot()
    def _on_template_help(self):
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Rename Template Variables",
            "<b>Available variables:</b><br>"
            "<code>{name}</code>     \u2014 Original filename<br>"
            "<code>{date}</code>     \u2014 Modified date (2024-01-15)<br>"
            "<code>{time}</code>     \u2014 Modified time (143022)<br>"
            "<code>{ext}</code>      \u2014 Extension (pdf)<br>"
            "<code>{category}</code> \u2014 File category (Document)<br><br>"
            "<b>Examples:</b><br>"
            "<code>{date}_{name}</code> \u2192 2024-01-15_report<br>"
            "<code>{category}/{name}</code> \u2192 Document/report<br>"
            "<code>{date}_{category}_{name}</code> \u2192 2024-01-15_Document_report",
        )

    # ── Get Selected Rules ──

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
        return rules or [CategoryRule()]

    # ── Preview ──

    @Slot()
    def _on_cancel(self):
        """Cancel operation"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.btn_preview.setEnabled(True)
        self.btn_execute.setEnabled(False)
        self.status_message.emit("\u23f9\ufe0f Operation cancelled")

    @Slot()
    def _on_preview(self):
        if not self.source_dir:
            self.status_message.emit("\u26a0\ufe0f Please select a source folder first")
            return

        self._cancelled = False
        self._cancelling = False
        self.btn_preview.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_table.setRowCount(0)
        self.status_message.emit("Scanning files...")

        def worker():
            # Scan files (cancellable)
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

            # Generate preview
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

            from PySide6.QtCore import Q_ARG, QMetaObject, Qt

            QMetaObject.invokeMethod(
                self,
                "_display_preview",
                Qt.QueuedConnection,
                Q_ARG(list, operations),
                Q_ARG(list, files),
            )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _display_preview(self, operations: list[dict], files: list | None = None):
        """Display preview results"""
        if files is not None:
            self.files = files
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(operations))

        for row, op in enumerate(operations):
            self.result_table.setItem(row, 0, QTableWidgetItem(op["source"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(op["destination"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(op["category"]))
            self.result_table.setItem(row, 3, QTableWidgetItem(op["size"]))

            status = QTableWidgetItem("\U0001f4cb Preview")
            status.setTextAlignment(Qt.AlignCenter)
            status.setForeground(Qt.gray)
            self.result_table.setItem(row, 4, status)

        self.result_table.setSortingEnabled(True)
        self.btn_preview.setEnabled(True)
        self.btn_execute.setEnabled(len(operations) > 0)
        self.progress_bar.setVisible(False)

        target_root = self.target_dir or (
            (self.source_dir / "_organized") if self.source_dir else Path()
        )
        self.stats_label.setText(
            f"\U0001f441\ufe0f Preview: {len(operations)} files will be organized, "
            f"target: {target_root}",
        )

    # ── Execute ──

    @Slot()
    def _on_cancel_done(self):
        """Restore button state after cancel"""
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
            "Confirm Organization",
            f"Organize {len(self.files)} files into\n"
            f"{self.target_dir or self.source_dir / '_organized'}?\n\n"
            "This will move files. Backup recommended.",
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
        self.status_message.emit("Organizing files...")

        def worker():
            rules = self._get_selected_rules()
            rename = bool(self.rename_input.text().strip())
            pattern = self.rename_input.text().strip()

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
                    int(i / len(self.files) * 100),
                ),
            )

            if not self._cancelled:
                from PySide6.QtCore import Q_ARG, QMetaObject, Qt

                QMetaObject.invokeMethod(
                    self,
                    "_display_execution",
                    Qt.QueuedConnection,
                    Q_ARG(list, operations),
                )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _display_execution(self, operations: list[dict]):
        """Display execution results"""
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(operations))

        done = 0
        for row, op in enumerate(operations):
            self.result_table.setItem(row, 0, QTableWidgetItem(op["source"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(op["destination"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(op["category"]))
            self.result_table.setItem(row, 3, QTableWidgetItem(op["size"]))

            is_dry = op.get("dry_run", False)
            status_text = "\u2705 Moved" if not is_dry else "\U0001f4cb Preview"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            if not is_dry:
                status_item.setForeground(Qt.green)
                done += 1
            self.result_table.setItem(row, 4, status_item)

        self.result_table.setSortingEnabled(True)
        self.btn_execute.setEnabled(False)
        self.btn_preview.setEnabled(True)
        self.btn_undo.setEnabled(done > 0)
        self.progress_bar.setVisible(False)

        # Save undo log
        if done > 0:
            undo_path = Path.home() / ".filepilot" / "last_undo.json"
            undo_path.parent.mkdir(parents=True, exist_ok=True)
            self.organizer.save_undo_log(undo_path)

        stats = self.organizer.stats
        self.stats_label.setText(
            f"\u2705 Organization complete: {stats['organized_count']} files moved"
            + (f", {stats['errors']} errors" if stats["errors"] else ""),
        )

    @Slot()
    def _on_undo(self):
        """Undo last organize operation"""
        from PySide6.QtWidgets import QMessageBox

        undo_path = Path.home() / ".filepilot" / "last_undo.json"
        if not undo_path.exists():
            QMessageBox.warning(self, "Undo Failed", "No undo log found")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Undo",
            "Undo the last organize operation? Files will be moved back to their original locations.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        result = self.organizer.undo(undo_path)
        self.stats_label.setText(
            f"\u21a9\ufe0f Undo complete: restored {result['restored']} files"
            + (f", {result['errors']} failed" if result["errors"] else ""),
        )
        self.btn_undo.setEnabled(False)
        self.result_table.setRowCount(0)

    @Slot()
    def _clear_results(self):
        """Clear results"""
        self.result_table.setRowCount(0)
        self.btn_execute.setEnabled(False)
        self.stats_label.setText("Ready")

    # ── Batch Regex Rename ──

    @Slot()
    def _on_regex_preview(self):
        """Preview regex rename results."""
        pattern = self.regex_pattern_input.text().strip()
        if not pattern:
            self.status_message.emit("\u26a0\ufe0f Please enter a regex pattern")
            return

        try:
            flags = re.IGNORECASE if self.regex_case_cb.isChecked() else 0
            compiled = re.compile(pattern, flags)
        except re.error as e:
            self.status_message.emit(f"\u274c Invalid regex: {e}")
            return

        if not self.source_dir:
            self.status_message.emit("\u26a0\ufe0f Please select a source folder first")
            return

        self._cancelled = False
        self._cancelling = False
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.emit("Scanning files for regex preview...")

        def worker():
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

            replacement = self.regex_replacement_input.text()
            operations = []
            for f in files:
                new_name = compiled.sub(replacement, f.name)
                if new_name != f.name:
                    operations.append(
                        {
                            "source": str(f.path),
                            "destination": str(f.path.parent / new_name),
                            "category": "Regex Rename",
                            "size": f.size_str,
                        }
                    )

            from PySide6.QtCore import Q_ARG, QMetaObject, Qt

            QMetaObject.invokeMethod(
                self,
                "_display_regex_preview",
                Qt.QueuedConnection,
                Q_ARG(list, operations),
            )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _display_regex_preview(self, operations: list[dict]):
        """Display regex rename preview results."""
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(operations))

        for row, op in enumerate(operations):
            self.result_table.setItem(row, 0, QTableWidgetItem(op["source"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(op["destination"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(op["category"]))
            self.result_table.setItem(row, 3, QTableWidgetItem(op["size"]))

            status = QTableWidgetItem("\U0001f4cb Preview")
            status.setTextAlignment(Qt.AlignCenter)
            status.setForeground(Qt.gray)
            self.result_table.setItem(row, 4, status)

        self.result_table.setSortingEnabled(True)
        self.regex_execute_btn.setEnabled(len(operations) > 0)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)

        self.stats_label.setText(
            f"\U0001f441\ufe0f Regex Preview: {len(operations)} files will be renamed"
        )

    @Slot()
    def _on_regex_execute(self):
        """Execute regex rename on scanned files."""
        pattern = self.regex_pattern_input.text().strip()
        if not pattern:
            return

        try:
            flags = re.IGNORECASE if self.regex_case_cb.isChecked() else 0
            compiled = re.compile(pattern, flags)
        except re.error as e:
            self.status_message.emit(f"\u274c Invalid regex: {e}")
            return

        if not self.files:
            self.status_message.emit("\u26a0\ufe0f Please scan files first")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Regex Rename",
            f"Rename {len(self.files)} files using regex pattern?\n\n"
            f"Pattern: {pattern}\n"
            f"Replace: {self.regex_replacement_input.text()}\n\n"
            "This will rename files. Backup recommended.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._cancelled = False
        self._cancelling = False
        self.btn_execute.setEnabled(False)
        self.btn_preview.setEnabled(False)
        self.regex_execute_btn.setEnabled(False)
        self.regex_preview_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.emit("Renaming files with regex...")

        def worker():
            replacement = self.regex_replacement_input.text()
            operations = []
            success_count = 0
            error_count = 0

            for i, f in enumerate(self.files):
                if self._cancelled:
                    return

                new_name = compiled.sub(replacement, f.name)
                if new_name != f.name:
                    new_path = f.path.parent / new_name
                    try:
                        f.path.rename(new_path)
                        operations.append(
                            {
                                "source": str(f.path),
                                "destination": str(new_path),
                                "category": "Regex Rename",
                                "size": f.size_str,
                                "status": "\u2705 Renamed",
                            }
                        )
                        success_count += 1
                    except Exception as e:
                        operations.append(
                            {
                                "source": str(f.path),
                                "destination": str(new_path),
                                "category": "Regex Rename",
                                "size": f.size_str,
                                "status": f"\u274c Error: {e}",
                            }
                        )
                        error_count += 1

                self.progress_updated.emit(int((i + 1) / len(self.files) * 100))

            from PySide6.QtCore import Q_ARG, QMetaObject, Qt

            QMetaObject.invokeMethod(
                self,
                "_display_regex_execution",
                Qt.QueuedConnection,
                Q_ARG(list, operations),
                Q_ARG(int, success_count),
                Q_ARG(int, error_count),
            )

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _display_regex_execution(
        self, operations: list[dict], success_count: int, error_count: int
    ):
        """Display regex rename execution results."""
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(operations))

        for row, op in enumerate(operations):
            self.result_table.setItem(row, 0, QTableWidgetItem(op["source"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(op["destination"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(op["category"]))
            self.result_table.setItem(row, 3, QTableWidgetItem(op["size"]))

            status = QTableWidgetItem(op.get("status", "\u2705 Renamed"))
            status.setTextAlignment(Qt.AlignCenter)
            if "\u2705" in op.get("status", ""):
                status.setForeground(Qt.green)
            elif "\u274c" in op.get("status", ""):
                status.setForeground(Qt.red)
            self.result_table.setItem(row, 4, status)

        self.result_table.setSortingEnabled(True)
        self.btn_preview.setEnabled(True)
        self.regex_preview_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)

        self.stats_label.setText(
            f"\u2705 Regex rename complete: {success_count} renamed"
            + (f", {error_count} errors" if error_count else "")
        )
