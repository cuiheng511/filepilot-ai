"""BasePanel — Base class for all feature panels

Provides shared signals, cancel operation support, and stat card methods.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class BasePanel(QWidget):
    """Base class for all feature panels, providing shared signals and common methods."""

    # === Shared Signals ===
    status_message = Signal(str)
    progress_updated = Signal(int)
    progress_text = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Cancel operation support
        self._cancelled: bool = False

        # Cancel button (added by subclasses to their layouts)
        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self._cancelling: bool = False

        # Stat card dict (only panels using _make_stat_card need to initialize)
        self.stat_cards: dict[str, QLabel] = {}

    # ── Cancel Operations ──────────────────────────────────────────────

    def reset_cancel(self) -> None:
        """Call before starting a new operation to clear the cancel flag."""
        self._cancelled = False

    @Slot()
    def _on_cancel(self) -> None:
        """Cancel the current operation (sets flag, overridden by subclasses)."""
        self._cancelled = True
        self.status_message.emit("⏹️ Cancelling...")

    @Slot()
    def _on_cancel_done(self) -> None:
        """Restore UI after cancellation (overridden by subclasses for their controls)."""
        self.btn_cancel.setVisible(False)
        # Safely hide progress bar (if exists)
        progress_bar = getattr(self, "progress_bar", None)
        if progress_bar is not None:
            progress_bar.setVisible(False)
        progress_label = getattr(self, "progress_label", None)
        if progress_label is not None:
            progress_label.setVisible(False)

    # ── Stat Cards ─────────────────────────────────────────────────────

    def _make_stat_card(self, title: str, value: str) -> QFrame:
        """Create a uniformly styled stat card."""
        card = QFrame()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        title_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        self.stat_cards[title] = value_label
        return card

    def _update_stat(self, title: str, value: str) -> None:
        """Update the value of a stat card."""
        if title in self.stat_cards:
            self.stat_cards[title].setText(str(value))
