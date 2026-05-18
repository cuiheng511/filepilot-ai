"""Preview panel — file content, image, and archive preview (async for text)."""

from pathlib import Path
from threading import Thread

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from filepilot.utils.file_utils import (
    get_category_name,
    get_file_size_str,
)


class PreviewPanel(QWidget):
    """File preview widget with async text loading."""

    preview_ready = Signal(str, str)  # html_content, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_preview_path: str | None = None
        self._setup_ui()
        self.preview_ready.connect(self._on_preview_ready)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.preview_stack = QStackedWidget()

        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setPlaceholderText("Select a file to preview its content or metadata...")
        self.preview_stack.addWidget(self.text_preview)  # index 0

        self.image_scroll = QScrollArea()
        self.image_label = QLabel("Loading...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_scroll.setWidget(self.image_label)
        self.image_scroll.setWidgetResizable(True)
        self.preview_stack.addWidget(self.image_scroll)  # index 1

        self.archive_list = QListWidget()
        self.preview_stack.addWidget(self.archive_list)  # index 2

        layout.addWidget(self.preview_stack, 1)

    def show_preview(self, path: Path):
        """Trigger async preview for a file."""
        self._current_preview_path = str(path)
        self._preview_file(path)

    def clear(self):
        """Clear preview."""
        self.preview_stack.setCurrentIndex(0)
        self.text_preview.clear()
        self.image_label.clear()
        self.archive_list.clear()

    def _preview_file(self, path: Path):
        """Preview file content or metadata (async for text/code)."""
        cat = get_category_name(path.suffix.lower())
        ext = path.suffix.lower()
        try:
            st = path.stat()
            size_str = get_file_size_str(st.st_size)
            modified_str = st.st_mtime
        except OSError:
            size_str = "?"
            modified_str = 0

        # Archive preview
        if self._try_preview_archive(path):
            return

        # Image preview
        if cat == "Image":
            self.preview_stack.setCurrentIndex(1)
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(600, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                details = (
                    f"<p style='text-align:center;color:#888;'>"
                    f"{path.name}  |  {pixmap.width()}×{pixmap.height()}px  |  {size_str}"
                    f"</p>"
                )
                self.image_label.setToolTip(details)
            else:
                self.preview_stack.setCurrentIndex(0)
                self.text_preview.setHtml(
                    f"<p><b>🖼️ {path.name}</b></p>"
                    f"<p>Size: {size_str} | Modified: {modified_str:.0f}</p>"
                    f"<p><i>Cannot load image preview.</i></p>"
                )
            return

        # Text/code/markdown preview (async)
        is_text_like = cat in ("Code", "Text") or ext in (
            ".txt",
            ".log",
            ".cfg",
            ".ini",
            ".conf",
            ".yaml",
            ".yml",
            ".toml",
            ".json",
            ".xml",
            ".csv",
        )
        is_markdown = ext in (".md", ".markdown", ".mdx", ".rst")

        if is_text_like or is_markdown:
            self.preview_stack.setCurrentIndex(0)
            self.text_preview.setPlainText("Loading...")
            Thread(
                target=self._preview_text_worker,
                args=(path, is_markdown),
                daemon=True,
            ).start()
            return

        # PDF / Office — metadata only
        self.preview_stack.setCurrentIndex(0)
        stats_html = f"<p>Size: {size_str}</p><p>Modified: {modified_str:.0f}</p>"
        if cat == "PDF":
            self.text_preview.setHtml(
                f"<p><b>📕 PDF file:</b> {path.name}</p>"
                f"<p><i>Use the 'AI Summary' panel"
                f" to extract content from this PDF.</i></p>{stats_html}"
            )
        elif cat == "Office":
            self.text_preview.setHtml(
                f"<p><b>📄 Office file:</b> {path.name}</p>"
                f"<p><i>Use the 'AI Summary' panel to extract content.</i></p>{stats_html}"
            )
        else:
            self.text_preview.setHtml(
                f"<p><b>📄 {path.name}</b></p>{stats_html}"
                f"<p><i>Preview not available for this file type.</i></p>"
            )

    def _preview_text_worker(self, path: Path, is_markdown: bool):
        """Read text file in background and emit preview_ready."""
        try:
            if is_markdown:
                import markdown as md_lib

                raw = path.read_text(encoding="utf-8", errors="replace")[:10000]
                html = md_lib.markdown(
                    raw,
                    extensions=["extra", "codehilite", "tables", "fenced_code"],
                )
                styled = f"""
                <style>
                  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; padding: 12px; }}
                  pre {{ background: #1e1e1e; color: #d4d4d4; padding: 10px;"
                  " border-radius: 6px; overflow-x: auto; }}
                  code {{ background: #2d2d2d; padding: 2px 5px; border-radius: 3px; }}
                  img {{ max-width: 100%; }}
                  table {{ border-collapse: collapse; width: 100%; }}
                  th, td {{ border: 1px solid #444; padding: 6px 10px; text-align: left; }}
                </style>
                {html}
                """
            else:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                max_lines = 200
                shown = lines[:max_lines]
                num_width = len(str(max_lines))
                html_lines = []
                for i, line in enumerate(shown, 1):
                    escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    html_lines.append(
                        f"<tr><td style='color:#666;padding:0 8px 0 0;text-align:right;"
                        f"user-select:none;width:{num_width}ch;'>{i:>{num_width}}</td>"
                        f"<td style='white-space:pre;padding:0;'>{escaped}</td></tr>"
                    )
                table = "".join(html_lines)
                styled = f"""
                <style>
                  body {{ margin:0; padding:8px;"
                  " font-family:'Cascadia Code','Consolas',monospace; font-size:13px; }}
                  table {{ border-spacing:0; width:100%; }}
                  tr:hover td {{ background:#2a2a2a; }}
                </style>
                <table>{table}</table>
                """
                if len(lines) > max_lines:
                    styled += (
                        f"<p style='color:#888;'><i>… {len(lines) - max_lines} more lines</i></p>"
                    )
            self.preview_ready.emit(styled, str(path))
        except Exception:
            self.preview_ready.emit(
                f"<p><i>Failed to load preview for {path.name}</i></p>", str(path)
            )

    @Slot()
    def _on_preview_ready(self, html: str, file_path: str):
        """Display async preview result — guard against stale results."""
        if self._current_preview_path == file_path:
            self.text_preview.setHtml(html)

    def _try_preview_archive(self, path: Path) -> bool:
        """Show archive contents. Returns True if handled."""
        ext = path.suffix.lower()
        name_lower = path.name.lower()
        entries: list[str] = []

        if ext == ".zip":
            import zipfile

            try:
                with zipfile.ZipFile(path, "r") as zf:
                    for info in zf.infolist():
                        entries.append(f"📄 {info.filename}  ({get_file_size_str(info.file_size)})")
            except Exception:
                return False
        elif ext in (".tar", ".tgz", ".gz", ".bz2", ".xz", ".txz"):
            import tarfile

            try:
                mode = {
                    ".tgz": "r:gz",
                    ".gz": "r:gz",
                    ".bz2": "r:bz2",
                    ".xz": "r:xz",
                    ".txz": "r:xz",
                    ".tar": "r:",
                }.get(ext, "r:")
                if name_lower.endswith(".tar.gz"):
                    mode = "r:gz"
                elif name_lower.endswith(".tar.bz2"):
                    mode = "r:bz2"
                elif name_lower.endswith(".tar.xz"):
                    mode = "r:xz"
                with tarfile.open(path, mode) as tf:  # type: ignore[call-overload]
                    for info in tf.getmembers():
                        entries.append(f"📄 {info.name}  ({get_file_size_str(info.size)})")
            except Exception:
                return False
        else:
            return False

        self.preview_stack.setCurrentIndex(2)
        self.archive_list.clear()
        self.archive_list.addItem(f"📦 {path.name}  ({len(entries)} files)")
        self.archive_list.addItem("")
        for e in entries:
            self.archive_list.addItem(e)
        return True
