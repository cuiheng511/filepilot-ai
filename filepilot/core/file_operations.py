"""Shared file operation helpers for copy, move, and delete workflows."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from filepilot.utils.file_utils import resolve_path_conflict


@dataclass(frozen=True)
class FileOperationResult:
    """Result for one file operation."""

    source: Path
    destination: Path | None
    success: bool
    error: str = ""

    @property
    def renamed(self) -> bool:
        return self.destination is not None and self.destination.name != self.source.name


@dataclass(frozen=True)
class PlannedFileOperation:
    """A planned file operation before it is executed."""

    source: Path
    destination: Path

    @property
    def renamed(self) -> bool:
        return self.destination.name != self.source.name


@dataclass(frozen=True)
class FileOperationPreview:
    """Preview for a pending copy or move batch."""

    action: str
    destination_dir: Path
    operations: list[PlannedFileOperation]

    @property
    def renamed_count(self) -> int:
        return sum(1 for op in self.operations if op.renamed)

    def summary(self) -> str:
        verb = "copy" if self.action == "copy" else "move"
        message = f"Ready to {verb} {len(self.operations)} file"
        if len(self.operations) != 1:
            message += "s"
        message += f" to {self.destination_dir}"
        if self.renamed_count:
            message += f"\n{self.renamed_count} item"
            if self.renamed_count != 1:
                message += "s"
            message += " will be renamed to avoid overwriting existing files."
        return message

    def details(self, limit: int = 8) -> str:
        rows = []
        for op in self.operations[:limit]:
            rename_note = " (renamed)" if op.renamed else ""
            rows.append(f"{op.source.name} -> {op.destination.name}{rename_note}")
        remaining = len(self.operations) - limit
        if remaining > 0:
            rows.append(f"...and {remaining} more")
        return "\n".join(rows)


@dataclass(frozen=True)
class FileBatchResult:
    """Aggregate result for a copy or move batch."""

    action: str
    destination_dir: Path
    operations: list[FileOperationResult]

    @property
    def success_count(self) -> int:
        return sum(1 for op in self.operations if op.success)

    @property
    def error_count(self) -> int:
        return sum(1 for op in self.operations if not op.success)

    @property
    def renamed_count(self) -> int:
        return sum(1 for op in self.operations if op.success and op.renamed)

    @property
    def successful_operations(self) -> list[FileOperationResult]:
        return [op for op in self.operations if op.success]

    def status_message(self) -> str:
        verb_map = {"copy": "Copied", "move": "Moved", "trash": "Deleted"}
        verb = verb_map.get(self.action, self.action.title())
        message = f"{verb} {self.success_count} file{'s' if self.success_count != 1 else ''}"
        if self.error_count:
            message += f", {self.error_count} error{'s' if self.error_count != 1 else ''}"
        if self.renamed_count:
            message += f" ({self.renamed_count} renamed to avoid overwrite)"
        return message


class FileOperationService:
    """Plan and execute batch file operations with conflict-safe destinations."""

    def plan_destinations(
        self, sources: list[Path], destination_dir: Path
    ) -> list[tuple[Path, Path]]:
        reserved: set[Path] = set()
        planned: list[tuple[Path, Path]] = []
        for source in sources:
            target = resolve_path_conflict(destination_dir / source.name, reserved)
            reserved.add(target)
            planned.append((source, target))
        return planned

    def preview(
        self, action: str, sources: list[Path], destination_dir: Path
    ) -> FileOperationPreview:
        if action not in {"copy", "move"}:
            raise ValueError(f"Unsupported preview action: {action}")
        operations = [
            PlannedFileOperation(source, target)
            for source, target in self.plan_destinations(sources, destination_dir)
        ]
        return FileOperationPreview(action, destination_dir, operations)

    def copy(self, sources: list[Path], destination_dir: Path) -> FileBatchResult:
        return self._run("copy", sources, destination_dir)

    def move(self, sources: list[Path], destination_dir: Path) -> FileBatchResult:
        return self._run("move", sources, destination_dir)

    def trash(self, sources: list[Path]) -> FileBatchResult:
        operations: list[FileOperationResult] = []
        try:
            from send2trash import send2trash
        except ImportError as e:
            return FileBatchResult(
                "trash",
                Path(),
                [FileOperationResult(source, None, False, str(e)) for source in sources],
            )

        for source in sources:
            try:
                send2trash(str(source))
                operations.append(FileOperationResult(source, None, True))
            except Exception as e:
                operations.append(FileOperationResult(source, None, False, str(e)))
        return FileBatchResult("trash", Path(), operations)

    def _run(
        self,
        action: str,
        sources: list[Path],
        destination_dir: Path,
    ) -> FileBatchResult:
        destination_dir.mkdir(parents=True, exist_ok=True)
        operations: list[FileOperationResult] = []
        for source, target in self.plan_destinations(sources, destination_dir):
            try:
                if action == "copy":
                    if source.is_dir():
                        shutil.copytree(source, target)
                    else:
                        shutil.copy2(source, target)
                elif action == "move":
                    shutil.move(str(source), str(target))
                else:
                    raise ValueError(f"Unsupported file operation: {action}")
                operations.append(FileOperationResult(source, target, True))
            except Exception as e:
                operations.append(FileOperationResult(source, target, False, str(e)))
        return FileBatchResult(action, destination_dir, operations)
