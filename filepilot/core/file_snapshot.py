"""File Snapshot — records file metadata before moves/deletes for history tracking.

Stores a history of file operations (move, rename, delete) in SQLite
so users can answer "where was this file before?" or undo operations.
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("filepilot.file_snapshot")

SNAPSHOT_DB = Path.home() / ".filepilot" / "file_history.db"


class FileSnapshot:
    """Records file operation history for undo and tracking.

    Tracks:
    - File moves (source -> destination)
    - File renames (old name -> new name)
    - File deletions (path + metadata at time of deletion)
    """

    MAX_ENTRIES = 5000

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else SNAPSHOT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        conn: sqlite3.Connection = self._local.conn
        return conn

    def _init_db(self):
        conn = self._conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS file_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                source_path TEXT NOT NULL,
                dest_path TEXT DEFAULT '',
                file_name TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                file_ext TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}'
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_source ON file_history(source_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_name ON file_history(file_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON file_history(timestamp DESC)")
        conn.commit()

    def record_move(self, source: str | Path, destination: str | Path) -> None:
        """Record a file move operation."""
        src = Path(source)
        dst = Path(destination)
        self._insert(
            operation="move",
            source_path=str(src),
            dest_path=str(dst),
            file_name=src.name,
            file_size=dst.stat().st_size if dst.exists() else 0,
            file_ext=src.suffix.lower(),
        )

    def record_rename(self, old_path: str | Path, new_path: str | Path) -> None:
        """Record a file rename operation."""
        old = Path(old_path)
        new = Path(new_path)
        self._insert(
            operation="rename",
            source_path=str(old),
            dest_path=str(new),
            file_name=old.name,
            file_size=new.stat().st_size if new.exists() else 0,
            file_ext=old.suffix.lower(),
            metadata=json.dumps({"old_name": old.name, "new_name": new.name}),
        )

    def record_delete(self, file_path: str | Path, file_size: int = 0) -> None:
        """Record a file deletion."""
        path = Path(file_path)
        self._insert(
            operation="delete",
            source_path=str(path),
            dest_path="",
            file_name=path.name,
            file_size=file_size or (path.stat().st_size if path.exists() else 0),
            file_ext=path.suffix.lower(),
        )

    def record_organize(
        self, source: str | Path, destination: str | Path, category: str = ""
    ) -> None:
        """Record a file organization (categorized move)."""
        src = Path(source)
        dst = Path(destination)
        self._insert(
            operation="organize",
            source_path=str(src),
            dest_path=str(dst),
            file_name=src.name,
            file_size=dst.stat().st_size if dst.exists() else 0,
            file_ext=src.suffix.lower(),
            metadata=json.dumps({"category": category}),
        )

    def find_previous_location(self, file_name: str) -> list[dict]:
        """Find where a file was previously located.

        Args:
            file_name: The filename to search for.

        Returns:
            List of history entries showing previous locations.
        """
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM file_history WHERE file_name = ? "
            "ORDER BY timestamp DESC, id DESC LIMIT 20",
            (file_name,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def find_by_path(self, path: str) -> list[dict]:
        """Find all operations involving a specific path."""
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM file_history WHERE source_path = ? OR dest_path = ? "
            "ORDER BY timestamp DESC, id DESC LIMIT 20",
            (path, path),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Get recent file operations."""
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM file_history ORDER BY timestamp DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_deletions(self, limit: int = 50) -> list[dict]:
        """Get recent file deletions."""
        conn = self._conn()
        cursor = conn.execute(
            "SELECT * FROM file_history WHERE operation = 'delete' "
            "ORDER BY timestamp DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Total number of recorded operations."""
        conn = self._conn()
        result = conn.execute("SELECT COUNT(*) FROM file_history").fetchone()
        return result[0] if result else 0

    def clear(self) -> None:
        """Clear all history."""
        conn = self._conn()
        conn.execute("DELETE FROM file_history")
        conn.commit()

    def _insert(
        self,
        operation: str,
        source_path: str,
        dest_path: str,
        file_name: str,
        file_size: int = 0,
        file_ext: str = "",
        metadata: str = "{}",
    ) -> None:
        """Insert a history record."""
        conn = self._conn()
        conn.execute(
            """
            INSERT INTO file_history
                (timestamp, operation, source_path, dest_path, file_name, file_size, file_ext, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                operation,
                source_path,
                dest_path,
                file_name,
                file_size,
                file_ext,
                metadata,
            ),
        )
        conn.commit()
        self._prune_if_needed()

    def _prune_if_needed(self) -> None:
        """Remove oldest entries if over MAX_ENTRIES."""
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM file_history").fetchone()[0]
        if count > self.MAX_ENTRIES:
            excess = count - self.MAX_ENTRIES
            conn.execute(
                "DELETE FROM file_history WHERE id IN "
                "(SELECT id FROM file_history ORDER BY timestamp ASC, id ASC LIMIT ?)",
                (excess,),
            )
            conn.commit()
