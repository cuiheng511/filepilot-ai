"""AI 摘要生成面板 — 单文件 / 批量摘要、关键词提取"""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
)

from filepilot.ai.summarizer import Summarizer
from filepilot.ai.local_ai import LocalAI
from filepilot.ai.cloud_ai import CloudAI
from filepilot.ui.base_panel import BasePanel


class SummaryPanel(BasePanel):
    """AI 摘要生成面板"""

    # 支持的文件扩展名
    SUPPORTED_EXTS = {
        ".pdf", ".md", ".markdown", ".mdx",
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".java", ".cpp", ".c", ".h", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".php",
        ".swift", ".kt", ".scala", ".sql",
        ".sh", ".bash", ".ps1", ".lua",
        ".txt", ".rst",
    }

    def __init__(
        self,
        summarizer: Summarizer | None = None,
        local_ai: LocalAI | None = None,
        cloud_ai: CloudAI | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._files: list[Path] = []
        self._processing = False

        # 如果注入了服务，直接使用；否则惰性初始化
        self._local_ai = local_ai
        self._cloud_ai = cloud_ai
        self._summarizer = summarizer
        self._ai_initialized = (
            summarizer is not None
            and local_ai is not None
            and cloud_ai is not None
        )

        self._setup_ui()
        self._connect_signals()

    def _init_ai(self):
        """惰性初始化 AI 引擎（仅在未注入服务时使用）"""
        if self._summarizer is not None:
            self._update_ai_status()
            return

        from filepilot.app import load_settings
        settings = load_settings()
        ai_mode = settings.get("ai_mode", "local")

        self._local_ai = LocalAI(
            model=settings.get("ollama_model", "qwen2.5:7b"),
            api_base=settings.get("ollama_url", "http://localhost:11434"),
        )
        self._cloud_ai = CloudAI(
            api_key=settings.get("openai_key", ""),
            model=settings.get("openai_model", "gpt-4o-mini"),
            api_base=settings.get("openai_url", "https://api.openai.com/v1"),
        )
        self._summarizer = Summarizer(
            local_ai=self._local_ai,
            cloud_ai=self._cloud_ai,
            prefer_local=(ai_mode in ("local", "hybrid")),
        )
        self._update_ai_status()

    def _update_ai_status(self):
        """更新 AI 状态指示"""
        local_ok = self._local_ai and self._local_ai.is_available
        cloud_ok = self._cloud_ai and self._cloud_ai.is_available

        if local_ok and cloud_ok:
            status = "✅ Ollama + OpenAI 均可用"
        elif local_ok:
            status = "✅ Ollama 本地模型可用（推荐）"
        elif cloud_ok:
            status = "✅ OpenAI API 可用"
        else:
            status = "⚠️ 无可用的 AI 引擎，请在设置中配置"

        self.ai_status_label.setText(status)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ── 标题 ──
        title = QLabel("📝 AI 摘要生成")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel(
            "使用 AI 自动提取 PDF、Markdown、代码文件的摘要和关键词。\n"
            "支持单个文件和批量处理。需要配置 Ollama 或 OpenAI API。"
        )
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ── AI 状态指示 ──
        self.ai_status_label = QLabel("正在检测 AI 引擎...")
        self.ai_status_label.setStyleSheet(
            "color: #a6adc8; font-size: 12px; background: #181825; "
            "border: 1px solid #313244; border-radius: 6px; padding: 8px 12px;"
        )
        layout.addWidget(self.ai_status_label)

        # ── 文件选择 ──
        file_sel_layout = QHBoxLayout()
        file_sel_layout.addWidget(QLabel("📂 选择文件:"))

        self.file_path_label = QLabel("未选择")
        self.file_path_label.setStyleSheet(
            "color: #585b70; padding: 6px 10px; background: #181825; "
            "border: 1px solid #313244; border-radius: 4px;"
        )
        self.file_path_label.setWordWrap(True)

        self.btn_select_file = QPushButton("选择文件...")
        self.btn_select_file.clicked.connect(self._on_select_file)

        self.btn_select_folder = QPushButton("选择文件夹（批量）...")
        self.btn_select_folder.clicked.connect(self._on_select_folder)

        file_sel_layout.addWidget(self.file_path_label, 1)
        file_sel_layout.addWidget(self.btn_select_file)
        file_sel_layout.addWidget(self.btn_select_folder)
        layout.addLayout(file_sel_layout)

        # ── 批量文件列表 ──
        self.file_list = QListWidget()
        self.file_list.setVisible(False)
        self.file_list.setMaximumHeight(120)
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 6px;
                font-size: 12px;
            }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected { background-color: #313244; color: #cba6f7; }
        """)
        layout.addWidget(self.file_list)

        # ── 操作按钮 ──
        action_layout = QHBoxLayout()

        self.btn_summarize = QPushButton("🤖 生成摘要")
        self.btn_summarize.clicked.connect(self._on_summarize)
        self.btn_summarize.setEnabled(False)
        self.btn_summarize.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa; color: #1e1e2e;
                border: none; border-radius: 6px;
                padding: 10px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #74c7ec; }
            QPushButton:disabled { background-color: #313244; color: #585b70; }
        """)

        self.btn_batch = QPushButton("📦 批量处理")
        self.btn_batch.clicked.connect(self._on_batch_summarize)
        self.btn_batch.setEnabled(False)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_clear.setEnabled(False)

        action_layout.addWidget(self.btn_summarize)
        action_layout.addWidget(self.btn_batch)
        action_layout.addWidget(self.btn_clear)
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
        self.btn_cancel.clicked.connect(self._on_cancel_processing)
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

        # ── 分割器：内容预览 + 摘要结果 ──
        splitter = QSplitter(Qt.Vertical)

        # 上方：原始内容预览
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        content_label = QLabel("📄 原始内容")
        content_label.setStyleSheet("color: #a6adc8; font-size: 12px; font-weight: bold;")
        content_layout.addWidget(content_label)

        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setPlaceholderText("选择文件后将显示提取的文本内容...")
        self.content_preview.setStyleSheet("""
            QTextEdit {
                background-color: #181825; color: #cdd6f4;
                border: 1px solid #313244; border-radius: 8px;
                padding: 12px; font-size: 12px;
            }
        """)
        content_layout.addWidget(self.content_preview, 1)
        splitter.addWidget(content_widget)

        # 下方：摘要结果 + 关键词
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(4)

        result_header = QHBoxLayout()
        result_title = QLabel("🤖 AI 摘要")
        result_title.setStyleSheet("color: #a6adc8; font-size: 12px; font-weight: bold;")
        result_header.addWidget(result_title)
        result_header.addStretch()

        self.btn_copy = QPushButton("📋 复制摘要")
        self.btn_copy.clicked.connect(self._on_copy_summary)
        self.btn_copy.setEnabled(False)
        self.btn_copy.setStyleSheet(
            "QPushButton { padding: 4px 12px; font-size: 11px; }"
        )
        result_header.addWidget(self.btn_copy)
        result_layout.addLayout(result_header)

        self.summary_preview = QTextEdit()
        self.summary_preview.setReadOnly(True)
        self.summary_preview.setPlaceholderText("点击「生成摘要」查看结果...")
        self.summary_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e; color: #cdd6f4;
                border: 1px solid #45475a; border-radius: 8px;
                padding: 12px; font-size: 13px;
            }
        """)
        result_layout.addWidget(self.summary_preview, 1)

        # 关键词区域
        kw_layout = QHBoxLayout()
        kw_label = QLabel("🏷️ 关键词:")
        kw_label.setStyleSheet("color: #a6adc8; font-size: 12px; font-weight: bold;")
        kw_layout.addWidget(kw_label)

        self.keywords_widget = QWidget()
        self.keywords_widget.setStyleSheet("background: transparent;")
        self.keywords_layout = QHBoxLayout(self.keywords_widget)
        self.keywords_layout.setContentsMargins(0, 0, 0, 0)
        self.keywords_layout.setSpacing(6)
        kw_layout.addWidget(self.keywords_widget, 1)
        result_layout.addLayout(kw_layout)

        splitter.addWidget(result_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

        # ── 底部状态 ──
        self.stats_label = QLabel("选择 PDF、Markdown 或代码文件后生成 AI 摘要")
        self.stats_label.setStyleSheet(
            "color: #585b70; font-size: 12px; padding: 4px 0;"
        )
        layout.addWidget(self.stats_label)

    def _make_keyword_tag(self, word: str) -> QLabel:
        """创建一个关键词标签"""
        tag = QLabel(f"  {word}  ")
        tag.setStyleSheet("""
            QLabel {
                background-color: #313244; color: #cba6f7;
                border: 1px solid #45475a; border-radius: 12px;
                padding: 3px 6px; font-size: 11px;
            }
        """)
        return tag

    def _connect_signals(self):
        self.progress_updated.connect(self.progress_bar.setValue)
        self.progress_text.connect(self.progress_label.setText)
        self.status_message.connect(self.stats_label.setText)

    def showEvent(self, event):
        """面板可见时初始化 AI（仅首次，避免启动时阻塞）"""
        super().showEvent(event)
        if not self._ai_initialized:
            self._ai_initialized = True
            Thread(target=self._init_ai, daemon=True).start()

    # ── 文件选择 ──

    @Slot()
    def _on_select_file(self):
        """选择单个文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文件",
            str(Path.home()),
            "支持的文件 (*.pdf *.md *.txt *.py *.js *.ts *.java *.cpp *.c *.go *.rs);;"
            "所有文件 (*)",
        )
        if not file_path:
            return

        p = Path(file_path)
        self._files = [p]
        self._update_file_display()
        self._load_content_preview(p)
        self.btn_summarize.setEnabled(True)
        self.btn_batch.setEnabled(False)
        self.btn_clear.setEnabled(True)
        self.status_message.emit(f"已选择: {p.name}")

    @Slot()
    def _on_select_folder(self):
        """选择文件夹（批量处理）"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择文件夹（批量处理）", str(Path.home())
        )
        if not dir_path:
            return

        root = Path(dir_path)
        supported = []
        for f in root.rglob("*"):
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTS:
                supported.append(f)

        if not supported:
            self.status_message.emit("⚠️ 文件夹中没有找到支持的文件类型")
            return

        self._files = sorted(supported)
        self._update_file_display()
        self._show_batch_list()
        self.btn_summarize.setEnabled(False)  # 批量模式用 btn_batch
        self.btn_batch.setEnabled(len(self._files) > 0)
        self.btn_clear.setEnabled(True)
        self.status_message.emit(f"📦 找到 {len(self._files)} 个支持的文件")

    def _update_file_display(self):
        """更新文件路径显示"""
        if len(self._files) == 1:
            self.file_path_label.setText(f"📄 {self._files[0]}")
            self.file_path_label.setStyleSheet(
                "color: #cdd6f4; padding: 6px 10px; background: #181825; "
                "border: 1px solid #313244; border-radius: 4px;"
            )
        elif len(self._files) > 1:
            self.file_path_label.setText(f"📂 {len(self._files)} 个文件")
            self.file_path_label.setStyleSheet(
                "color: #cdd6f4; padding: 6px 10px; background: #181825; "
                "border: 1px solid #313244; border-radius: 4px;"
            )
        else:
            self.file_path_label.setText("未选择")
            self.file_path_label.setStyleSheet(
                "color: #585b70; padding: 6px 10px; background: #181825; "
                "border: 1px solid #313244; border-radius: 4px;"
            )

    def _show_batch_list(self):
        """显示批量文件列表"""
        self.file_list.setVisible(True)
        self.file_list.clear()
        for f in self._files:
            item = QListWidgetItem(f"{f.name} — {f.parent.name}")
            item.setToolTip(str(f))
            self.file_list.addItem(item)

    def _load_content_preview(self, file_path: Path):
        """加载文件内容预览"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > 10000:
                content = content[:10000] + "\n\n... (内容过长，已截断)"
            self.content_preview.setPlainText(content)
        except Exception:
            self.content_preview.setPlainText("(无法预览二进制文件内容)")

    # ── 生成摘要 ──

    @Slot()
    def _on_summarize(self):
        """生成单文件摘要"""
        if not self._files or self._processing:
            return
        self._init_ai()
        self._start_summarize(self._files[0])

    @Slot()
    def _on_batch_summarize(self):
        """批量生成摘要"""
        if not self._files or self._processing:
            return
        self._init_ai()
        self._start_batch_summarize(self._files)

    @Slot()
    def _on_cancel_processing(self):
        """取消摘要处理"""
        self._cancelled = True
        self._processing = False
        self.btn_cancel.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._set_buttons_enabled(True)
        self.status_message.emit("⏹️ 处理已取消")

    def _start_summarize(self, file_path: Path):
        """启动单文件摘要线程"""
        self._cancelled = False
        self._processing = True
        self._set_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_text.emit("正在准备...")
        self.status_message.emit(f"正在分析: {file_path.name}")

        summarizer = self._summarizer

        def worker():
            try:
                if self._cancelled:
                    return

                # 加载内容预览
                self._load_content_preview(file_path)

                def on_progress(msg: str):
                    if self._cancelled:
                        return
                    self.progress_text.emit(msg)

                result = summarizer.summarize(
                    file_path,
                    max_length=300,
                    on_progress=on_progress,
                )

                if not self._cancelled:
                    from PySide6.QtCore import QMetaObject, Qt, Q_ARG

                    QMetaObject.invokeMethod(
                        self,
                        "_display_summary_result",
                        Qt.QueuedConnection,
                        Q_ARG(object, result),
                    )
            except Exception as e:
                if not self._cancelled:
                    from PySide6.QtCore import QMetaObject, Qt, Q_ARG

                    QMetaObject.invokeMethod(
                        self,
                        "_on_summarize_error",
                        Qt.QueuedConnection,
                        Q_ARG(str, str(e)),
                    )

        Thread(target=worker, daemon=True).start()

    def _start_batch_summarize(self, files: list[Path]):
        """启动批量摘要线程"""
        self._cancelled = False
        self._processing = True
        self._set_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(0)

        total = len(files)
        results: list[str] = []
        errors = 0
        summarizer = self._summarizer

        def worker():
            nonlocal errors
            for i, file_path in enumerate(files):
                if self._cancelled:
                    break

                progress_pct = int((i + 1) / total * 100)
                self.progress_updated.emit(progress_pct)
                self.progress_text.emit(f"({i + 1}/{total}) {file_path.name}")
                self.status_message.emit(f"正在处理 ({i + 1}/{total}): {file_path.name}")

                if self._cancelled:
                    break

                try:
                    result = summarizer.summarize(file_path, max_length=200)
                    if result.get("success"):
                        summary = result["summary"]
                        results.append(
                            f"## 📄 {file_path.name}\n\n"
                            f"> 路径: {file_path}\n\n"
                            f"{summary}\n\n"
                            f"关键词: {' · '.join(result.get('keywords', []))}\n"
                            "---\n"
                        )
                    else:
                        results.append(
                            f"## ❌ {file_path.name}\n\n"
                            f"{result.get('error', '处理失败')}\n\n---\n"
                        )
                        errors += 1
                except Exception as e:
                    results.append(
                        f"## ❌ {file_path.name}\n\n{str(e)}\n\n---\n"
                    )
                    errors += 1

            if self._cancelled:
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self, "_on_cancel_processing", Qt.QueuedConnection
                )
                return

            combined = "\n".join(results)

            from PySide6.QtCore import QMetaObject, Qt, Q_ARG

            QMetaObject.invokeMethod(
                self,
                "_display_batch_result",
                Qt.QueuedConnection,
                Q_ARG(str, combined),
                Q_ARG(int, total),
                Q_ARG(int, errors),
            )

        Thread(target=worker, daemon=True).start()

    @Slot(object)
    def _display_summary_result(self, result: dict):
        """显示单文件摘要结果"""
        self._processing = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._set_buttons_enabled(True)

        if result.get("success"):
            summary = result["summary"]
            keywords = result.get("keywords", [])

            self.summary_preview.setPlainText(summary)
            self.btn_copy.setEnabled(True)

            # 显示关键词标签
            self._clear_keywords()
            for word in keywords:
                self.keywords_layout.addWidget(self._make_keyword_tag(word))
            self.keywords_layout.addStretch()

            file_name = result.get("filename", "")
            self.status_message.emit(
                f"✅ 摘要生成完成: {file_name} | "
                f"{len(summary)} 字摘要 | {len(keywords)} 个关键词"
            )
        else:
            self.summary_preview.setPlainText(
                f"❌ 生成失败\n\n{result.get('error', '未知错误')}"
            )
            self.status_message.emit(f"❌ {result.get('error', '生成失败')}")

    @Slot()
    def _display_batch_result(self, combined: str, total: int, errors: int):
        """显示批量摘要结果"""
        self._processing = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._set_buttons_enabled(True)

        self.summary_preview.setPlainText(combined)
        self.btn_copy.setEnabled(True)
        self._clear_keywords()

        success = total - errors
        self.status_message.emit(
            f"📦 批量处理完成: {success}/{total} 成功"
            + (f", {errors} 个失败" if errors else "")
        )

    @Slot()
    def _on_summarize_error(self, error_msg: str):
        """摘要出错"""
        self._processing = False
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self._set_buttons_enabled(True)
        self.summary_preview.setPlainText(f"❌ 处理出错\n\n{error_msg}")
        self.status_message.emit(f"❌ {error_msg}")

    # ── 辅助方法 ──

    def _set_buttons_enabled(self, enabled: bool):
        """设置按钮可用状态"""
        self.btn_summarize.setEnabled(enabled and len(self._files) == 1)
        self.btn_batch.setEnabled(enabled and len(self._files) > 1)
        self.btn_select_file.setEnabled(enabled)
        self.btn_select_folder.setEnabled(enabled)

    def _clear_keywords(self):
        """清空关键词标签"""
        while self.keywords_layout.count() > 0:
            item = self.keywords_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @Slot()
    def _on_clear(self):
        """清空所有结果"""
        self._files = []
        self._processing = False
        self.file_path_label.setText("未选择")
        self.file_path_label.setStyleSheet(
            "color: #585b70; padding: 6px 10px; background: #181825; "
            "border: 1px solid #313244; border-radius: 4px;"
        )
        self.file_list.setVisible(False)
        self.file_list.clear()
        self.content_preview.clear()
        self.summary_preview.clear()
        self._clear_keywords()
        self.btn_summarize.setEnabled(False)
        self.btn_batch.setEnabled(False)
        self.btn_copy.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.status_message.emit("就绪")

    @Slot()
    def _on_copy_summary(self):
        """复制摘要到剪贴板"""
        text = self.summary_preview.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_message.emit("📋 摘要已复制到剪贴板")

    def refresh_ai_status(self):
        """刷新 AI 状态（外部调用）"""
        Thread(target=self._init_ai, daemon=True).start()
