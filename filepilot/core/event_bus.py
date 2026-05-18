"""Centralized event bus for cross-panel communication.

Replaces ad-hoc Signal connections scattered across main_window.py.
Panels can emit events and subscribe to events without knowing each other.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """Application-wide event bus for decoupled cross-panel communication.

    Usage:
        bus = EventBus()
        bus.open_folder_requested.connect(self._on_open_folder)
        bus.open_folder_requested.emit("/some/path")

    Note: connect/disconnect by name are intentionally omitted to avoid
    shadowing QObject's built-in methods. Use direct signal connections instead.
    """

    # Navigation
    open_folder_requested = Signal(str)
    open_file_requested = Signal(str)
    switch_panel_requested = Signal(str)  # panel key
    global_search_requested = Signal()

    # File operations
    file_tagged = Signal(str, list)  # file_path, tags
    file_untagged = Signal(str, list)
    files_deleted = Signal(list)
    files_moved = Signal(list, str)  # files, destination
    files_copied = Signal(list, str)

    # Indexing / scanning
    scan_requested = Signal(str)
    index_requested = Signal(str)
    scan_completed = Signal(str)  # dir_path
    index_completed = Signal(str)

    # Settings / state
    theme_toggled = Signal(bool)  # dark=True
    settings_applied = Signal(dict)

    # Dashboard refresh
    dashboard_refresh_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
