"""File Tag Manager — persistent tags with color markers and cross-directory search."""

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger("filepilot.tag_manager")

TAGS_FILE = Path.home() / ".filepilot" / "tags.json"

DEFAULT_COLORS = [
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
]


class TagManager:
    """Manages file tags with persistent storage and cross-directory search.

    Uses a deferred save strategy: writes are batched and flushed after a short
    delay (300ms) to avoid excessive disk I/O during bulk operations.
    """

    _SAVE_DELAY_MS = 300

    def __init__(self) -> None:
        self._tags: dict[str, dict] = {}
        self._dirty = False
        self._save_timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if TAGS_FILE.exists():
            try:
                self._tags = json.loads(TAGS_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load tags: %s", e)
                self._tags = {}

    def _save(self):
        """Immediate save to disk."""
        TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            TAGS_FILE.write_text(
                json.dumps(self._tags, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._dirty = False
        except Exception as e:
            logger.warning("Failed to save tags: %s", e)

    def _schedule_save(self):
        """Schedule a deferred save. Multiple rapid changes are batched."""
        self._dirty = True
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(self._SAVE_DELAY_MS / 1000.0, self._save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def flush(self):
        """Force immediate save if there are pending changes."""
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
        if self._dirty:
            self._save()

    def add_tag(self, file_path: str | Path, tag: str, color: str | None = None) -> None:
        path_str = str(Path(file_path).resolve())
        if path_str not in self._tags:
            self._tags[path_str] = {"tags": [], "color": color or DEFAULT_COLORS[0]}
        entry = self._tags[path_str]
        if tag.lower() not in [t.lower() for t in entry["tags"]]:
            entry["tags"].append(tag)
        if color:
            entry["color"] = color
        self._schedule_save()

    def remove_tag(self, file_path: str | Path, tag: str) -> None:
        path_str = str(Path(file_path).resolve())
        if path_str in self._tags:
            entry = self._tags[path_str]
            entry["tags"] = [t for t in entry["tags"] if t.lower() != tag.lower()]
            if not entry["tags"]:
                del self._tags[path_str]
            self._schedule_save()

    def get_tags(self, file_path: str | Path) -> list[str]:
        path_str = str(Path(file_path).resolve())
        if path_str in self._tags:
            return list(self._tags[path_str]["tags"])
        return []

    def get_color(self, file_path: str | Path) -> str | None:
        path_str = str(Path(file_path).resolve())
        if path_str in self._tags:
            return self._tags[path_str].get("color")
        return None

    def set_color(self, file_path: str | Path, color: str) -> None:
        path_str = str(Path(file_path).resolve())
        if path_str not in self._tags:
            self._tags[path_str] = {"tags": [], "color": color}
        else:
            self._tags[path_str]["color"] = color
        self._schedule_save()

    def has_tag(self, file_path: str | Path, tag: str) -> bool:
        path_str = str(Path(file_path).resolve())
        if path_str in self._tags:
            return tag.lower() in [t.lower() for t in self._tags[path_str]["tags"]]
        return False

    def find_by_tag(self, tag: str) -> list[str]:
        tag_lower = tag.lower()
        return [p for p, e in self._tags.items() if tag_lower in [t.lower() for t in e["tags"]]]

    def get_all_tags(self) -> list[str]:
        tags = set()
        for entry in self._tags.values():
            tags.update(entry["tags"])
        return sorted(tags)

    def get_tagged_files(self) -> dict[str, dict]:
        return dict(self._tags)

    def remove_file(self, file_path: str | Path) -> None:
        path_str = str(Path(file_path).resolve())
        if path_str in self._tags:
            del self._tags[path_str]
            self._schedule_save()

    def cleanup_nonexistent(self) -> int:
        to_remove = [p for p in self._tags if not Path(p).exists()]
        for p in to_remove:
            del self._tags[p]
        if to_remove:
            self._schedule_save()
        return len(to_remove)

    def get_tag_count(self) -> int:
        """Return the total number of unique tags."""
        return len(self.get_all_tags())
