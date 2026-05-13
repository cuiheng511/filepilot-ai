"""File Scanner — Recursively scan directories, identify file types"""

import logging
import mimetypes
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filepilot.utils.file_utils import (
    FileCategory,
    compute_file_hash,
    get_file_category,
    get_file_created_time,
    get_file_modified_time,
    get_file_size_str,
)

logger = logging.getLogger("filepilot.scanner")


@dataclass
class FileInfo:
    """File metadata information"""
    path: Path
    name: str
    extension: str
    size_bytes: int
    size_str: str
    category: FileCategory
    mime_type: str
    modified_time: datetime
    created_time: datetime
    is_directory: bool = False
    hash_sha256: str | None = None

    @property
    def relative_path(self, base_path: Path | None = None) -> str:
        """Get relative path"""
        if base_path:
            try:
                return str(self.path.relative_to(base_path))
            except ValueError:
                pass
        return str(self.path.name)


class FileScanner:
    """Recursive file scanner"""

    IGNORED_DIRS: set[str] = {
        "__pycache__", ".git", ".svn", ".hg",
        "node_modules", ".idea", ".vscode",
        "$RECYCLE.BIN", "System Volume Information",
    }
    IGNORED_EXTENSIONS: set[str] = {
        ".pyc", ".pyo", ".DS_Store", ".lnk",
    }
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500 MB

    def __init__(self, follow_symlinks: bool = False):
        self.follow_symlinks = follow_symlinks
        self._scanned_count = 0
        self._total_size = 0

    def scan(
        self,
        root_path: str | Path,
        recursive: bool = True,
        progress_callback: Callable[[int, str], None] | None = None,
        include_dirs: bool = False,
        include_hidden: bool = False,
        max_depth: int = -1,
    ) -> list[FileInfo]:
        """Scan directory and return file list

        Args:
            root_path: Root directory path
            recursive: Whether to scan subdirectories recursively
            progress_callback: Progress callback (current count, current file path)
            include_dirs: Whether to include directories themselves
            include_hidden: Whether to include hidden files/directories
            max_depth: Maximum recursion depth, -1 for unlimited
        """
        root = Path(root_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Path does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")

        results: list[FileInfo] = []
        self._scanned_count = 0
        self._total_size = 0

        for file_path in self._walk(root, recursive, include_hidden, max_depth):
            if file_path.is_dir():
                if include_dirs:
                    info = self._create_file_info(file_path)
                    results.append(info)
                continue

            # Skip ignored extensions
            if file_path.suffix.lower() in self.IGNORED_EXTENSIONS:
                continue

            # Skip files exceeding max size
            try:
                if file_path.stat().st_size > self.MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            try:
                info = self._create_file_info(file_path)
                results.append(info)
                self._scanned_count += 1
                self._total_size += info.size_bytes

                if progress_callback:
                    progress_callback(self._scanned_count, str(file_path))
            except (OSError, PermissionError) as e:
                logger.debug("Skipped %s: %s", file_path, e)
                continue

        return results

    def _walk(
        self,
        root: Path,
        recursive: bool,
        include_hidden: bool,
        max_depth: int,
        current_depth: int = 0,
    ) -> Iterator[Path]:
        """Walk directory tree"""
        if max_depth >= 0 and current_depth > max_depth:
            return

        try:
            entries = list(root.iterdir())
        except (OSError, PermissionError):
            return

        entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

        for entry in entries:
            # Skip hidden files/directories
            if not include_hidden and entry.name.startswith("."):
                continue

            # Skip ignored directories
            if entry.is_dir() and entry.name in self.IGNORED_DIRS:
                continue

            yield entry

            if entry.is_dir() and recursive and (self.follow_symlinks or not entry.is_symlink()):
                yield from self._walk(
                    entry, recursive, include_hidden, max_depth, current_depth + 1
                )

    def _create_file_info(self, file_path: Path) -> FileInfo:
        """Create FileInfo from file path"""
        stat = file_path.stat()
        extension = file_path.suffix.lower()
        category = get_file_category(file_path)
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return FileInfo(
            path=file_path,
            name=file_path.name,
            extension=extension,
            size_bytes=stat.st_size,
            size_str=get_file_size_str(stat.st_size),
            category=category,
            mime_type=mime_type or "application/octet-stream",
            modified_time=get_file_modified_time(file_path),
            created_time=get_file_created_time(file_path),
            is_directory=file_path.is_dir(),
        )

    def quick_scan(
        self,
        root_path: str | Path,
        max_files: int = 100,
        file_types: list[str] | None = None,
    ) -> list[FileInfo]:
        """Quick scan (limited file count), supports type filtering

        Args:
            root_path: Root directory
            max_files: Maximum file count
            file_types: File extension list, e.g. ['.pdf', '.md']
        """
        root = Path(root_path).resolve()
        results: list[FileInfo] = []

        for i, info in enumerate(self.scan(root)):
            if i >= max_files:
                break
            if file_types and info.extension not in file_types:
                continue
            results.append(info)

        return results

    def compute_hash(self, file_info: FileInfo) -> str:
        """Compute file hash (lazy evaluation)"""
        if file_info.hash_sha256 is None:
            file_info.hash_sha256 = compute_file_hash(file_info.path)
        return file_info.hash_sha256

    @property
    def stats(self) -> dict:
        """Return scan statistics"""
        return {
            "scanned_count": self._scanned_count,
            "total_size": self._total_size,
            "total_size_str": get_file_size_str(self._total_size),
        }
