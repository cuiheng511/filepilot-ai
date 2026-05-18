"""File Statistics & Disk Visualization panel — file distribution by type, size, date, treemap."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.file_scanner import FileCategory, FileInfo, FileScanner
from filepilot.core.worker import Worker
from filepilot.ui.base_panel import BasePanel

logger = logging.getLogger("filepilot.stats_panel")

# ── Color palette for distribution bars ──────────────────────────

_CATEGORY_COLORS = {
    FileCategory.DOCUMENT: "#4a9eff",
    FileCategory.IMAGE: "#f5a623",
    FileCategory.VIDEO: "#e74c3c",
    FileCategory.AUDIO: "#9b59b6",
    FileCategory.CODE: "#2ecc71",
    FileCategory.ARCHIVE: "#e67e22",
    FileCategory.PDF: "#e74c3c",
    FileCategory.MARKDOWN: "#1abc9c",
    FileCategory.SPREADSHEET: "#27ae60",
}

_CATEGORY_ICONS = {
    FileCategory.DOCUMENT: "📄",
    FileCategory.IMAGE: "🖼️",
    FileCategory.VIDEO: "🎬",
    FileCategory.AUDIO: "🎵",
    FileCategory.CODE: "💻",
    FileCategory.ARCHIVE: "🗜️",
    FileCategory.PDF: "📕",
    FileCategory.MARKDOWN: "📝",
    FileCategory.SPREADSHEET: "📊",
}

_SIZE_RANGES = [
    ("< 1 KB", 0, 1024),
    ("1 KB – 100 KB", 1024, 100 * 1024),
    ("100 KB – 1 MB", 100 * 1024, 1024 * 1024),
    ("1 MB – 10 MB", 1024 * 1024, 10 * 1024 * 1024),
    ("10 MB – 100 MB", 10 * 1024 * 1024, 100 * 1024 * 1024),
    ("> 100 MB", 100 * 1024 * 1024, float("inf")),
]

_DATE_RANGES = [
    ("Today", 0),
    ("This Week", 7),
    ("This Month", 30),
    ("This Year", 365),
    ("Older", None),
]

_TREEMAP_COLORS = [
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#96CEB4",
    "#FFEAA7",
    "#DDA0DD",
    "#98D8C8",
    "#F7DC6F",
    "#BB8FCE",
    "#85C1E9",
    "#F8B500",
    "#5D8AA8",
    "#E6B0AA",
    "#7DCEA0",
    "#AED6F1",
]


class TreemapWidget(QWidget):
    """Custom widget that draws a treemap visualization of file sizes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # list of (name, size, color)
        self.setMinimumSize(400, 300)

    def set_data(self, data):
        """Set treemap data: list of (name, size, color_hex)."""
        self.data = data
        self.update()

    def paintEvent(self, event):  # noqa: N802
        if not self.data:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawText(self.rect(), Qt.AlignCenter, "No data to display")
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        total = sum(size for _, size, _ in self.data)
        if total == 0:
            return

        rect = self.rect()
        self._draw_treemap(painter, rect, self.data, total)

    def _draw_treemap(self, painter, rect, data, total):
        """Recursively draw treemap rectangles."""
        if not data or total == 0:
            return

        sorted_data = sorted(data, key=lambda x: x[1], reverse=True)

        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

        for name, size, color_hex in sorted_data:
            if w <= 0 or h <= 0:
                break

            ratio = size / total
            if w > h:
                block_w = int(w * ratio)
                block_h = h
                painter.fillRect(x, y, block_w, block_h, QColor(color_hex))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawRect(x, y, block_w, block_h)

                if block_w > 40 and block_h > 20:
                    painter.setPen(Qt.white if QColor(color_hex).lightness() < 128 else Qt.black)
                    font = painter.font()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.drawText(x + 2, y + 12, name[:15])

                x += block_w
                w -= block_w
            else:
                block_w = w
                block_h = int(h * ratio)
                painter.fillRect(x, y, block_w, block_h, QColor(color_hex))
                painter.setPen(QPen(Qt.black, 1))
                painter.drawRect(x, y, block_w, block_h)

                if block_w > 40 and block_h > 20:
                    painter.setPen(Qt.white if QColor(color_hex).lightness() < 128 else Qt.black)
                    font = painter.font()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.drawText(x + 2, y + 12, name[:15])

                y += block_h
                h -= block_h


class FileStatsPanel(BasePanel):
    """File statistics & disk visualization panel — distribution + treemap."""

    analyze_requested = Signal(str)
    stats_ready = Signal(dict)

    def __init__(self, scanner: FileScanner | None = None, parent=None):
        super().__init__(parent)
        self.scanner = scanner or FileScanner()
        self.current_dir: str | None = None
        self._setup_ui()
        self._connect_signals()
        self._show_empty_state()

    # ── Public API ───────────────────────────────────────────────

    def set_current_dir(self, dir_path: str | None) -> None:
        """Update the known current directory."""
        self.current_dir = dir_path
        self.btn_analyze.setEnabled(bool(dir_path))

    def analyze_directory(self, dir_path: str | Path) -> None:
        """Scan a directory and display statistics."""
        self.current_dir = str(dir_path)
        self._run_analysis(dir_path)

    # ── Setup ────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Title
        title = QLabel("\U0001f4ca File Statistics & Disk Usage")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel(
            "Analyze file distribution by type, size, and modification date.\n"
            "Visualize disk space usage with treemap. Open a folder first, then click Analyze."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_select_dir = QPushButton("\U0001f4c2 Select Folder")
        self.btn_select_dir.clicked.connect(self._on_select_directory)
        self.btn_analyze = QPushButton("\U0001f50d Analyze")
        self.btn_analyze.setToolTip("Scan the current directory and show statistics")
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._on_analyze)
        self.view_combo = QComboBox()
        self.view_combo.addItem("\U0001f4ca Statistics")
        self.view_combo.addItem("\U0001f4c8 Treemap")
        self.view_combo.currentTextChanged.connect(self._on_view_changed)
        toolbar.addWidget(self.btn_select_dir)
        toolbar.addWidget(self.btn_analyze)
        toolbar.addStretch()
        toolbar.addWidget(QLabel("View:"))
        toolbar.addWidget(self.view_combo)
        layout.addLayout(toolbar)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Stat cards row
        stats_row = QHBoxLayout()
        self._stat_total_files = self._make_stat_card("Total Files", "0")
        self._stat_total_size = self._make_stat_card("Total Size", "0 B")
        self._stat_categories = self._make_stat_card("Categories", "0")
        stats_row.addWidget(self._stat_total_files)
        stats_row.addWidget(self._stat_total_size)
        stats_row.addWidget(self._stat_categories)
        layout.addLayout(stats_row)

        # Main content: scrollable stats | treemap
        main_splitter = QSplitter(Qt.Horizontal)

        # Scrollable content area for distribution sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setSpacing(12)
        scroll.setWidget(self._content_widget)
        main_splitter.addWidget(scroll)

        # Treemap widget
        self.treemap = TreemapWidget()
        self.treemap.setVisible(False)
        main_splitter.addWidget(self.treemap)

        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 1)
        layout.addWidget(main_splitter, stretch=1)

        # Placeholder for distribution sections (rebuilt each analysis)
        self._section_type: QWidget | None = None
        self._section_size: QWidget | None = None
        self._section_date: QWidget | None = None

    def _connect_signals(self) -> None:
        self.btn_analyze.clicked.connect(self._on_analyze)
        self.stats_ready.connect(self._on_stats_ready)
        self.status_message.connect(self._on_status_message)

    # ── State ────────────────────────────────────────────────────

    def _show_empty_state(self) -> None:
        """Show placeholder when no analysis has been run."""
        self._update_stat("Total Files", "0")
        self._update_stat("Total Size", "0 B")
        self._update_stat("Categories", "0")
        self._clear_sections()
        self._update_add_button_state()

    def _clear_sections(self) -> None:
        """Remove all distribution sections from the content area."""
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child is not None:
                w = child.widget()
                if w is not None:
                    w.deleteLater()
        self._section_type = None
        self._section_size = None
        self._section_date = None

    def _update_add_button_state(self) -> None:
        self.btn_analyze.setEnabled(bool(self.current_dir))

    @Slot()
    def _on_select_directory(self) -> None:
        """Select directory to analyze."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder to Analyze")
        if dir_path:
            self.current_dir = dir_path
            self.btn_analyze.setEnabled(True)
            self.status_message.emit(f"Selected: {Path(dir_path).name}")

    # ── Analysis (background thread) ────────────────────────────

    def _run_analysis(self, dir_path: str | Path) -> None:
        """Run analysis in a background thread."""
        self.btn_analyze.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.emit("Scanning directory...")

        def worker():
            files: list[FileInfo] = []
            for i, f in enumerate(self.scanner.scan(str(dir_path))):
                files.append(f)
                if i % 50 == 0:
                    self.progress_updated.emit(min(i, 100))

            # Compute stats
            stats = self._compute_stats(files)
            stats["directory"] = str(dir_path)

            # Signal results to main thread
            self.stats_ready.emit(stats)

        w = Worker(worker)
        w.signals.finished.connect(lambda _: None)
        w.signals.error.connect(self._on_stats_error)
        QThreadPool.globalInstance().start(w)

    def _compute_stats(self, files: list[FileInfo]) -> dict:
        """Compute type, size, and date distributions."""
        total_files = len(files)
        total_size = sum(f.size_bytes for f in files)

        # By size range
        by_size: list[dict] = []
        for label, lo, hi in _SIZE_RANGES:
            matched = [f for f in files if lo <= f.size_bytes < hi]
            if matched:
                by_size.append(
                    {
                        "label": label,
                        "count": len(matched),
                        "size": sum(f.size_bytes for f in matched),
                        "files": matched,
                    }
                )

        # By date — non-overlapping ranges
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = datetime(now.year, now.month, 1)
        year_start = datetime(now.year, 1, 1)

        date_groups = [
            ("Today", lambda f: f.modified_time and f.modified_time >= today_start),
            (
                "This Week",
                lambda f: f.modified_time and week_start <= f.modified_time < today_start,
            ),
            (
                "This Month",
                lambda f: f.modified_time and month_start <= f.modified_time < week_start,
            ),
            (
                "This Year",
                lambda f: f.modified_time and year_start <= f.modified_time < month_start,
            ),
            ("Older", lambda f: f.modified_time and f.modified_time < year_start),
            ("Unknown", lambda f: f.modified_time is None),
        ]

        by_date_final = []
        for label, predicate in date_groups:
            matched = [f for f in files if predicate(f)]
            if matched:
                by_date_final.append(
                    {
                        "label": label,
                        "count": len(matched),
                        "size": sum(f.size_bytes for f in matched),
                    }
                )

        # Build category stats with proper enum objects
        category_stats = []
        for cat in FileCategory:
            matched = [f for f in files if f.category == cat]
            if matched:
                category_stats.append(
                    {
                        "category": cat,
                        "count": len(matched),
                        "size": sum(f.size_bytes for f in matched),
                    }
                )
        from typing import cast

        category_stats.sort(key=lambda x: cast(int, x.get("count", 0)), reverse=True)

        return {
            "total_files": total_files,
            "total_size": total_size,
            "by_category": category_stats,
            "by_size": by_size,
            "by_date": by_date_final,
            "all_files": files,
        }

    @Slot()
    def _on_analyze(self) -> None:
        """Analyze the current directory."""
        if self.current_dir:
            self._run_analysis(self.current_dir)

    @Slot(str)
    def _on_stats_error(self, msg: str) -> None:
        """Restore UI after analysis error."""
        self.status_message.emit(f"Stats error: {msg}")
        self.progress_bar.setVisible(False)
        self.btn_analyze.setEnabled(bool(self.current_dir))

    @Slot(dict)
    def _on_stats_ready(self, stats: dict) -> None:
        """Display computed statistics."""
        self.progress_bar.setVisible(False)
        self.btn_analyze.setEnabled(True)

        # Update stat cards
        self._update_stat("Total Files", f"{stats['total_files']:,}")
        self._update_stat("Total Size", self._fmt_size(stats["total_size"]))
        self._update_stat("Categories", str(len(stats["by_category"])))

        # Rebuild distribution sections
        self._clear_sections()

        # By Type
        type_section = self._build_section(
            "\U0001f4c2 By Type",
            stats["by_category"],
            lambda item: self._make_distribution_row(
                icon=_CATEGORY_ICONS.get(item["category"], "\U0001f4c1"),
                label=item["category"].label
                if hasattr(item["category"], "label")
                else str(item["category"]),
                count=item["count"],
                size=item["size"],
                total=stats["total_files"],
                color=_CATEGORY_COLORS.get(item["category"], "#888"),
            ),
        )
        if type_section:
            self._content_layout.addWidget(type_section)

        # By Size
        size_section = self._build_section(
            "\U0001f4cf By Size",
            stats["by_size"],
            lambda item: self._make_distribution_row(
                icon="\U0001f4be",
                label=item["label"],
                count=item["count"],
                size=item["size"],
                total=stats["total_files"],
                color="#3498db",
            ),
        )
        if size_section:
            self._content_layout.addWidget(size_section)

        # By Date
        date_section = self._build_section(
            "\U0001f4c5 By Modification Date",
            stats["by_date"],
            lambda item: self._make_distribution_row(
                icon="\U0001f550",
                label=item["label"],
                count=item["count"],
                size=item["size"],
                total=stats["total_files"],
                color="#1abc9c",
            ),
        )
        if date_section:
            self._content_layout.addWidget(date_section)

        # Push remaining space to bottom
        self._content_layout.addStretch()

        # Update treemap with top 20 files by size
        treemap_data = []
        top_files = sorted(stats.get("all_files", []), key=lambda f: f.size_bytes, reverse=True)[
            :20
        ]
        for i, f in enumerate(top_files):
            color = _TREEMAP_COLORS[i % len(_TREEMAP_COLORS)]
            treemap_data.append((f.name, f.size_bytes, color))
        self.treemap.set_data(treemap_data)

        self.status_message.emit(
            f"Analysis complete: {stats['total_files']:,} files, "
            f"{self._fmt_size(stats['total_size'])}"
        )

    # ── UI Builders ──────────────────────────────────────────────

    def _build_section(self, title: str, items: list, row_factory) -> QWidget | None:
        """Build a collapsible section with distribution rows."""
        if not items:
            return None

        container = QFrame()
        container.setObjectName("statsSection")
        container.setStyleSheet(
            "QFrame#statsSection { background: rgba(128,128,128,0.06);"
            " border-radius: 8px; padding: 4px; }"
        )
        section_layout = QVBoxLayout(container)
        section_layout.setContentsMargins(12, 8, 12, 8)
        section_layout.setSpacing(4)

        # Section header
        header = QLabel(title)
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        section_layout.addWidget(header)

        # Distribution rows
        for item in items:
            row = row_factory(item)
            if row:
                section_layout.addWidget(row)

        return container

    def _make_distribution_row(
        self,
        icon: str,
        label: str,
        count: int,
        size: int,
        total: int,
        color: str,
    ) -> QWidget:
        """Create a single distribution row with label, bar, and stats."""
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(2)

        # Top line: icon + label + count + size
        top = QHBoxLayout()
        label_widget = QLabel(f"{icon}  {label}")
        label_widget.setStyleSheet("font-size: 12px;")
        top.addWidget(label_widget)

        count_label = QLabel(f"{count:,} files")
        count_label.setStyleSheet("color: #888; font-size: 11px;")
        top.addWidget(count_label)

        size_label = QLabel(self._fmt_size(size))
        size_label.setStyleSheet("color: #888; font-size: 11px;")
        top.addWidget(size_label)

        pct = (count / total * 100) if total > 0 else 0
        pct_label = QLabel(f"{pct:.1f}%")
        pct_label.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 11px; min-width: 45px;"
        )
        pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(pct_label)

        row_layout.addLayout(top)

        # Progress bar (visual)
        bar = QFrame()
        bar.setFixedHeight(6)
        bar.setStyleSheet("background: rgba(128,128,128,0.12); border-radius: 3px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)

        fill = QFrame()
        fill.setFixedHeight(6)
        fill.setStyleSheet(f"background: {color}; border-radius: 3px;")
        # Use a fixed percentage width via fixed pixel size
        bar_width = 300  # max width of the bar
        fill_width = max(int(bar_width * pct / 100), 2)
        fill.setFixedWidth(fill_width)
        bar_layout.addWidget(fill)
        bar_layout.addStretch()

        row_layout.addWidget(bar)

        return row

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _fmt_size(size_bytes: int) -> str:
        """Format byte size to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / 1024 / 1024:.1f} MB"
        else:
            return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"

    @Slot()
    def _on_status_message(self, msg: str) -> None:
        """Update status bar."""
        logger.debug("Stats panel: %s", msg)

    @Slot()
    def _on_view_changed(self, text: str) -> None:
        """Switch between statistics and treemap view."""
        if "\U0001f4c8 Treemap" in text:
            self.treemap.setVisible(True)
        else:
            self.treemap.setVisible(False)
