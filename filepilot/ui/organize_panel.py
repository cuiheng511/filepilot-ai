"""Organize Panel — Auto-classify, smart rename, batch regex rename"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, Signal, Slot
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

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.core.file_organizer import (
    CategoryRule,
    DateRule,
    ExtensionRule,
    FileOrganizer,
    SizeRule,
)
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.worker import Worker
from filepilot.i18n import t
from filepilot.ui.base_panel import BasePanel


class OrganizePanel(BasePanel):
    """File Organize Panel"""

    preview_ready = Signal(list, list)
    execute_ready = Signal(list)
    regex_preview_ready = Signal(list)
    regex_execute_ready = Signal(list, int, int)
    cancel_done = Signal()

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
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.source_dir: Path | None = None
        self.source_dirs: list[Path] = []
        self.target_dir: Path | None = None
        self.files: list[FileInfo] = []
        self.organizer = organizer or FileOrganizer()
        self.scanner = scanner or FileScanner()
        self.state = app_state
        self.event_bus = event_bus

        self._regex_undo: list[dict] = []
        self._last_preview_operations: list[dict] = []
        self._last_precheck: dict | None = None
        self._pool = QThreadPool.globalInstance()

        self._setup_ui()
        self._connect_signals()

    def update_services(
        self,
        scanner: FileScanner | None = None,
        organizer: FileOrganizer | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
    ):
        """Update service references without recreating the panel"""
        if scanner is not None:
            self.scanner = scanner
        if organizer is not None:
            self.organizer = organizer
        if app_state is not None:
            self.state = app_state
        if event_bus is not None:
            self.event_bus = event_bus

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._create_title_section(layout)
        self._create_pipeline_section(layout)
        self._create_folder_selection(layout)
        self._create_organize_rules(layout)
        self._create_rename_settings(layout)
        self._create_safety_section(layout)
        self._create_regex_rename(layout)
        self._create_action_buttons(layout)
        self._create_progress_bar(layout)
        self._create_results_table(layout)
        self._create_status_bar(layout)

    def _create_title_section(self, layout):
        title = QLabel(t("organize_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        desc = QLabel(
            "Select source and target folders, configure rules, and organize files.\n"
            "Supports auto-classification by type, date, extension, size, and smart renaming.",
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

    def _create_pipeline_section(self, layout):
        pipeline_group = QGroupBox("Workflow")
        pipeline_layout = QVBoxLayout()
        self.pipeline_label = QLabel("")
        self.pipeline_label.setObjectName("workflowPipeline")
        self.pipeline_label.setWordWrap(True)
        self.pipeline_label.setStyleSheet(
            "QLabel#workflowPipeline { color: #666; font-size: 12px; "
            "background: rgba(255,255,255,0.03); padding: 8px; border-radius: 4px; }"
        )
        self.history_label = QLabel("Recent organize history: no local runs yet")
        self.history_label.setObjectName("organizeHistory")
        self.history_label.setWordWrap(True)
        pipeline_layout.addWidget(self.pipeline_label)
        pipeline_layout.addWidget(self.history_label)
        pipeline_group.setLayout(pipeline_layout)
        layout.addWidget(pipeline_group)
        self._set_stage("select")
        self._refresh_history_summary()

    def _create_folder_selection(self, layout):
        dir_group = QGroupBox("Folders")
        dir_layout = QVBoxLayout()
        dir_layout.setSpacing(8)
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel(t("organize_src")))
        self.src_path_label = QLabel(t("organize_src_placeholder"))
        self.src_path_label.setObjectName("pathLabel")
        self.src_path_label.setWordWrap(True)
        self.btn_src = QPushButton(t("browse"))
        self.btn_src.clicked.connect(self._on_select_source)
        self.btn_add_src = QPushButton("Add Source")
        self.btn_add_src.clicked.connect(self._on_add_source)
        src_layout.addWidget(self.src_path_label, 1)
        src_layout.addWidget(self.btn_src)
        src_layout.addWidget(self.btn_add_src)
        dir_layout.addLayout(src_layout)
        dst_layout = QHBoxLayout()
        dst_layout.addWidget(QLabel(t("organize_dst")))
        self.dst_path_label = QLabel(t("organize_dst_placeholder"))
        self.dst_path_label.setObjectName("pathLabel")
        self.dst_path_label.setWordWrap(True)
        self.btn_dst = QPushButton(t("browse"))
        self.btn_dst.clicked.connect(self._on_select_target)
        dst_layout.addWidget(self.dst_path_label, 1)
        dst_layout.addWidget(self.btn_dst)
        dir_layout.addLayout(dst_layout)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

    def _create_organize_rules(self, layout):
        rule_group = QGroupBox("Organize Rules")
        rule_layout = QHBoxLayout()
        rule_layout.setSpacing(16)
        self.cb_category = QCheckBox("\U0001f4c2 By File Type")
        self.cb_category.setChecked(True)
        self.cb_date = QCheckBox("\U0001f4c5 By Date (Year/Month)")
        self.cb_extension = QCheckBox("\U0001f4ce By Extension")
        self.cb_size = QCheckBox("\U0001f4cf By File Size")
        self.cb_review_unknown = QCheckBox("Route unknown files to Review")
        self.cb_review_unknown.setChecked(True)
        rule_layout.addWidget(self.cb_category)
        rule_layout.addWidget(self.cb_date)
        rule_layout.addWidget(self.cb_extension)
        rule_layout.addWidget(self.cb_size)
        rule_layout.addWidget(self.cb_review_unknown)
        rule_layout.addStretch()
        rule_group.setLayout(rule_layout)
        layout.addWidget(rule_group)

    def _create_safety_section(self, layout):
        safety_group = QGroupBox("Safety Precheck")
        safety_layout = QVBoxLayout()
        self.precheck_label = QLabel("Generate a preview to run the safety precheck.")
        self.precheck_label.setObjectName("safetyPrecheck")
        self.precheck_label.setWordWrap(True)
        self.precheck_label.setStyleSheet(
            "QLabel#safetyPrecheck { color: #666; font-size: 12px; "
            "background: rgba(255,255,255,0.03); padding: 8px; border-radius: 4px; }"
        )
        safety_layout.addWidget(self.precheck_label)
        safety_group.setLayout(safety_layout)
        layout.addWidget(safety_group)

    def _create_rename_settings(self, layout):
        rename_layout = QHBoxLayout()
        rename_layout.addWidget(QLabel("\u270f\ufe0f Rename Template:"))
        self.rename_input = QLineEdit()
        self.rename_input.setPlaceholderText(
            "Leave empty for no rename. Supports: {name} {date} {time} {ext} {category}"
        )
        rename_layout.addWidget(self.rename_input, 1)
        self.template_btn = QPushButton(t("template_help"))
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

    def _create_regex_rename(self, layout):
        regex_group = QGroupBox("\U0001f504 Batch Regex Rename")
        regex_layout = QVBoxLayout()
        regex_layout.setSpacing(8)
        regex_pattern_layout = QHBoxLayout()
        regex_pattern_layout.addWidget(QLabel("Pattern:"))
        self.regex_pattern_input = QLineEdit()
        self.regex_pattern_input.setPlaceholderText(r"e.g., ^(\d{4})-(\d{2})-(\d{2})_")
        self.regex_pattern_input.textChanged.connect(self._on_regex_live_preview)
        regex_pattern_layout.addWidget(self.regex_pattern_input, 1)
        regex_layout.addLayout(regex_pattern_layout)
        regex_replacement_layout = QHBoxLayout()
        regex_replacement_layout.addWidget(QLabel("Replace:"))
        self.regex_replacement_input = QLineEdit()
        self.regex_replacement_input.setPlaceholderText(r"e.g., \2/\3/\1_")
        self.regex_replacement_input.textChanged.connect(self._on_regex_live_preview)
        regex_replacement_layout.addWidget(self.regex_replacement_input, 1)
        regex_layout.addLayout(regex_replacement_layout)

        # Live preview area
        self.regex_live_label = QLabel("")
        self.regex_live_label.setObjectName("regexLivePreview")
        self.regex_live_label.setWordWrap(True)
        self.regex_live_label.setStyleSheet(
            "QLabel#regexLivePreview { color: #888; font-size: 11px;"
            " background: rgba(255,255,255,0.03); padding: 6px; border-radius: 4px; }"
        )
        regex_layout.addWidget(self.regex_live_label)

        regex_options_layout = QHBoxLayout()
        self.regex_case_cb = QCheckBox(t("case_insensitive"))
        self.regex_case_cb.stateChanged.connect(self._on_regex_live_preview)
        self.regex_preview_btn = QPushButton(t("regex_preview"))
        self.regex_preview_btn.clicked.connect(self._on_regex_preview)
        self.regex_execute_btn = QPushButton(t("regex_execute"))
        self.regex_execute_btn.setObjectName("btnSuccess")
        self.regex_execute_btn.clicked.connect(self._on_regex_execute)
        self.regex_execute_btn.setEnabled(False)
        self.regex_undo_btn = QPushButton("\u21a9\ufe0f Undo Rename")
        self.regex_undo_btn.clicked.connect(self._on_regex_undo)
        self.regex_undo_btn.setEnabled(False)
        regex_options_layout.addWidget(self.regex_case_cb)
        regex_options_layout.addStretch()
        regex_options_layout.addWidget(self.regex_preview_btn)
        regex_options_layout.addWidget(self.regex_execute_btn)
        regex_options_layout.addWidget(self.regex_undo_btn)
        regex_layout.addLayout(regex_options_layout)
        regex_group.setLayout(regex_layout)
        layout.addWidget(regex_group)

    def _create_action_buttons(self, layout):
        action_layout = QHBoxLayout()
        self.btn_preview = QPushButton(t("organize_preview"))
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_preview.setEnabled(False)
        self.btn_execute = QPushButton(t("organize_execute"))
        self.btn_execute.setObjectName("btnSuccess")
        self.btn_execute.clicked.connect(self._on_execute)
        self.btn_execute.setEnabled(False)
        self.btn_clear = QPushButton(t("clear_results"))
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

    def _create_progress_bar(self, layout):
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

    def _create_results_table(self, layout):
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(
            [
                t("src_path_header"),
                t("dst_path_header"),
                t("category_header"),
                "Size",
                t("status_header"),
                "Target Slot",
            ]
        )
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        layout.addWidget(self.result_table, 1)

    def _create_status_bar(self, layout):
        self.stats_label = QLabel("Select a source folder to start preview")
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)
        self.preview_ready.connect(self._display_preview)
        self.execute_ready.connect(self._display_execution)
        self.regex_preview_ready.connect(self._display_regex_preview)
        self.regex_execute_ready.connect(self._display_regex_execution)
        self.cancel_done.connect(self._on_cancel_done)

    # ── Directory Selection ──

    def _source_roots(self) -> list[Path]:
        if self.source_dirs:
            return list(self.source_dirs)
        return [self.source_dir] if self.source_dir else []

    def _set_source_roots(self, roots: list[Path]) -> None:
        deduped: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root.resolve())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(root)
        self.source_dirs = deduped
        self.source_dir = deduped[0] if deduped else None
        self._refresh_source_label()

    def _refresh_source_label(self) -> None:
        roots = self._source_roots()
        if not roots:
            self.src_path_label.setText(t("organize_src_placeholder"))
        elif len(roots) == 1:
            self.src_path_label.setText(f"\U0001f4c2 {roots[0]}")
        else:
            self.src_path_label.setText(
                f"\U0001f4c2 {len(roots)} sources: {roots[0]} (+{len(roots) - 1})"
            )

    def _target_root(self) -> Path:
        if self.target_dir:
            return self.target_dir
        if self.source_dir:
            return self.source_dir / "_organized"
        return Path()

    def _ensure_default_target(self) -> None:
        if self.target_dir or not self.source_dir:
            return
        default_target = self.source_dir / "_organized"
        self.target_dir = default_target
        self.dst_path_label.setText(f"\U0001f3af {default_target}")
        self.dst_path_label.setProperty("selected", True)
        self.dst_path_label.style().unpolish(self.dst_path_label)
        self.dst_path_label.style().polish(self.dst_path_label)

    @Slot()
    def _on_select_source(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if dir_path:
            self._set_source_roots([Path(dir_path)])
            self.src_path_label.setProperty("selected", True)
            self.src_path_label.style().unpolish(self.src_path_label)
            self.src_path_label.style().polish(self.src_path_label)

            self._ensure_default_target()

            self.btn_preview.setEnabled(True)
            self._set_stage("select")

    @Slot()
    def _on_add_source(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Add Source Folder")
        if dir_path:
            self._set_source_roots([*self._source_roots(), Path(dir_path)])
            self.src_path_label.setProperty("selected", True)
            self.src_path_label.style().unpolish(self.src_path_label)
            self.src_path_label.style().polish(self.src_path_label)
            self._ensure_default_target()
            self.btn_preview.setEnabled(True)
            self._set_stage("select")

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
            self._set_stage("select")

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
        source_roots = self._source_roots()
        if not source_roots:
            self.status_message.emit("\u26a0\ufe0f Please select a source folder first")
            return
        target_root = self._target_root()

        self._cancelled = False
        self._cancelling = False
        self.btn_preview.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_table.setRowCount(0)
        self._last_preview_operations = []
        self._last_precheck = None
        self._set_stage("scan")
        self.status_message.emit(f"Scanning files from {len(source_roots)} source(s)...")

        def preview_worker():
            files = []
            for source_root in source_roots:
                for f in self.scanner.scan(
                    str(source_root),
                    progress_callback=lambda i, p: self.progress_updated.emit((i % 100) + 1),
                ):
                    if self._cancelled:
                        self.cancel_done.emit()
                        return
                    files.append(f)

            if self._cancelled:
                return

            rules = self._get_selected_rules()
            rename = bool(self.rename_input.text().strip())
            pattern = self.rename_input.text().strip()

            operations = self.organizer.organize(
                files,
                target_root=str(target_root),
                rules=rules,
                dry_run=True,
                rename=rename,
                rename_pattern=pattern or None,
                review_unknown=self.cb_review_unknown.isChecked(),
            )

            self.preview_ready.emit(operations, files)

        worker = Worker(preview_worker)
        worker.signals.finished.connect(lambda _: None)
        self._pool.start(worker)

    @Slot()
    def _display_preview(self, operations: list[dict], files: list | None = None):
        """Display preview results"""
        if files is not None:
            self.files = files
        self._last_preview_operations = list(operations)
        self._last_precheck = self._run_precheck(operations)
        self.result_table.setSortingEnabled(False)
        self.result_table.setRowCount(len(operations))

        for row, op in enumerate(operations):
            self.result_table.setItem(row, 0, QTableWidgetItem(op["source"]))
            self.result_table.setItem(row, 1, QTableWidgetItem(op["destination"]))
            self.result_table.setItem(row, 2, QTableWidgetItem(op["category"]))
            self.result_table.setItem(row, 3, QTableWidgetItem(op["size"]))

            risk = op.get("precheck_status", "")
            status = QTableWidgetItem(risk or "\U0001f4cb Preview")
            status.setTextAlignment(Qt.AlignCenter)
            status.setForeground(Qt.red if risk else Qt.gray)
            self.result_table.setItem(row, 4, status)
            self.result_table.setItem(row, 5, QTableWidgetItem(self._target_slot_text(op)))

        self.result_table.setSortingEnabled(True)
        self.btn_preview.setEnabled(True)
        self.btn_execute.setEnabled(len(operations) > 0 and self._last_precheck["safe_to_execute"])
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._display_precheck(self._last_precheck)
        self._set_stage("precheck" if self._last_precheck["safe_to_execute"] else "blocked")

        target_root = self._target_root()
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
        if not self._source_roots() or not self.files:
            return
        target_root = self._target_root()

        from PySide6.QtWidgets import QMessageBox

        precheck = self._run_precheck(self._last_preview_operations)
        self._last_precheck = precheck
        self._display_precheck(precheck)
        if not precheck["safe_to_execute"]:
            self._set_stage("blocked")
            QMessageBox.warning(
                self,
                "Safety precheck blocked execution",
                "Resolve the listed precheck issue(s), then preview again before executing.",
            )
            return

        reply = QMessageBox.question(
            self,
            t("organize_confirm"),
            f"Organize {len(self.files)} files into\n"
            f"{target_root}?\n\n"
            f"{precheck['summary']}\n\n"
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
        self._set_stage("execute")
        self.status_message.emit("Organizing files...")

        def execute_worker():
            rules = self._get_selected_rules()
            rename = bool(self.rename_input.text().strip())
            pattern = self.rename_input.text().strip()

            if self._cancelled:
                self.cancel_done.emit()
                return

            operations = self.organizer.organize(
                self.files,
                target_root=str(target_root),
                rules=rules,
                dry_run=False,
                rename=rename,
                rename_pattern=pattern or None,
                review_unknown=self.cb_review_unknown.isChecked(),
                progress_callback=lambda i, name: self.progress_updated.emit(
                    int(i / len(self.files) * 100) if self.files else 0,
                ),
            )

            if not self._cancelled:
                self.execute_ready.emit(operations)

        worker = Worker(execute_worker)
        worker.signals.finished.connect(lambda _: None)
        self._pool.start(worker)

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
            self.result_table.setItem(row, 5, QTableWidgetItem(self._target_slot_text(op)))

        self.result_table.setSortingEnabled(True)
        self.btn_execute.setEnabled(False)
        self.btn_preview.setEnabled(True)
        self.btn_undo.setEnabled(done > 0)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._set_stage("done")

        # Save undo log
        if done > 0:
            undo_path = Path.home() / ".filepilot" / "last_undo.json"
            undo_path.parent.mkdir(parents=True, exist_ok=True)
            self.organizer.save_undo_log(undo_path)
            self._record_history(operations, undo_path)
            self._refresh_history_summary()

        stats = self.organizer.stats
        self.stats_label.setText(
            f"\u2705 {t('organize_done')}: {stats['organized_count']} files moved"
            + (f", {stats['errors']} errors" if stats["errors"] else ""),
        )

    @Slot()
    def _on_undo(self):
        """Undo last organize operation"""
        from PySide6.QtWidgets import QMessageBox

        undo_path = Path.home() / ".filepilot" / "last_undo.json"
        if not undo_path.exists():
            QMessageBox.warning(self, t("undo_failed"), t("no_undo_log"))
            return

        reply = QMessageBox.question(
            self,
            t("confirm_undo_title"),
            "Undo the last organize operation?"
            " Files will be moved back to their original locations.",
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
        self._set_stage("select")
        self._refresh_history_summary()

    @Slot()
    def _clear_results(self):
        """Clear results"""
        self.result_table.setRowCount(0)
        self.btn_execute.setEnabled(False)
        self._last_preview_operations = []
        self._last_precheck = None
        self.precheck_label.setText("Generate a preview to run the safety precheck.")
        self._set_stage("select")
        self.stats_label.setText(t("ready"))

    def _set_stage(self, stage: str) -> None:
        stages = [
            ("select", "Select"),
            ("scan", "Scan"),
            ("precheck", "Precheck"),
            ("execute", "Execute"),
            ("done", "Done"),
        ]
        if stage == "blocked":
            self.pipeline_label.setText(
                "Select -> Scan -> Precheck -> Execute -> Done\n"
                "Blocked: review the safety precheck."
            )
            return

        parts = []
        passed = True
        for key, name in stages:
            if key == stage:
                parts.append(f"[{name}]")
                passed = False
            elif passed:
                parts.append(f"✓ {name}")
            else:
                parts.append(name)
        self.pipeline_label.setText(" -> ".join(parts))

    def _run_precheck(self, operations: list[dict]) -> dict:
        destination_counts: dict[str, int] = {}
        blockers: list[str] = []
        warnings: list[str] = []
        target_slots = self._target_slot_summary(operations)
        review_count = 0
        cross_drive_count = 0
        missing_count = 0
        existing_count = 0

        for op in operations:
            destination_key = str(Path(op["destination"]).resolve())
            destination_counts[destination_key] = destination_counts.get(destination_key, 0) + 1

        duplicates = {path for path, count in destination_counts.items() if count > 1}

        for op in operations:
            source = Path(op["source"])
            destination = Path(op["destination"])
            status: list[str] = []

            if source.is_absolute() and not source.exists():
                missing_count += 1
                status.append("missing source")
            if destination.exists():
                existing_count += 1
                status.append("target exists")
            if str(destination.resolve()) in duplicates:
                status.append("duplicate target")
            if (
                destination.drive
                and source.drive
                and destination.drive.lower() != source.drive.lower()
            ):
                cross_drive_count += 1
                status.append("cross-drive")
            if any(part.lower() == "review" for part in destination.parts):
                review_count += 1
                status.append("review")

            if status:
                op["precheck_status"] = ", ".join(status)
            else:
                op.pop("precheck_status", None)

        if missing_count:
            blockers.append(f"{missing_count} source file(s) are missing.")
        if existing_count:
            blockers.append(f"{existing_count} target path(s) already exist.")
        if duplicates:
            blockers.append(f"{len(duplicates)} duplicate target path(s) were found.")
        if cross_drive_count:
            warnings.append(f"{cross_drive_count} file(s) will move across drives.")
        if review_count:
            warnings.append(f"{review_count} unknown file(s) are routed to Review.")

        safe_to_execute = bool(operations) and not blockers
        summary = (
            f"Precheck {'passed' if safe_to_execute else 'needs attention'}: "
            f"{len(operations)} planned move(s), {len(blockers)} blocker(s), "
            f"{len(warnings)} warning(s)."
        )
        return {
            "safe_to_execute": safe_to_execute,
            "summary": summary,
            "blockers": blockers,
            "warnings": warnings,
            "review_count": review_count,
            "missing_count": missing_count,
            "existing_count": existing_count,
            "cross_drive_count": cross_drive_count,
            "duplicate_target_count": len(duplicates),
            "target_slots": target_slots,
            "target_slot_count": len(target_slots),
        }

    def _display_precheck(self, precheck: dict) -> None:
        lines = [precheck["summary"]]
        target_slots = list(precheck.get("target_slots") or [])
        if target_slots:
            slot_bits = [
                f"{slot['slot_id']} -> {slot['target_subdir']} ({slot['operation_count']})"
                for slot in target_slots[:5]
            ]
            if len(target_slots) > 5:
                slot_bits.append(f"+{len(target_slots) - 5} more")
            lines.append("Targets: " + ", ".join(slot_bits))
        lines.extend(f"Blocker: {item}" for item in precheck["blockers"])
        lines.extend(f"Warning: {item}" for item in precheck["warnings"])
        if precheck["safe_to_execute"] and not precheck["warnings"]:
            lines.append("Ready to execute after user confirmation.")
        self.precheck_label.setText("\n".join(lines))

    def _target_slot_summary(self, operations: list[dict]) -> list[dict]:
        slots: dict[str, dict] = {}
        for operation in operations:
            slot_id = str(operation.get("target_slot") or "").strip()
            if not slot_id:
                continue
            slot = slots.setdefault(
                slot_id,
                {
                    "slot_id": slot_id,
                    "target_dir": str(operation.get("target_dir") or ""),
                    "target_subdir": str(operation.get("target_subdir") or "."),
                    "operation_count": 0,
                },
            )
            slot["operation_count"] += 1
        return sorted(slots.values(), key=lambda item: item["slot_id"])

    def _target_slot_text(self, operation: dict) -> str:
        slot = str(operation.get("target_slot") or "").strip()
        target_subdir = str(operation.get("target_subdir") or "").strip()
        if slot and target_subdir and target_subdir != ".":
            return f"{slot} -> {target_subdir}"
        return slot

    def _history_path(self) -> Path:
        return Path.home() / ".filepilot" / "organize-history.jsonl"

    def _record_history(self, operations: list[dict], undo_path: Path) -> None:
        moved_count = sum(1 for op in operations if not op.get("dry_run", False))
        record = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_dir": str(self.source_dir) if self.source_dir else None,
            "source_dirs": [str(root) for root in self._source_roots()],
            "target_dir": str(self._target_root()) if self._source_roots() else None,
            "moved_count": moved_count,
            "error_count": self.organizer.stats.get("errors", 0),
            "review_count": self._last_precheck.get("review_count", 0)
            if self._last_precheck
            else 0,
            "target_slots": self._target_slot_summary(operations),
            "undo_log": str(undo_path),
        }
        history_path = self._history_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _refresh_history_summary(self) -> None:
        history_path = self._history_path()
        if not history_path.exists():
            self.history_label.setText("Recent organize history: no local runs yet")
            return
        try:
            lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line]
            if not lines:
                self.history_label.setText("Recent organize history: no local runs yet")
                return
            record = json.loads(lines[-1])
        except (OSError, json.JSONDecodeError):
            self.history_label.setText("Recent organize history: unavailable")
            return
        self.history_label.setText(
            "Recent organize history: "
            f"{record.get('moved_count', 0)} moved, "
            f"{record.get('error_count', 0)} errors, "
            f"{record.get('review_count', 0)} review item(s), "
            f"{len(record.get('target_slots', []))} target slot(s)"
        )

    # ── Batch Regex Rename ──

    @Slot()
    def _on_regex_live_preview(self):
        """Update live preview as user types regex pattern/replacement."""
        pattern = self.regex_pattern_input.text().strip()
        replacement = self.regex_replacement_input.text()

        if not pattern:
            self.regex_live_label.setText("")
            return

        try:
            flags = re.IGNORECASE if self.regex_case_cb.isChecked() else 0
            compiled = re.compile(pattern, flags)
        except re.error as e:
            self.regex_live_label.setText(f"<span style='color:#ef5350;'>Invalid regex: {e}</span>")
            return

        # Show preview on first 5 scanned files that match
        if not self.files:
            self.regex_live_label.setText(
                "<span style='color:#888;'>Scan files first to see live preview</span>"
            )
            return

        previews = []
        for f in self.files[:50]:  # Check first 50 files
            new_name = compiled.sub(replacement, f.name)
            if new_name != f.name:
                previews.append(f"  {f.name} -> <b>{new_name}</b>")
            if len(previews) >= 5:
                break

        if not previews:
            self.regex_live_label.setText(
                "<span style='color:#888;'>No files match this pattern</span>"
            )
        else:
            count_text = f"<b>{len(previews)}</b> matches (showing first {len(previews)}):"
            self.regex_live_label.setText(count_text + "<br>" + "<br>".join(previews))

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

        source_roots = self._source_roots()
        if not source_roots:
            self.status_message.emit("\u26a0\ufe0f Please select a source folder first")
            return

        self._regex_undo.clear()
        self.regex_undo_btn.setEnabled(False)
        self._cancelled = False
        self._cancelling = False
        self.progress_bar.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.emit("Scanning files for regex preview...")

        def regex_preview_worker():
            files = []
            for source_root in source_roots:
                for f in self.scanner.scan(
                    str(source_root),
                    progress_callback=lambda i, p: self.progress_updated.emit((i % 100) + 1),
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

            self.regex_preview_ready.emit(operations)

        worker = Worker(regex_preview_worker)
        worker.signals.finished.connect(lambda _: None)
        self._pool.start(worker)

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
            self.result_table.setItem(row, 5, QTableWidgetItem(""))

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

        def regex_execute_worker():
            replacement = self.regex_replacement_input.text()
            operations = []
            success_count = 0
            error_count = 0
            undo_ops = []

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
                        undo_ops.append({"source": str(f.path), "destination": str(new_path)})
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

                self.progress_updated.emit(
                    int((i + 1) / len(self.files) * 100) if self.files else 0
                )

            self._regex_undo = undo_ops
            self.regex_execute_ready.emit(operations, success_count, error_count)

        worker = Worker(regex_execute_worker)
        worker.signals.finished.connect(lambda _: None)
        self._pool.start(worker)

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
            self.result_table.setItem(row, 5, QTableWidgetItem(""))

        self.result_table.setSortingEnabled(True)
        self.btn_preview.setEnabled(True)
        self.regex_preview_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)

        self.regex_undo_btn.setEnabled(success_count > 0)
        self.stats_label.setText(
            f"\u2705 Regex rename complete: {success_count} renamed"
            + (f", {error_count} errors" if error_count else "")
        )

    @Slot()
    def _on_regex_undo(self):
        """Undo the last regex rename operation."""
        if not self._regex_undo:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Undo Rename",
            f"Undo the last regex rename? {len(self._regex_undo)} file(s) will be renamed back.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        restored = 0
        errors = 0
        for op in reversed(self._regex_undo):
            src = Path(op["source"])
            dst = Path(op["destination"])
            try:
                if dst.exists():
                    dst.rename(src)
                    restored += 1
            except Exception as e:
                errors += 1
                self.status_message.emit(f"\u274c Undo error: {e}")
        self._regex_undo.clear()
        self.regex_undo_btn.setEnabled(False)
        self.stats_label.setText(
            f"\u21a9\ufe0f Undo complete: {restored} restored"
            + (f", {errors} errors" if errors else "")
        )
