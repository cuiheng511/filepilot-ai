"""Notification History — records and displays past toast notifications."""

from datetime import datetime

from PySide6.QtCore import Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from filepilot.i18n import t


class NotificationHistory(QWidget):
    """Widget that records and displays notification history.

    Connect to this widget's `record()` slot to log notifications.
    Displays them in a scrollable list with timestamps and level colors.
    """

    MAX_ENTRIES = 200

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName(t("notifications_title"))
        self._entries: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        title = QLabel(t("notifications_title"))
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self.count_label = QLabel("0")
        self.count_label.setObjectName("statsLabel")
        self.count_label.setAccessibleName("Notification count")
        header.addWidget(self.count_label)

        self.btn_clear = QPushButton(t("clear"))
        self.btn_clear.setAccessibleName(t("clear"))
        self.btn_clear.setFixedHeight(22)
        self.btn_clear.clicked.connect(self.clear)
        header.addWidget(self.btn_clear)
        layout.addLayout(header)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName(t("notifications_title"))
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget, 1)

    @Slot(str, str)
    def record(self, text: str, level: str = "info") -> None:
        """Record a notification entry.

        Args:
            text: Notification message.
            level: One of 'info', 'warning', 'error', 'success'.
        """
        now = datetime.now().strftime("%H:%M:%S")
        entry = {"time": now, "text": text, "level": level}
        self._entries.append(entry)

        # Trim old entries
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries = self._entries[-self.MAX_ENTRIES :]
            self.list_widget.takeItem(0)

        # Level icons and colors
        level_map = {
            "info": ("", QColor("#4a9eff")),
            "warning": ("", QColor("#f5a623")),
            "error": ("", QColor("#ef5350")),
            "success": ("", QColor("#4caf50")),
        }
        icon, color = level_map.get(level, ("", QColor("#888")))

        item = QListWidgetItem(f"[{now}] {icon} {text}")
        item.setForeground(color)
        item.setToolTip(f"{level.upper()} at {now}\n{text}")
        self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()

        self.count_label.setText(str(len(self._entries)))

    @Slot()
    def clear(self) -> None:
        """Clear all notification history."""
        self._entries.clear()
        self.list_widget.clear()
        self.count_label.setText("0")

    @property
    def entries(self) -> list[dict]:
        """Return all recorded entries."""
        return list(self._entries)

    def entry_count(self) -> int:
        """Return number of recorded entries."""
        return len(self._entries)
