"""Theme Manager — Loads QSS stylesheets with hot-reload support

Usage:
    themes_dir = Path(__file__).parent / \"styles\" / \"themes\"
    mgr = ThemeManager(themes_dir)
    mgr.apply_theme(\"dark\")       # applies dark.qss globally
    mgr.apply_theme(\"light\")      # applies light.qss globally

Hot-reload:
    Edit any .qss file in the themes directory and the styles
    are automatically re-applied via QFileSystemWatcher.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, Signal, Slot


class ThemeManager(QObject):
    """Manage Qt Stylesheet (.qss) loading, theme switching, and hot-reload.

    Signals:
        theme_changed(str):  Emitted with the new theme name after apply.
        styles_reloaded():   Emitted after a hot-reload detects a .qss file change.
    """

    theme_changed = Signal(str)
    styles_reloaded = Signal()

    def __init__(
        self,
        themes_dir: str | Path,
        initial_theme: str = "dark",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._themes_dir = Path(themes_dir)
        self._current_theme: str = initial_theme
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)

    # ── Public API ──────────────────────────────────────────────────────

    def apply_theme(self, name: str) -> bool:
        """Load *name*.qss from themes dir and apply it to QApplication.

        Returns ``True`` on success, ``False`` if the file is missing or
        the application instance is not yet available.
        """
        qss_path = self._themes_dir / f"{name}.qss"
        if not qss_path.exists():
            return False

        try:
            qss = qss_path.read_text(encoding="utf-8")
        except OSError:
            return False

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return False

        app.setStyleSheet(qss)  # type: ignore[attr-defined]
        self._current_theme = name
        self.theme_changed.emit(name)

        # Watch the current file for hot-reload
        self._watcher.addPath(str(qss_path))

        return True

    def reload_current(self) -> bool:
        """Re-apply the current theme (useful after manual edits)."""
        return self.apply_theme(self._current_theme)

    def toggle(self) -> str:
        """Switch between ``\"dark\"`` and ``\"light\"`` and return the new name."""
        new = "light" if self._current_theme == "dark" else "dark"
        self.apply_theme(new)
        return new

    @property
    def current_theme(self) -> str:
        """Name of the currently active theme (e.g. ``\"dark\"``)."""
        return self._current_theme

    @property
    def themes_dir(self) -> Path:
        """Directory that contains the ``.qss`` theme files."""
        return self._themes_dir

    def available_themes(self) -> list[str]:
        """List theme names (``.qss`` file stems) found in the themes directory."""
        return sorted(p.stem for p in self._themes_dir.glob("*.qss"))

    # ── Slots ────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_file_changed(self, path: str) -> None:
        """Hot-reload: re-apply the current theme when the .qss file changes on disk."""
        # QFileSystemWatcher sometimes forgets the path; re-add it.
        if self.apply_theme(self._current_theme):
            self.styles_reloaded.emit()
