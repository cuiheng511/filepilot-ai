"""重复文件查找器 — 基于内容哈希和大小"""

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Callable

from filepilot.core.file_scanner import FileInfo


class DuplicateFinder:
    """重复文件查找器"""

    def __init__(self):
        self._potential_duplicates: list[list[FileInfo]] = []
        self._exact_duplicates: list[list[FileInfo]] = []

    def find_duplicates(
        self,
        files: list[FileInfo],
        use_hash: bool = True,
        min_size: int = 1,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[list[FileInfo]]:
        """查找重复文件

        算法：
        1. 先按文件大小分组（快速过滤）
        2. 相同大小的文件计算部分哈希（前64KB + 后64KB）
        3. 仍相同的计算完整哈希

        Args:
            files: 文件列表
            use_hash: 是否使用哈希校验（否则仅按大小判断）
            min_size: 最小文件大小（字节）
            progress_callback: 进度回调

        Returns:
            重复文件分组列表，每组至少2个文件
        """
        if not files:
            return []

        # 第一步：按文件大小分组
        size_groups: defaultdict[int, list[FileInfo]] = defaultdict(list)
        for f in files:
            if f.size_bytes >= min_size and not f.is_directory:
                size_groups[f.size_bytes].append(f)

        # 筛选出有重复大小的组
        potential_groups = [g for g in size_groups.values() if len(g) > 1]
        total = len(potential_groups)

        if not use_hash:
            self._potential_duplicates = potential_groups
            return potential_groups

        # 第二步：计算部分哈希快速过滤
        hash_groups: defaultdict[str, list[FileInfo]] = defaultdict(list)
        for i, group in enumerate(potential_groups):
            for f in group:
                partial_hash = self._partial_hash(f.path)
                hash_groups[partial_hash].append(f)

            if progress_callback:
                progress_callback(i + 1, f"校验哈希... {i + 1}/{total}")

        # 筛选出部分哈希相同的组
        still_potential = [g for g in hash_groups.values() if len(g) > 1]

        # 第三步：计算完整哈希确认
        final_groups: list[list[FileInfo]] = []
        for group in still_potential:
            full_hash_groups: defaultdict[str, list[FileInfo]] = defaultdict(list)
            for f in group:
                full_hash = self._full_hash(f.path)
                full_hash_groups[full_hash].append(f)

            final_groups.extend(g for g in full_hash_groups.values() if len(g) > 1)

        self._exact_duplicates = final_groups
        return final_groups

    def find_similar_by_name(
        self,
        files: list[FileInfo],
        threshold: float = 0.8,
    ) -> list[list[FileInfo]]:
        """基于文件名相似度查找近似重复文件

        Args:
            files: 文件列表
            threshold: 相似度阈值 0.0-1.0

        Returns:
            相似文件分组
        """
        from difflib import SequenceMatcher

        groups: list[list[FileInfo]] = []
        used = set()

        for i, f1 in enumerate(files):
            if i in used:
                continue
            group = [f1]
            used.add(i)

            for j, f2 in enumerate(files):
                if j in used or i == j:
                    continue
                if f1.size_bytes == f2.size_bytes:
                    continue  # 大小相同的不算"近似"
                name1 = f1.path.stem.lower()
                name2 = f2.path.stem.lower()
                similarity = SequenceMatcher(None, name1, name2).ratio()
                if similarity >= threshold:
                    group.append(f2)
                    used.add(j)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _partial_hash(self, file_path: Path, sample_size: int = 65536) -> str:
        """计算文件部分哈希（头尾各 sample_size 字节）

        当文件大小 <= 2 * sample_size 时，head 和 tail 会重叠，
        因此用长度前缀区分，避免不同大小文件产生相同 hash。
        """
        hasher = hashlib.sha256()
        try:
            file_size = file_path.stat().st_size
            hasher.update(file_size.to_bytes(8, 'big'))  # 长度前缀
            with open(file_path, "rb") as f:
                head = f.read(sample_size)
                hasher.update(head)
                if file_size > sample_size:
                    f.seek(-sample_size, 2)
                    tail = f.read(sample_size)
                    hasher.update(tail)
        except (OSError, PermissionError):
            pass
        return hasher.hexdigest()

    def _full_hash(self, file_path: Path) -> str:
        """计算文件完整 SHA256 哈希"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
        except (OSError, PermissionError):
            pass
        return hasher.hexdigest()

    def get_duplicate_stats(self, groups: list[list[FileInfo]]) -> dict:
        """获取重复文件统计信息"""
        total_duplicates = sum(len(g) - 1 for g in groups)
        wasted_bytes = sum(
            sum(f.size_bytes for f in g) - g[0].size_bytes
            for g in groups
        )
        return {
            "groups": len(groups),
            "duplicate_files": total_duplicates,
            "wasted_space": wasted_bytes,
            "wasted_space_str": self._format_bytes(wasted_bytes),
        }

    def _format_bytes(self, size: int) -> str:
        """格式化字节数"""
        from filepilot.utils.file_utils import get_file_size_str
        return get_file_size_str(size)
