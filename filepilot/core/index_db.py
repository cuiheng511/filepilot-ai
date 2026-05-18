"""Metadata database — SQLite-backed file metadata storage.

Stores file metadata (path, name, size, timestamps, extension, category)
in SQLite for fast filtering. Full-text content search still uses Whoosh.
"""

import sqlite3
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from filepilot.core.file_scanner import FileInfo


class MetadataDB:
    """SQLite database for file metadata.

    Provides fast queries by type, size, date, and extension
    without going through Whoosh.
    """

    def __init__(self, db_path: str | Path = "~/.filepilot/file_meta.db"):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn  # type: ignore[no-any-return]

    def _init_db(self):
        conn = self._conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                modified_time TEXT,
                created_time TEXT,
                extension TEXT DEFAULT '',
                category TEXT DEFAULT 'Other'
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_extension ON files(extension)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON files(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_size ON files(size_bytes)")
        conn.commit()

    def insert_file(self, info: FileInfo):
        conn = self._conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO files
                (path, name, size_bytes, modified_time, created_time, extension, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(info.path),
                info.name,
                info.size_bytes,
                info.modified_time.isoformat() if info.modified_time else None,
                info.created_time.isoformat() if info.created_time else None,
                info.extension.lower(),
                info.category.label if info.category else "Other",
            ),
        )
        conn.commit()

    def bulk_insert(
        self, files: list[FileInfo], progress_callback: Callable[[int, str], None] | None = None
    ):
        conn = self._conn()
        rows = []
        for i, info in enumerate(files):
            rows.append(
                (
                    str(info.path),
                    info.name,
                    info.size_bytes,
                    info.modified_time.isoformat() if info.modified_time else None,
                    info.created_time.isoformat() if info.created_time else None,
                    info.extension.lower(),
                    info.category.label if info.category else "Other",
                )
            )
            if progress_callback and (i + 1) % 500 == 0:
                progress_callback(i + 1, f"Metadata: {i + 1}/{len(files)}")
        conn.executemany(
            """
            INSERT OR REPLACE INTO files
                (path, name, size_bytes, modified_time, created_time, extension, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()

    def search_metadata(
        self,
        category: str | None = None,
        extension: str | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        paths: set[str] | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """Search file metadata. Returns dicts compatible with indexer.search()."""
        conditions = []
        params: list = []

        if category and category != "All":
            conditions.append("category = ?")
            params.append(category)
        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            conditions.append("extension = ?")
            params.append(ext.lower())
        if size_min is not None:
            conditions.append("size_bytes >= ?")
            params.append(size_min)
        if size_max is not None:
            conditions.append("size_bytes < ?")
            params.append(size_max)
        if date_from:
            conditions.append("modified_time >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("modified_time <= ?")
            params.append(date_to)
        if paths:
            placeholders = ",".join("?" for _ in paths)
            conditions.append(f"path IN ({placeholders})")
            params.extend(paths)

        where = " AND ".join(conditions) if conditions else "1"
        conn = self._conn()
        cursor = conn.execute(
            f"SELECT path, name, size_bytes, modified_time, extension, category"
            f" FROM files WHERE {where} ORDER BY modified_time DESC LIMIT ?",
            params + [limit],
        )
        from filepilot.utils.file_utils import get_file_size_str

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "path": row["path"],
                    "filename": row["name"],
                    "extension": row["extension"],
                    "category": row["category"],
                    "size": row["size_bytes"],
                    "size_str": get_file_size_str(row["size_bytes"]),
                    "modified": self._format_dt_str(row["modified_time"]),
                    "score": 1.0,
                    "highlights": "",
                }
            )
        return results

    def get_by_path(self, path: str) -> dict | None:
        conn = self._conn()
        cursor = conn.execute("SELECT * FROM files WHERE path = ?", (path,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def remove(self, path: str):
        conn = self._conn()
        conn.execute("DELETE FROM files WHERE path = ?", (path,))
        conn.commit()

    def remove_prefix(self, prefix: str):
        conn = self._conn()
        safe = prefix.replace("%", r"\%").replace("_", r"\_")
        conn.execute(
            "DELETE FROM files WHERE path LIKE ? ESCAPE '\\'",
            (f"{safe}%",),
        )
        conn.commit()

    def clear(self):
        conn = self._conn()
        conn.execute("DELETE FROM files")
        conn.commit()

    def count(self) -> int:
        conn = self._conn()
        result = conn.execute("SELECT COUNT(*) FROM files").fetchone()
        return result[0] if result else 0

    def total_size(self) -> int:
        conn = self._conn()
        result = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM files").fetchone()
        return result[0] if result else 0

    def get_stats(self) -> dict:
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        total = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM files").fetchone()[0]
        from filepilot.utils.file_utils import get_file_size_str

        return {
            "indexed_files": count,
            "total_size": total,
            "total_size_str": get_file_size_str(total),
        }

    def _format_dt_str(self, dt_str: str | None) -> str:
        if not dt_str:
            return ""
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return dt_str or ""
