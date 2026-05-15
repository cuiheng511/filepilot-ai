"""AI summary generation panel"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from filepilot.ui.base_panel import BasePanel
from filepilot.utils.file_utils import CAT_CODE, CAT_MARKDOWN, CAT_OFFICE, CAT_PDF, CAT_TEXT

SUPPORTED_EXTS = CAT_CODE | CAT_PDF | CAT_MARKDOWN | CAT_TEXT | CAT_OFFICE
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"}


class SummaryPanel(BasePanel):
    """AI summary generation panel — extracts summaries and keywords from files"""

    summary_ready = Signal(str)
    keyword_ready = Signal(str)
    _add_file_requested = Signal(str, str, str)  # name, suffix, path_str

    def __init__(self, summarizer=None, local_ai=None, cloud_ai=None, parent=None):
        super().__init__(parent)
        self._summarizer = summarizer
        self._local_ai = local_ai
        self._cloud_ai = cloud_ai
        self._lazy_init_done = False

        self.selected_files: list[Path] = []
        self.current_dir: Path | None = None

        self._setup_ui()
        self._connect_signals()
        self._add_file_requested.connect(self._add_file_item)

    def update_services(self, summarizer=None, local_ai=None, cloud_ai=None):
        """Update service references without recreating the panel"""
        if summarizer is not None:
            self._summarizer = summarizer
        if local_ai is not None:
            self._local_ai = local_ai
        if cloud_ai is not None:
            self._cloud_ai = cloud_ai
        self._lazy_init_done = False

    def _ensure_ai_init(self):
        """Lazy initialization of AI engines (imported late to avoid circular imports)"""
        if self._lazy_init_done:
            return
        self._lazy_init_done = True

        if self._summarizer is None:
            from filepilot.ai.summarizer import Summarizer

            self._summarizer = Summarizer()

        if self._local_ai is None:
            from filepilot.ai.local_ai import LocalAI

            self._local_ai = LocalAI()

        if self._cloud_ai is None:
            from filepilot.ai.cloud_ai import CloudAI

            self._cloud_ai = CloudAI()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── Title ──
        title = QLabel("📝 AI Summary Generation")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Extract summaries and keywords from PDF, Markdown, and code files. "
            "Supports both local (Ollama) and cloud (OpenAI) AI engines.",
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── File selection area ──
        file_sel_layout = QHBoxLayout()

        # Left: file list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("📂 Selected Files:"))

        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        left_layout.addWidget(self.file_list, 1)

        btn_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("➕ Add Files")
        self.btn_add_files.clicked.connect(self._on_add_files)
        self.btn_add_folder = QPushButton("📁 Add Folder")
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        self.btn_clear_files = QPushButton("Clear")
        self.btn_clear_files.clicked.connect(self.file_list.clear)
        btn_layout.addWidget(self.btn_add_files)
        btn_layout.addWidget(self.btn_add_folder)
        btn_layout.addWidget(self.btn_clear_files)
        left_layout.addLayout(btn_layout)

        # Right: AI settings & actions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("🤖 AI Settings:"))

        self.ai_status_label = QLabel("AI status: checking...")
        self.ai_status_label.setObjectName("aiStatusLabel")
        self.ai_status_label.setWordWrap(True)
        right_layout.addWidget(self.ai_status_label)

        self.cb_local_first = QCheckBox("Prefer local AI (Ollama)")
        self.cb_local_first.setChecked(True)
        right_layout.addWidget(self.cb_local_first)

        self.cb_include_code = QCheckBox("Include code snippets in summary")
        self.cb_include_code.setChecked(True)
        right_layout.addWidget(self.cb_include_code)

        self.cb_ocr_images = QCheckBox("Extract text from images (OCR)")
        self.cb_ocr_images.setChecked(True)
        self.cb_ocr_images.setToolTip("Use Tesseract OCR to extract text from image files")
        right_layout.addWidget(self.cb_ocr_images)

        right_layout.addStretch()

        self.btn_generate = QPushButton("🚀 Generate Summary")
        self.btn_generate.setObjectName("btnSuccess")
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_generate.setEnabled(False)
        right_layout.addWidget(self.btn_generate)

        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        right_layout.addWidget(self.btn_cancel)

        file_sel_layout.addWidget(left_panel, 3)
        file_sel_layout.addWidget(right_panel, 2)
        layout.addLayout(file_sel_layout, 1)

        # ── Progress bar ──
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar, 1)
        layout.addLayout(progress_layout)

        # ── Results splitter ──
        result_splitter = QSplitter(Qt.Vertical)

        # Summary area
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 8, 0, 0)
        summary_layout.addWidget(QLabel("📋 Summary:"))
        self.summary_output = QTextEdit()
        self.summary_output.setReadOnly(True)
        self.summary_output.setPlaceholderText('Click "Generate Summary" to start...')
        summary_layout.addWidget(self.summary_output, 1)
        result_splitter.addWidget(summary_widget)

        # Keywords area
        keyword_widget = QWidget()
        keyword_layout = QVBoxLayout(keyword_widget)
        keyword_layout.setContentsMargins(0, 8, 0, 0)
        keyword_layout.addWidget(QLabel("🔑 Keywords:"))
        self.keyword_output = QTextEdit()
        self.keyword_output.setReadOnly(True)
        self.keyword_output.setPlaceholderText("Keywords will appear here...")
        keyword_layout.addWidget(self.keyword_output, 1)
        result_splitter.addWidget(keyword_widget)

        result_splitter.setStretchFactor(0, 3)
        result_splitter.setStretchFactor(1, 1)
        layout.addWidget(result_splitter, 2)

        # ── Status bar ──
        self.stats_label = QLabel('Add files and click "Generate Summary"')
        self.stats_label.setObjectName("statusLabel")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.status_message.connect(self.stats_label.setText)
        self.summary_ready.connect(self.summary_output.setPlainText)
        self.keyword_ready.connect(self.keyword_output.setPlainText)

    def _is_supported(self, path: Path) -> bool:
        """Check if the file extension is supported"""
        return path.suffix.lower() in SUPPORTED_EXTS

    # ── File selection ──

    @Slot()
    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files for summarization",
            str(self.current_dir or str(Path.home())),
            "Supported files (*.pdf *.md *.txt *.py *.js *.ts *.java *.cpp *.c *.h *.go *.rs *.rb *.php *.swift *.kt *.png *.jpg *.jpeg *.tiff *.bmp *.gif *.webp);;All files (*.*)",
        )
        for fp in files:
            path = Path(fp)
            is_text = path.suffix.lower() in SUPPORTED_EXTS
            is_image = path.suffix.lower() in IMAGE_EXTS
            if not is_text and not is_image:
                continue
            if is_image and not self.cb_ocr_images.isChecked():
                continue
            existing = [
                self.file_list.item(i).data(Qt.UserRole) for i in range(self.file_list.count())
            ]
            if str(path) not in existing:
                label = f"{path.name} ({path.suffix})"
                if is_image:
                    label = f"🖼️ {path.name} ({path.suffix})"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, str(path))
                item.setToolTip(str(path))
                self.file_list.addItem(item)

        self.btn_generate.setEnabled(self.file_list.count() > 0)

    @Slot()
    def _on_add_folder(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select folder to scan",
            str(self.current_dir or Path.home()),
        )
        if not dir_path:
            return

        self.current_dir = Path(dir_path)
        self.status_message.emit(f"Scanning folder: {dir_path}")

        existing = [self.file_list.item(i).data(Qt.UserRole) for i in range(self.file_list.count())]

        def scan_worker():
            from filepilot.core.file_scanner import FileScanner

            scanner = FileScanner()
            count = 0
            for f in scanner.scan(dir_path):
                path = Path(f.path)
                if not self._is_supported(path):
                    continue
                if str(path) in existing:
                    continue
                # Thread-safe UI update via signal
                self._add_file_requested.emit(path.name, path.suffix, str(path))
                count += 1
            if count > 0:
                self.status_message.emit(f"✅ Added {count} supported files")
            else:
                self.status_message.emit("No supported files found in the selected folder")

        Thread(target=scan_worker, daemon=True).start()

    @Slot()
    def _add_file_item(self, name: str, suffix: str, path_str: str):
        item = QListWidgetItem(f"{name} ({suffix})")
        item.setData(Qt.UserRole, path_str)
        item.setToolTip(path_str)
        self.file_list.addItem(item)
        self.btn_generate.setEnabled(self.file_list.count() > 0)

    # ── Generate summary ──

    @Slot()
    def _on_cancel(self):
        """Cancel current operation"""
        if self._cancelling:
            return
        self._cancelled = True
        self._cancelling = True
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        self.status_message.emit("⏹️ Operation cancelled")

    @Slot()
    def _on_generate(self):
        """Start summary generation"""
        if self.file_list.count() == 0:
            self.status_message.emit("⚠️ Please add files first")
            return

        self._ensure_ai_init()

        self._cancelled = False
        self._cancelling = False
        self.btn_generate.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.summary_output.clear()
        self.keyword_output.clear()
        self.status_message.emit("Generating summary, please wait...")

        files = []
        for i in range(self.file_list.count()):
            path_str = self.file_list.item(i).data(Qt.UserRole)
            if path_str:
                files.append(Path(path_str))

        prefer_local = self.cb_local_first.isChecked()

        def worker():
            # Read file contents
            contents = []
            total = len(files)
            use_ocr = self.cb_ocr_images.isChecked()

            for i, fp in enumerate(files):
                if self._cancelled:
                    return
                try:
                    if fp.suffix.lower() in IMAGE_EXTS and use_ocr:
                        from filepilot.extractors.ocr_extractor import OCRExtractor

                        ocr = OCRExtractor()
                        text = ocr.extract_text(fp) or "[OCR extracted no text]"
                    else:
                        text = fp.read_text(encoding="utf-8", errors="replace")
                    contents.append((fp.name, text))
                except Exception:
                    contents.append((fp.name, "[Error reading file]"))
                self.progress_updated.emit(int((i + 1) / total * 40))

            if self._cancelled:
                return

            # Generate summary
            combined_text = ""
            for name, text in contents:
                combined_text += f"\n\n# File: {name}\n{text[:2000]}"

            max_len = 8000
            if len(combined_text) > max_len:
                combined_text = combined_text[:max_len] + "\n\n[...content truncated...]"

            self.progress_updated.emit(45)

            summary = ""
            keywords_text = ""

            try:
                if prefer_local and self._local_ai:
                    summary = self._local_ai.generate(
                        f"Please generate a concise summary of the following content:\n\n{combined_text}",
                    )
                    self.progress_updated.emit(70)

                    keywords_text = self._local_ai.generate(
                        f"Extract 5-10 key keywords from the following content, separated by commas:\n\n{combined_text}",
                    )
                elif self._cloud_ai:
                    summary = self._cloud_ai.generate(
                        f"Please generate a concise summary of the following content:\n\n{combined_text}",
                    )
                    self.progress_updated.emit(70)

                    keywords_text = self._cloud_ai.generate(
                        f"Extract 5-10 key keywords from the following content, separated by commas:\n\n{combined_text}",
                    )
                else:
                    # Fallback: use summarizer
                    summary = "Summary: "
                    for name, text in contents:
                        s = self._summarizer.summarize_text(text, max_length=512)
                        if s:
                            summary += f"\n\n### {name}\n{s}"
                    self.progress_updated.emit(70)

                    keywords_text = "Keywords: "
                    kw_set = set()
                    for _name, text in contents:
                        kw = self._summarizer.extract_keywords(text, top_n=5)
                        kw_set.update(kw)
                    keywords_text += ", ".join(list(kw_set)[:15])
            except Exception as e:
                summary = f"[AI generation failed: {e}]"
                keywords_text = ""

            self.progress_updated.emit(90)

            if not self._cancelled:
                self.summary_ready.emit(summary or "No summary generated")
                self.keyword_ready.emit(keywords_text or "No keywords extracted")
                self.status_message.emit(f"✅ Summary complete — processed {len(files)} files")
                from PySide6.QtCore import QMetaObject, Qt

                QMetaObject.invokeMethod(self, "_on_summary_done", Qt.QueuedConnection)

        Thread(target=worker, daemon=True).start()

    @Slot()
    def _on_summary_done(self) -> None:
        """Restore UI after summary generation completes (main thread only)."""
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)
