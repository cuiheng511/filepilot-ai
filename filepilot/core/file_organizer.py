"""文件整理器 — 自动归类、智能重命名"""

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from filepilot.core.file_scanner import FileInfo
from filepilot.utils.file_utils import FileCategory, safe_filename


@dataclass
class OrganizeRule:
    """组织规则"""
    name: str
    enabled: bool = True

    def apply(self, file_info: FileInfo) -> str | None:
        """返回目标子目录名，None 表示不匹配"""
        raise NotImplementedError


class CategoryRule(OrganizeRule):
    """按文件分类归类"""
    category_map: dict[FileCategory, str] = {
        FileCategory.DOCUMENT: "文档",
        FileCategory.IMAGE: "图片",
        FileCategory.VIDEO: "视频",
        FileCategory.AUDIO: "音频",
        FileCategory.CODE: "代码",
        FileCategory.ARCHIVE: "压缩包",
        FileCategory.PDF: "PDF",
        FileCategory.MARKDOWN: "Markdown",
        FileCategory.SPREADSHEET: "表格",
        FileCategory.PRESENTATION: "演示",
        FileCategory.DATA: "数据",
        FileCategory.EXECUTABLE: "可执行文件",
        FileCategory.FONT: "字体",
        FileCategory.UNKNOWN: "其他",
    }

    def __init__(self):
        super().__init__("按类型归类")

    def apply(self, file_info: FileInfo) -> str | None:
        return self.category_map.get(file_info.category, "其他")


class DateRule(OrganizeRule):
    """按日期归类（年/月）"""

    def __init__(self):
        super().__init__("按日期归类")

    def apply(self, file_info: FileInfo) -> str | None:
        dt = file_info.modified_time
        return f"{dt.year}/{dt.month:02d}月"


class ExtensionRule(OrganizeRule):
    """按扩展名归类"""

    def __init__(self):
        super().__init__("按扩展名归类")

    def apply(self, file_info: FileInfo) -> str | None:
        ext = file_info.extension.lstrip(".").upper()
        return ext if ext else "NO_EXT"


class SizeRule(OrganizeRule):
    """按文件大小归类"""

    def __init__(self):
        super().__init__("按文件大小归类")

    def apply(self, file_info: FileInfo) -> str | None:
        size = file_info.size_bytes
        if size < 1024:
            return "小于1KB"
        elif size < 100 * 1024:
            return "1KB-100KB"
        elif size < 1024 * 1024:
            return "100KB-1MB"
        elif size < 100 * 1024 * 1024:
            return "1MB-100MB"
        else:
            return "大于100MB"


class FileOrganizer:
    """文件整理器"""

    def __init__(self, rules: list[OrganizeRule] | None = None):
        self.rules = rules or [CategoryRule()]
        self._organized_count = 0
        self._errors: list[tuple[str, str]] = []
        self.preview_mode = True  # 默认预览模式
        self._undo_log: list[dict] = []  # 撤销日志

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
        """整理文件到目标目录

        Args:
            files: 文件列表
            target_root: 目标根目录
            rules: 组织规则列表
            preview: 预览模式（不实际移动）
            rename: 是否重命名文件
            rename_pattern: 重命名模板
            dry_run: 是否仅预览（不执行）
            progress_callback: 进度回调

        Returns:
            操作记录列表
        """
        rules = rules or self.rules
        target = Path(target_root)
        operations: list[dict] = []
        self._organized_count = 0
        self._errors = []

        for i, file_info in enumerate(files):
            try:
                # 确定目标子目录
                sub_dir = self._determine_target(file_info, rules)
                dest_dir = target / sub_dir if sub_dir else target

                # 确定目标文件名
                dest_name = self._determine_filename(file_info, rename, rename_pattern)
                dest_path = dest_dir / dest_name

                # 处理重名冲突
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
        """根据规则确定目标子目录"""
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
        """确定目标文件名"""
        if not rename or not pattern:
            return file_info.name

        # 支持的重命名变量:
        # {name} - 原文件名
        # {date} - 修改日期 (YYYY-MM-DD)
        # {time} - 修改时间 (HHMMSS)
        # {ext} - 扩展名
        # {idx} - 序号
        # {category} - 文件类别
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
        """处理文件重名冲突，添加数字后缀"""
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
        """保存撤销日志到文件"""
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._undo_log, f, ensure_ascii=False, indent=2)

    def undo(self, undo_log_path: str | Path) -> dict:
        """根据撤销日志回退文件操作

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
