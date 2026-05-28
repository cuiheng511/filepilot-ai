"""Tag Cloud Widget — visual tag display with size proportional to file count."""

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QLayout, QLayoutItem, QVBoxLayout, QWidget

from filepilot.core.tag_manager import TagManager
from filepilot.i18n import t

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

    def _setup_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)

        self._cloud_container = QWidget()
        self._cloud_container.setObjectName("tagCloudContainer")
        self._flow_layout = FlowLayout(self._cloud_container)
        self._layout.addWidget(self._cloud_container, 1)

    def refresh(self) -> None:
        """Rebuild the tag cloud from current tag data."""
        # Clear existing labels
        for label in self._tag_labels:
            label.deleteLater()
        self._tag_labels.clear()
        self._flow_layout.clear()

        # Get tag counts
        tagged_files = self._tag_manager.get_tagged_files()
        tag_counts: dict[str, int] = {}
        for entry in tagged_files.values():
            for tag in entry.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            placeholder = QLabel(t("tag_cloud_empty"))
            placeholder.setObjectName("emptyStateLabel")
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

    def set_tag_manager(self, tm: TagManager) -> None:
        """Update the tag manager reference."""
        self._tag_manager = tm
        self.refresh()


class ClickableTagLabel(QLabel):
    """A clickable tag label for the cloud."""

    clicked = Signal(str)

    def __init__(
        self,
        tag: str,
        count: int,
        color: str,
        font_size: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tag = tag
        self.setObjectName("tagCloudLabel")
        self.setAccessibleName(f"{tag}, {count} files")
        self.setText(f" {tag} ({count}) ")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(t("tag_cloud_tooltip", tag=tag, count=count))
        font = QFont()
        font.setPointSize(font_size)
        font.setBold(count > 3)
        self.setFont(font)
        self.setStyleSheet(f"QLabel#tagCloudLabel {{ color: {color}; }}")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._tag)
        super().mousePressEvent(event)


class FlowLayout(QLayout):
    """Qt layout that wraps child widgets horizontally."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 4) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def clear(self) -> None:
        while self._items:
            item = self.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = 0
        y = 0
        row_height = 0
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        x = effective_rect.x()
        y = effective_rect.y()
        max_width = max(effective_rect.width(), 200)
        spacing = self.spacing()

        for item in self._items:
            hint = item.sizeHint()
            w = hint.width()
            h = hint.height()

            if x + w > effective_rect.x() + max_width and x > effective_rect.x():
                x = effective_rect.x()
                y += row_height + spacing
                row_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += w + spacing
            row_height = max(row_height, h)

        return y + row_height - rect.y() + margins.bottom()
