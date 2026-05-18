"""Centralized application state with change signals.

Replaces the raw settings dict pattern used across the codebase.
Emits typed signals when state changes so UI components can react.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from filepilot.core.config import DEFAULTS, add_recent_file, get_recent_files


def _get_list(settings: dict, key: str) -> list:
    return list(settings.get(key) or [])


def _get_dict(settings: dict, key: str) -> dict:
    return dict(settings.get(key) or {})


class AppState(QObject):
    """Centralized application state with change signals."""

    settings_changed = Signal(dict)
    theme_changed = Signal(str)
    current_dir_changed = Signal(str)
    recent_dirs_changed = Signal(list)
    recent_files_changed = Signal(list)
    favorite_dirs_changed = Signal(list)
    search_history_changed = Signal(list)

    def __init__(self, settings: dict | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._settings: dict[str, Any] = dict(DEFAULTS)
        if settings:
            self._settings.update(settings)

    # ── Generic settings access ──

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value

    def update(self, other: dict) -> None:
        self._settings.update(other)

    @property
    def raw(self) -> dict:
        return self._settings

    # ── Typed accessors ──

    @property
    def theme(self) -> str:
        return str(self._settings.get("theme", "dark"))

    @theme.setter
    def theme(self, value: str) -> None:
        self._settings["theme"] = value
        self.theme_changed.emit(value)

    @property
    def current_dir(self) -> str | None:
        val = self._settings.get("_current_dir")
        return str(val) if val else None

    @current_dir.setter
    def current_dir(self, value: str | None) -> None:
        self._settings["_current_dir"] = value
        if value:
            self.current_dir_changed.emit(value)

    @property
    def recent_dirs(self) -> list[str]:
        return _get_list(self._settings, "recent_dirs")

    def add_recent_dir(self, dir_path: str, max_entries: int = 10) -> None:
        recent = self.recent_dirs
        if dir_path in recent:
            recent.remove(dir_path)
        recent.insert(0, dir_path)
        self._settings["recent_dirs"] = recent[:max_entries]
        self.recent_dirs_changed.emit(self.recent_dirs)

    @property
    def recent_files(self) -> list[str]:
        return get_recent_files(self._settings)

    def add_recent_file(self, file_path: str | Path) -> None:
        self._settings = add_recent_file(self._settings, str(file_path))
        self.recent_files_changed.emit(self.recent_files)

    @property
    def favorite_dirs(self) -> list[str]:
        return _get_list(self._settings, "favorite_dirs")

    def set_favorite_dirs(self, dirs: list[str]) -> None:
        self._settings["favorite_dirs"] = list(dirs)
        self.favorite_dirs_changed.emit(self.favorite_dirs)

    @property
    def search_history(self) -> list[str]:
        return _get_list(self._settings, "search_history")

    def add_search_history(self, query: str, max_entries: int = 20) -> None:
        history = self.search_history
        if query in history:
            history.remove(query)
        history.insert(0, query)
        self._settings["search_history"] = history[:max_entries]
        self.search_history_changed.emit(self.search_history)

    @property
    def file_tags(self) -> dict:
        return _get_dict(self._settings, "file_tags")

    def set_file_tags(self, tags: dict) -> None:
        self._settings["file_tags"] = tags

    @property
    def file_browser_columns(self) -> list[str]:
        return _get_list(self._settings, "file_browser_columns")

    def set_file_browser_columns(self, columns: list[str]) -> None:
        self._settings["file_browser_columns"] = list(columns)

    @property
    def saved_searches(self) -> list[dict]:
        return _get_list(self._settings, "saved_searches")

    def set_saved_searches(self, searches: list[dict]) -> None:
        self._settings["saved_searches"] = list(searches)

    @property
    def tag_automation_rules(self) -> list[dict]:
        return _get_list(self._settings, "tag_automation_rules")

    def set_tag_automation_rules(self, rules: list[dict]) -> None:
        self._settings["tag_automation_rules"] = list(rules)

    @property
    def shortcuts(self) -> dict:
        return _get_dict(self._settings, "shortcuts")

    def set_shortcuts(self, shortcuts: dict) -> None:
        self._settings["shortcuts"] = dict(shortcuts)
        self.settings_changed.emit(self._settings)

    # ── Persistence ──

    def save(self) -> None:
        """Persist to disk."""
        from filepilot.core.config import save as _save

        _save(self._settings)
        self.settings_changed.emit(self._settings)

    def reload(self) -> None:
        """Reload from disk."""
        from filepilot.core.config import load as _load

        self._settings = _load()
        self.settings_changed.emit(self._settings)
