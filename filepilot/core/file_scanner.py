"""文件扫描器 — 递归扫描目录、识别文件类型"""

import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

from filepilot.utils.file_utils import (
    FileCategory,
    compute_file_hash,
    get_file_category,
    get_file_created_time,
    get_file_modified_time,
    get_file_size_str,
)


@dataclass
class FileInfo:
    """文件的元数据信息"""
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
        """获取相对路径"""
        if base_path:
            try:
                return str(self.path.relative_to(base_path))
            except ValueError:
                pass
        return str(self.path.name)


class FileScanner:
    """递归文件扫描器"""

    IGNORED_DIRS: set[str] = {
        "__pycache__", ".git", ".svn", ".hg",
        "node_modules", ".idea", ".vscode",
        "$RECYCLE.BIN", "System Volume Information",
    }
    IGNORED_EXTENSIONS: set[str] = {
        ".pyc", ".pyo", ".DS_Store", ".lnk",
    }
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB

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
        """扫描目录，返回文件列表

        Args:
            root_path: 根目录路径
            recursive: 是否递归扫描子目录
            progress_callback: 进度回调 (当前文件数, 当前文件路径)
            include_dirs: 是否包含目录本身
            include_hidden: 是否包含隐藏文件/目录
            max_depth: 最大递归深度，-1 表示不限
        """
        root = Path(root_path).resolve()
        if not root.exists():
            raise FileNotFoundError(f"路径不存在: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"不是目录: {root}")

        results: list[FileInfo] = []
        self._scanned_count = 0
        self._total_size = 0

        for file_path in self._walk(root, recursive, include_hidden, max_depth):
            if file_path.is_dir():
                if include_dirs:
                    info = self._create_file_info(file_path)
                    results.append(info)
                continue

            # 跳过忽略的扩展名
            if file_path.suffix.lower() in self.IGNORED_EXTENSIONS:
                continue

            try:
                info = self._create_file_info(file_path)
                results.append(info)
                self._scanned_count += 1
                self._total_size += info.size_bytes

                if progress_callback:
                    progress_callback(self._scanned_count, str(file_path))
            except (OSError, PermissionError):
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
        """遍历目录树"""
        if max_depth >= 0 and current_depth > max_depth:
            return

        try:
            entries = list(root.iterdir())
        except (OSError, PermissionError):
            return

        entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

        for entry in entries:
            # 跳过隐藏文件/目录
            if not include_hidden and entry.name.startswith("."):
                continue

            # 跳过忽略的目录
            if entry.is_dir() and entry.name in self.IGNORED_DIRS:
                continue

            yield entry

            if entry.is_dir() and recursive and (self.follow_symlinks or not entry.is_symlink()):
                yield from self._walk(
                    entry, recursive, include_hidden, max_depth, current_depth + 1
                )

    def _create_file_info(self, file_path: Path) -> FileInfo:
        """根据文件路径创建 FileInfo"""
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
        """快速扫描（限制文件数量），支持按类型过滤

        Args:
            root_path: 根目录
            max_files: 最大文件数
            file_types: 文件扩展名列表，如 ['.pdf', '.md']
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
        """计算文件哈希（惰性计算）"""
        if file_info.hash_sha256 is None:
            file_info.hash_sha256 = compute_file_hash(file_info.path)
        return file_info.hash_sha256

    @property
    def stats(self) -> dict:
        """返回扫描统计信息"""
        return {
            "scanned_count": self._scanned_count,
            "total_size": self._total_size,
            "total_size_str": get_file_size_str(self._total_size),
        }
