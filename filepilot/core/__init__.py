"""Core FilePilot services with lazy imports.

Keeping this package initializer lazy lets MCP-only installs import
`filepilot.core` without immediately importing Qt-backed modules.
"""

from __future__ import annotations

from typing import Any

_EXPORTS = {
    "DEFAULTS": ("filepilot.core.config", "DEFAULTS"),
    "DuplicateFinder": ("filepilot.core.duplicate_finder", "DuplicateFinder"),
    "FileIndexer": ("filepilot.core.indexer", "FileIndexer"),
    "FileInfo": ("filepilot.core.file_scanner", "FileInfo"),
    "FileOrganizer": ("filepilot.core.file_organizer", "FileOrganizer"),
    "FileScanner": ("filepilot.core.file_scanner", "FileScanner"),
    "FileWatcher": ("filepilot.core.file_watcher", "FileWatcher"),
    "OrganizeRule": ("filepilot.core.file_organizer", "OrganizeRule"),
    "Task": ("filepilot.core.task_queue", "Task"),
    "TaskPriority": ("filepilot.core.task_queue", "TaskPriority"),
    "TaskQueueWorker": ("filepilot.core.task_queue", "TaskQueueWorker"),
    "TaskState": ("filepilot.core.task_queue", "TaskState"),
    "cache_results": ("filepilot.core.search_cache", "cache_results"),
    "clear_search_cache": ("filepilot.core.search_cache", "clear_search_cache"),
    "get_cache_stats": ("filepilot.core.search_cache", "get_cache_stats"),
    "get_cached_results": ("filepilot.core.search_cache", "get_cached_results"),
    "load_config": ("filepilot.core.config", "load"),
    "save_config": ("filepilot.core.config", "save"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    import importlib

    module_name, attr_name = _EXPORTS[name]
    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
