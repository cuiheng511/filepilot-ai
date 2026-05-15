"""Shortcut editor — customizable keyboard shortcuts for panel navigation."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

DEFAULT_SHORTCUTS: dict[str, str] = {
    "File Browser": "Ctrl+1",
    "File Search": "Ctrl+2",
    "File Organizer": "Ctrl+3",
    "Duplicate Finder": "Ctrl+4",
    "AI Summary": "Ctrl+5",
    "File Index": "Ctrl+6",
    "Favorites": "Ctrl+7",
}


class ShortcutEditor(QWidget):
    """A widget for customizing keyboard shortcuts.

    Displays a table of actions and their keyboard shortcuts. Users can
    click on a shortcut cell and press a new key combination to rebind it.
    Conflicts are highlighted in real-time.
    """

    shortcuts_changed = Signal(dict)

    def __init__(self, overrides: dict[str, str] | None = None, parent=None):
        super().__init__(parent)
        self._overrides = dict(overrides) if overrides else {}
        self._rows: list[tuple[str, QKeySequenceEdit]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the editor UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Info label
        info = QLabel(
            "Click a shortcut and press the desired key combination to rebind.\n"
            "Press Escape to cancel editing, Backspace/Delete to clear a shortcut."
        )
        info.setStyleSheet("color: #888; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)

        # Populate rows
        actions = list(DEFAULT_SHORTCUTS.keys())
        for i, action in enumerate(actions):
            self.table.insertRow(i)

            # Action name column
            name_item = QTableWidgetItem(action)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, name_item)

            # Shortcut editor column
            effective_key = self._overrides.get(action, DEFAULT_SHORTCUTS[action])
            kse = QKeySequenceEdit(QKeySequence(effective_key))
            kse.setObjectName(action)
            kse.setMaximumWidth(200)
            kse.keySequenceChanged.connect(self._on_key_sequence_changed)
            kse.editingFinished.connect(self._on_editing_finished)
            self.table.setCellWidget(i, 1, kse)
            self._rows.append((action, kse))

        self.table.setRowHeight(0, 36)
        layout.addWidget(self.table, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        hint_label = QLabel("")
        hint_label.setObjectName("conflictHint")
        hint_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        btn_layout.addWidget(hint_label, 1)

        reset_btn = QPushButton("↺ Reset to Defaults")
        reset_btn.setObjectName("btnResetShortcuts")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(reset_btn)

        layout.addLayout(btn_layout)

    def _on_key_sequence_changed(self, seq: QKeySequence) -> None:
        """Validate shortcuts and highlight conflicts in real-time."""
        kse = self.sender()
        if kse is None:
            return  # type: ignore[unreachable]
        action = kse.objectName()
        key_text = seq.toString()

        # Check for conflicts with other actions
        has_conflict = False
        for other_action, other_kse in self._rows:
            if other_action == action:
                continue
            if key_text and other_kse.keySequence().toString() == key_text:
                other_kse.setStyleSheet(
                    "QKeySequenceEdit { background-color: #5c1a1a; border: 1px solid #e74c3c; }"
                )
                has_conflict = True
            else:
                other_kse.setStyleSheet("")

        # Highlight current if conflict
        if has_conflict:
            kse.setStyleSheet(
                "QKeySequenceEdit { background-color: #5c1a1a; border: 1px solid #e74c3c; }"
            )
        else:
            kse.setStyleSheet("")

        # Update hint label
        hint = self.findChild(QLabel, "conflictHint")
        if hint:
            if has_conflict:
                hint.setText("⚠️ Conflict: Multiple actions have the same shortcut")
            else:
                hint.setText("")

    def _on_editing_finished(self) -> None:
        """Store the override when editing is complete."""
        kse = self.sender()
        if kse is None:
            return  # type: ignore[unreachable]
        action = kse.objectName()
        key_text = kse.keySequence().toString()

        # Store override only if it differs from default
        default_key = DEFAULT_SHORTCUTS.get(action, "")
        if key_text and key_text != default_key:
            self._overrides[action] = key_text
        else:
            self._overrides.pop(action, None)

        self.shortcuts_changed.emit(self._overrides)

    def _reset_defaults(self) -> None:
        """Reset all shortcuts to their default values."""
        self._overrides.clear()
        for action, kse in self._rows:
            default_key = DEFAULT_SHORTCUTS.get(action, "")
            kse.setKeySequence(QKeySequence(default_key))
            kse.setStyleSheet("")

        hint = self.findChild(QLabel, "conflictHint")
        if hint:
            hint.setText("")

        self.shortcuts_changed.emit(self._overrides)

    def get_overrides(self) -> dict[str, str]:
        """Return the current shortcut overrides dict."""
        return dict(self._overrides)
