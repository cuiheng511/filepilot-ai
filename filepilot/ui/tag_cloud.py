"""Tag Cloud Widget — visual tag display with size proportional to file count."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from filepilot.core.tag_manager import TagManager

_TAG_COLORS = [
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


class TagCloudWidget(QWidget):
    """Displays tags as a cloud with size proportional to usage count.

    Clicking a tag emits `tag_clicked` with the tag name.
    """

    tag_clicked = Signal(str)

    def __init__(self, tag_manager: TagManager | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._tag_manager = tag_manager or TagManager()
        self._tag_labels: list[QLabel] = []
        self._setup_ui()

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)

        self._cloud_container = QWidget()
        self._cloud_container.setObjectName("tagCloudContainer")
        self._flow_layout = FlowLayout(self._cloud_container)
        self._layout.addWidget(self._cloud_container, 1)

    def refresh(self):
        """Rebuild the tag cloud from current tag data."""
        # Clear existing labels
        for label in self._tag_labels:
            label.deleteLater()
        self._tag_labels.clear()

        # Get tag counts
        tagged_files = self._tag_manager.get_tagged_files()
        tag_counts: dict[str, int] = {}
        for entry in tagged_files.values():
            for tag in entry.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            placeholder = QLabel("No tags yet. Add tags to files to see the cloud.")
            placeholder.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
            placeholder.setAlignment(Qt.AlignCenter)
            self._flow_layout.addWidget(placeholder)
            self._tag_labels.append(placeholder)
            return

        # Calculate font sizes (min 9pt, max 20pt)
        max_count = max(tag_counts.values())
        min_count = min(tag_counts.values())
        count_range = max(max_count - min_count, 1)

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        for i, (tag, count) in enumerate(sorted_tags):
            # Scale font size
            ratio = (count - min_count) / count_range
            font_size = int(9 + ratio * 11)

            color = _TAG_COLORS[i % len(_TAG_COLORS)]
            label = ClickableTagLabel(tag, count, color, font_size)
            label.clicked.connect(self.tag_clicked.emit)
            self._flow_layout.addWidget(label)
            self._tag_labels.append(label)

    def set_tag_manager(self, tm: TagManager):
        """Update the tag manager reference."""
        self._tag_manager = tm
        self.refresh()


class ClickableTagLabel(QLabel):
    """A clickable tag label for the cloud."""

    clicked = Signal(str)

    def __init__(self, tag: str, count: int, color: str, font_size: int, parent=None):
        super().__init__(parent)
        self._tag = tag
        self.setText(f" {tag} ({count}) ")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"Tag: {tag}\nFiles: {count}\nClick to filter")
        font = QFont()
        font.setPointSize(font_size)
        font.setBold(count > 3)
        self.setFont(font)
        self.setStyleSheet(
            f"QLabel {{ color: {color}; padding: 4px 8px; margin: 2px;"
            f" background: rgba(255,255,255,0.05); border-radius: 4px; }}"
            f"QLabel:hover {{ background: rgba(255,255,255,0.12); }}"
        )

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._tag)
        super().mousePressEvent(event)


class FlowLayout(QVBoxLayout):
    """Simple flow layout that wraps widgets horizontally.

    Uses a container widget with manual positioning. Reflows on resize.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)
        self._container = _FlowContainer()
        super().addWidget(self._container)

    def addWidget(  # noqa: N802
        self,
        widget: QWidget,
        stretch: int | None = None,
        alignment: Qt.AlignmentFlag | None = None,
    ):
        """Add widget to flow."""
        widget.setParent(self._container)
        self._container._widgets.append(widget)
        widget.show()
        self._container._reflow()


class _FlowContainer(QWidget):
    """Internal container that handles reflow on resize."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets: list[QWidget] = []

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self):
        """Reposition all widgets in a flow pattern."""
        if not self._widgets:
            return
        x = 0
        y = 0
        row_height = 0
        max_width = max(self.width(), 200)

        for widget in self._widgets:
            hint = widget.sizeHint()
            w = hint.width()
            h = hint.height()

            if x + w > max_width and x > 0:
                x = 0
                y += row_height + 4
                row_height = 0

            widget.move(x, y)
            widget.resize(w, h)
            x += w + 4
            row_height = max(row_height, h)

        total_height = y + row_height + 8
        self.setMinimumHeight(total_height)
