"""File Organizer — Auto-categorize, smart rename"""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from filepilot.core.file_scanner import FileInfo
from filepilot.utils.file_utils import FileCategory, safe_filename


@dataclass
class OrganizeRule:
    """Organize rule"""
    name: str
    enabled: bool = True

    def apply(self, file_info: FileInfo) -> str | None:
        """Return target subdirectory name, None means no match"""
        raise NotImplementedError


class CategoryRule(OrganizeRule):
    """Organize by file category"""
    category_map: dict[FileCategory, str] = {
        FileCategory.DOCUMENT: "Documents",
        FileCategory.IMAGE: "Images",
        FileCategory.VIDEO: "Videos",
        FileCategory.AUDIO: "Audio",
        FileCategory.CODE: "Code",
        FileCategory.ARCHIVE: "Archives",
        FileCategory.PDF: "PDF",
        FileCategory.MARKDOWN: "Markdown",
        FileCategory.SPREADSHEET: "Spreadsheets",
        FileCategory.PRESENTATION: "Presentations",
        FileCategory.DATA: "Data",
        FileCategory.EXECUTABLE: "Executables",
        FileCategory.FONT: "Fonts",
        FileCategory.UNKNOWN: "Other",
    }

    def __init__(self):
        super().__init__("By Type")

    def apply(self, file_info: FileInfo) -> str | None:
        return self.category_map.get(file_info.category, "Other")


class DateRule(OrganizeRule):
    """Organize by date (year/month)"""

    def __init__(self):
        super().__init__("By Date")

    def apply(self, file_info: FileInfo) -> str | None:
        dt = file_info.modified_time
        return f"{dt.year}/{dt.month:02d}"


class ExtensionRule(OrganizeRule):
    """Organize by extension"""

    def __init__(self):
        super().__init__("By Extension")

    def apply(self, file_info: FileInfo) -> str | None:
        ext = file_info.extension.lstrip(".").upper()
        return ext if ext else "NO_EXT"


class SizeRule(OrganizeRule):
    """Organize by file size"""

    def __init__(self):
        super().__init__("By Size")

    def apply(self, file_info: FileInfo) -> str | None:
        size = file_info.size_bytes
        if size < 1024:
            return "<1KB"
        elif size < 100 * 1024:
            return "1KB-100KB"
        elif size < 1024 * 1024:
            return "100KB-1MB"
        elif size < 100 * 1024 * 1024:
            return "1MB-100MB"
        else:
            return ">100MB"


class FileOrganizer:
    """File organizer"""

    def __init__(self, rules: list[OrganizeRule] | None = None):
        self.rules = rules or [CategoryRule()]
        self._organized_count = 0
        self._errors: list[tuple[str, str]] = []
        self._undo_log: list[dict] = []  # Undo log

    def organize(
        self,
        files: list[FileInfo],
        target_root: str | Path,
        rules: list[OrganizeRule] | None = None,
        preview: bool = True,
        rename: bool = False,
        rename_pattern: str | None = None,
        dry_run: bool = True,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[dict]:
        """Organize files into target directory

        Args:
            files: List of files
            target_root: Target root directory
            rules: List of organization rules
            preview: Preview mode (don't actually move)
            rename: Whether to rename files
            rename_pattern: Rename template
            dry_run: Whether to preview only (no execution)
            progress_callback: Progress callback

        Returns:
            List of operation records
        """
        rules = rules or self.rules
        target = Path(target_root)
        operations: list[dict] = []
        self._organized_count = 0
        self._errors = []

        for i, file_info in enumerate(files):
            try:
                # Determine target subdirectory
                sub_dir = self._determine_target(file_info, rules)
                dest_dir = target / sub_dir if sub_dir else target

                # Determine target filename
                dest_name = self._determine_filename(file_info, rename, rename_pattern)
                dest_path = dest_dir / dest_name

                # Handle name conflicts
                dest_path = self._resolve_conflict(dest_path)

                op = {
                    "source": str(file_info.path),
                    "destination": str(dest_path),
                    "category": file_info.category.label,
                    "size": file_info.size_str,
                    "dry_run": dry_run,
                }
                operations.append(op)

                if not dry_run:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_info.path), str(dest_path))
                    self._organized_count += 1
                    self._undo_log.append({"source": str(file_info.path), "dest": str(dest_path)})

                if progress_callback:
                    progress_callback(i + 1, file_info.name)

            except (OSError, shutil.Error) as e:
                self._errors.append((file_info.name, str(e)))

        return operations

    def _determine_target(self, file_info: FileInfo, rules: list[OrganizeRule]) -> str:
        """Determine target subdirectory based on rules"""
        parts = []
        for rule in rules:
            if rule.enabled:
                result = rule.apply(file_info)
                if result:
                    parts.append(result)
        return "/".join(parts) if parts else ""

    def _determine_filename(
        self,
        file_info: FileInfo,
        rename: bool,
        pattern: str | None,
    ) -> str:
        """Determine target filename"""
        if not rename or not pattern:
            return file_info.name

        # Supported rename variables:
        # {name} - Original filename
        # {date} - Modified date (YYYY-MM-DD)
        # {time} - Modified time (HHMMSS)
        # {ext} - Extension
        # {idx} - Index number
        # {category} - File category
        dt = file_info.modified_time
        vars_map = {
            "name": file_info.path.stem,
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H%M%S"),
            "ext": file_info.extension.lstrip("."),
            "category": file_info.category.label,
        }

        new_name = pattern
        for key, value in vars_map.items():
            new_name = new_name.replace(f"{{{key}}}", safe_filename(value))

        return safe_filename(new_name) + file_info.extension

    def _resolve_conflict(self, path: Path) -> Path:
        """Handle filename conflicts by adding numeric suffix"""
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1

        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    @property
    def stats(self) -> dict:
        return {
            "organized_count": self._organized_count,
            "errors": len(self._errors),
        }

    def save_undo_log(self, path: str | Path) -> None:
        """Save undo log to file"""
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._undo_log, f, ensure_ascii=False, indent=2)

    def undo(self, undo_log_path: str | Path) -> dict:
        """Undo file operations based on undo log

        Returns:
            {"restored": int, "errors": int}
        """
        import json
        with open(undo_log_path, encoding="utf-8") as f:
            entries = json.load(f)

        restored = 0
        errors = 0
        for entry in entries:
            dest = Path(entry["dest"])
            source = Path(entry["source"])
            try:
                if dest.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dest), str(source))
                    restored += 1
                else:
                    errors += 1
            except (OSError, shutil.Error):
                errors += 1

        return {"restored": restored, "errors": errors}
