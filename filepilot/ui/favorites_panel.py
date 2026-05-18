"""Favorites panel — quick access to saved directories"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.ui.base_panel import BasePanel


class FavoritesPanel(BasePanel):
    """Favorites panel — quick access to saved directories"""

    navigate_to_directory = Signal(str)

    def __init__(
        self, app_state: AppState | None = None, event_bus: EventBus | None = None, parent=None
    ):
        super().__init__(parent)
        self.state = app_state
        self.event_bus = event_bus
        self.favorites: list[dict] = []
        self._current_dir: str | None = None
        self._load_favorites()
        self._setup_ui()
        self._connect_signals()

    # ── Public API ───────────────────────────────────────────────

    def set_current_dir(self, dir_path: str | None) -> None:
        """Update the known current directory (called by MainWindow)."""
        self._current_dir = dir_path
        self._update_add_button_state()

    def refresh(self) -> None:
        """Reload favorites from settings (e.g., after external changes)."""
        self._load_favorites()
        self._rebuild_list()

    def contains_path(self, path: str) -> bool:
        """Check if a path is already in favorites."""
        return any(fav["path"] == path for fav in self.favorites)

    # ── Setup ────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Title
        title = QLabel("⭐ Favorites")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel("Save frequently used directories for quick access.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("+ Add Current Directory")
        self.btn_add.setToolTip("Add the currently open directory to favorites")
        self.btn_remove = QPushButton("🗑 Remove Selected")
        self.btn_remove.setToolTip("Remove the selected favorite")
        self.btn_remove.setEnabled(False)
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_remove)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Favorites list
        self.fav_list = QListWidget()
        self.fav_list.setAlternatingRowColors(True)
        self.fav_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.fav_list.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self.fav_list, stretch=1)

        # Stats
        layout.addWidget(self._make_stat_card("Favorites", "0"))

        # Build the list
        self._rebuild_list()

    def _connect_signals(self) -> None:
        self.btn_add.clicked.connect(self._on_add)
        self.btn_remove.clicked.connect(self._on_remove_selected)
        self.fav_list.itemClicked.connect(self._on_item_clicked)
        self.fav_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.fav_list.customContextMenuRequested.connect(self._on_context_menu)
        self.fav_list.model().rowsMoved.connect(self._on_order_changed)

    # ── Data persistence ─────────────────────────────────────────

    def _load_favorites(self) -> None:
        if self.state:
            self.favorites = list(self.state.get("favorite_dirs", []))
        else:
            from filepilot.core import config

            self.favorites = list(config.load().get("favorite_dirs", []))

    def _save_favorites(self) -> None:
        if self.state:
            self.state.set("favorite_dirs", self.favorites)
            self.state.save()
        else:
            from filepilot.core import config

            settings = config.load()
            settings["favorite_dirs"] = self.favorites
            config.save(settings)

    # ── UI helpers ───────────────────────────────────────────────

    def _rebuild_list(self) -> None:
        self.fav_list.clear()
        for fav in self.favorites:
            name = fav.get("name", Path(fav["path"]).name)
            path = fav["path"]
            item = QListWidgetItem(f"📁  {name}")
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            item.setSizeHint(QSize(0, 36))
            self.fav_list.addItem(item)

        self._update_stat("Favorites", str(len(self.favorites)))

    def _update_add_button_state(self) -> None:
        """Enable/disable the Add button based on whether current dir is already a favorite."""
        if self._current_dir:
            self.btn_add.setEnabled(not self.contains_path(self._current_dir))
        else:
            self.btn_add.setEnabled(False)

    # ── Slots ────────────────────────────────────────────────────

    @Slot()
    def _on_add(self) -> None:
        """Add current directory to favorites."""
        if not self._current_dir:
            self.status_message.emit("No directory is currently open.")
            return

        path = self._current_dir

        if self.contains_path(path):
            self.status_message.emit("This directory is already in favorites.")
            return

        if not Path(path).is_dir():
            self.status_message.emit("Directory no longer exists.")
            return

        self.favorites.append(
            {
                "name": Path(path).name,
                "path": path,
            }
        )
        self._save_favorites()
        self._rebuild_list()
        self._update_add_button_state()
        self.status_message.emit(f"Added to favorites: {Path(path).name}")

    @Slot()
    def _on_remove_selected(self) -> None:
        """Remove selected favorite(s)."""
        selected = self.fav_list.selectedItems()
        if not selected:
            return

        paths_to_remove = {item.data(Qt.UserRole) for item in selected}
        self.favorites = [fav for fav in self.favorites if fav["path"] not in paths_to_remove]
        self._save_favorites()
        self._rebuild_list()
        self._update_add_button_state()
        count = len(paths_to_remove)
        self.status_message.emit(f"Removed {count} favorite{'s' if count > 1 else ''}.")

    @Slot()
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Navigate to the selected favorite directory."""
        path = item.data(Qt.UserRole)
        if not Path(path).is_dir():
            QMessageBox.warning(
                self,
                "Directory Not Found",
                f"The directory no longer exists:\n{path}\n\nRemove it from favorites?",
            )
            # Offer to remove
            self.favorites = [fav for fav in self.favorites if fav["path"] != path]
            self._save_favorites()
            self._rebuild_list()
            self._update_add_button_state()
            return

        self.navigate_to_directory.emit(path)
        if self.event_bus:
            self.event_bus.open_folder_requested.emit(path)

    @Slot()
    def _on_selection_changed(self) -> None:
        self.btn_remove.setEnabled(len(self.fav_list.selectedItems()) > 0)

    @Slot()
    def _on_context_menu(self, pos) -> None:
        """Right-click context menu."""
        item = self.fav_list.itemAt(pos)
        if not item:
            return

        self.fav_list.setCurrentItem(item)
        menu = QMenu(self)
        remove_action = menu.addAction(f"🗑 Remove '{item.text()}'")
        remove_action.triggered.connect(self._on_remove_selected)
        menu.exec(self.fav_list.viewport().mapToGlobal(pos))

    @Slot()
    def _on_order_changed(self) -> None:
        """Save the new order after drag-and-drop reordering."""
        new_order: list[dict] = []
        for i in range(self.fav_list.count()):
            item = self.fav_list.item(i)
            path = item.data(Qt.UserRole)
            # Find the matching favorite
            for fav in self.favorites:
                if fav["path"] == path:
                    new_order.append(fav)
                    break
        if new_order:
            self.favorites = new_order
            self._save_favorites()
