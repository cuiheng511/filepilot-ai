"""Duplicate File Finder — Based on content hash and size"""

import hashlib
import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from filepilot.core.file_scanner import FileInfo

logger = logging.getLogger("filepilot.duplicates")


class DuplicateFinder:
    """Duplicate file finder"""

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
        """Find duplicate files

        Algorithm:
        1. Group by file size (fast filter)
        2. Compute partial hash for same-size files (first 64KB + last 64KB)
        3. Compute full hash for remaining candidates

        Args:
            files: List of files
            use_hash: Whether to use hash verification (otherwise size-only)
            min_size: Minimum file size (bytes)
            progress_callback: Progress callback

        Returns:
            Groups of duplicate files, each group has at least 2 files
        """
        if not files:
            return []

        # Step 1: Group by file size
        size_groups: defaultdict[int, list[FileInfo]] = defaultdict(list)
        for f in files:
            if f.size_bytes >= min_size and not f.is_directory:
                size_groups[f.size_bytes].append(f)

        # Filter groups with duplicate sizes
        potential_groups = [g for g in size_groups.values() if len(g) > 1]
        total = len(potential_groups)

        if not use_hash:
            self._potential_duplicates = potential_groups
            return potential_groups

        # Step 2: Compute partial hash for fast filtering
        hash_groups: defaultdict[str, list[FileInfo]] = defaultdict(list)
        for i, group in enumerate(potential_groups):
            for f in group:
                partial_hash = self._partial_hash(f.path)
                hash_groups[partial_hash].append(f)

            if progress_callback:
                progress_callback(i + 1, f"Verifying hash... {i + 1}/{total}")

        # Filter groups with same partial hash
        still_potential = [g for g in hash_groups.values() if len(g) > 1]

        # Step 3: Compute full hash for final verification
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
        """Find near-duplicate files by name similarity

        Args:
            files: List of files
            threshold: Similarity threshold 0.0-1.0

        Returns:
            Similar file groups
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
                    continue  # Same size files don't count as "similar"
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
        """Compute partial file hash (first and last sample_size bytes each)

        When file size <= 2 * sample_size, head and tail may overlap,
        so a length prefix is used to avoid collisions.
        """
        hasher = hashlib.sha256()
        try:
            file_size = file_path.stat().st_size
            hasher.update(file_size.to_bytes(8, 'big'))  # Length prefix
            with open(file_path, "rb") as f:
                head = f.read(sample_size)
                hasher.update(head)
                if file_size > sample_size:
                    f.seek(-sample_size, 2)
                    tail = f.read(sample_size)
                    hasher.update(tail)
        except (OSError, PermissionError) as e:
            logger.debug("Partial hash failed for %s: %s", file_path, e)
        return hasher.hexdigest()

    def _full_hash(self, file_path: Path) -> str:
        """Compute full file SHA256 hash"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
        except (OSError, PermissionError) as e:
            logger.debug("Full hash failed for %s: %s", file_path, e)
            pass
        return hasher.hexdigest()

    def get_duplicate_stats(self, groups: list[list[FileInfo]]) -> dict:
        """Get duplicate file statistics"""
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
        """Format byte size"""
        from filepilot.utils.file_utils import get_file_size_str
        return get_file_size_str(size)
