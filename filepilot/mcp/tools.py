"""Tool implementation shared by the MCP server and tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from filepilot.ai.summarizer import Summarizer
from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.file_organizer import (
    CategoryRule,
    DateRule,
    ExtensionRule,
    FileOrganizer,
    OrganizeRule,
    SizeRule,
)
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.core.indexer import FileIndexer
from filepilot.core.tag_manager import TagManager
from filepilot.extractors.code_extractor import CodeExtractor
from filepilot.extractors.docx_extractor import DocxExtractor
from filepilot.extractors.markdown_extractor import MarkdownExtractor
from filepilot.extractors.pdf_extractor import PDFExtractor
from filepilot.extractors.pptx_extractor import PptxExtractor
from filepilot.extractors.xlsx_extractor import XlsxExtractor
from filepilot.mcp.security import PathGuard


class FilePilotMCPTools:
    """Local-first FilePilot operations exposed through MCP."""

    def __init__(self, guard: PathGuard, index_dir: str | Path | None = None):
        self.guard = guard
        self.index_dir = (
            Path(index_dir).expanduser() if index_dir else Path.home() / ".filepilot" / "mcp-index"
        )

    def server_status(self) -> dict:
        """Return the server's safety posture and configured directories."""
        return {
            "allowed_dirs": self.guard.list_allowed_dirs(),
            "write_enabled": self.guard.config.write_enabled,
            "allow_hidden": self.guard.config.allow_hidden,
            "max_file_size_bytes": self.guard.config.max_file_size_bytes,
            "max_read_chars": self.guard.config.max_read_chars,
            "index_dir": str(self.index_dir),
        }

    def scan_files(
        self,
        root: str,
        recursive: bool = True,
        limit: int = 200,
        extensions: list[str] | None = None,
        include_hidden: bool = False,
    ) -> dict:
        """Scan an allowed directory and return file metadata."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        normalized_exts = _normalize_extensions(extensions)
        scanner = FileScanner()
        files = scanner.scan(root_path, recursive=recursive, include_hidden=include_hidden)
        if normalized_exts:
            files = [f for f in files if f.extension in normalized_exts]
        files = files[: max(1, min(limit, 1000))]

        return {
            "root": str(root_path),
            "count": len(files),
            "files": [_file_info_to_dict(f, root_path) for f in files],
            "stats": scanner.stats,
        }

    def search_files(
        self,
        root: str,
        query: str,
        recursive: bool = True,
        limit: int = 50,
        extensions: list[str] | None = None,
        include_hidden: bool = False,
    ) -> dict:
        """Search file names and paths inside an allowed directory without building an index."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        query_lower = query.lower().strip()
        normalized_exts = _normalize_extensions(extensions)
        scanner = FileScanner()
        matches: list[FileInfo] = []
        for file_info in scanner.scan(
            root_path, recursive=recursive, include_hidden=include_hidden
        ):
            if normalized_exts and file_info.extension not in normalized_exts:
                continue
            relative = file_info.relative_path(root_path).lower()
            if query_lower in file_info.name.lower() or query_lower in relative:
                matches.append(file_info)
            if len(matches) >= max(1, min(limit, 200)):
                break

        return {
            "root": str(root_path),
            "query": query,
            "count": len(matches),
            "results": [_file_info_to_dict(f, root_path) for f in matches],
        }

    def index_folder(
        self,
        root: str,
        include_content: bool = True,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> dict:
        """Build or update a path-scoped local search index."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        scanner = FileScanner()
        files = scanner.scan(root_path, recursive=recursive, include_hidden=include_hidden)
        indexer = FileIndexer(index_dir=self.index_dir)
        indexed = indexer.index_files(
            files,
            content_extractor=self._extract_for_index if include_content else None,
            incremental=True,
        )
        return {
            "root": str(root_path),
            "scanned": len(files),
            "indexed": indexed,
            "include_content": include_content,
            "index_stats": indexer.get_stats(),
        }

    def search_index(
        self,
        query: str,
        root: str | None = None,
        limit: int = 50,
        semantic: bool = False,
    ) -> dict:
        """Search the FilePilot MCP index, optionally scoped to an allowed directory."""
        root_path = None
        if root:
            root_path = self.guard.resolve_read_path(root)
            self.guard.ensure_directory_readable(root_path)

        indexer = FileIndexer(index_dir=self.index_dir)
        raw_results = (
            indexer.search_semantic(query, limit=limit * 2)
            if semantic
            else indexer.search(query, limit=limit * 2)
        )
        results = []
        for result in raw_results:
            path = Path(result["path"]).resolve()
            if not self.guard.is_allowed_path(path):
                continue
            if root_path and not (path == root_path or root_path in path.parents):
                continue
            results.append(result)
            if len(results) >= max(1, min(limit, 200)):
                break

        return {"query": query, "count": len(results), "results": results}

    def read_file(self, path: str, start: int = 0, max_chars: int | None = None) -> dict:
        """Read a slice from a text file inside an allowed directory."""
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        read_limit = self._read_limit(max_chars)

        text = file_path.read_text(encoding="utf-8", errors="replace")
        start = max(0, start)
        chunk = text[start : start + read_limit]
        return {
            "path": str(file_path),
            "name": file_path.name,
            "start": start,
            "returned_chars": len(chunk),
            "total_chars": len(text),
            "truncated": start + len(chunk) < len(text),
            "content": chunk,
        }

    def extract_file_text(self, path: str, max_chars: int | None = None) -> dict:
        """Extract text from documents, code, Markdown, spreadsheets, and presentations."""
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        read_limit = self._read_limit(max_chars)

        text = extract_text(file_path)
        return {
            "path": str(file_path),
            "name": file_path.name,
            "extension": file_path.suffix.lower(),
            "returned_chars": min(len(text), read_limit),
            "total_chars": len(text),
            "truncated": len(text) > read_limit,
            "content": text[:read_limit],
        }

    def summarize_file(self, path: str, max_length: int = 500) -> dict:
        """Summarize a file with configured AI, falling back to an extractive local summary."""
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        text = extract_text(file_path)
        if not text.strip():
            return {
                "path": str(file_path),
                "success": False,
                "summary": "",
                "keywords": [],
                "error": "No extractable text",
            }

        summarizer = Summarizer()
        max_length = max(80, min(max_length, 2000))
        summary = summarizer.summarize_text(text[:8000], max_length=max_length)
        source = "ai"
        if not summary:
            summary = _extractive_summary(text, max_length)
            source = "local-extractive"

        return {
            "path": str(file_path),
            "success": True,
            "summary": summary,
            "summary_source": source,
            "keywords": summarizer.extract_keywords(text, top_n=10),
        }

    def suggest_tags(self, path: str, max_tags: int = 8) -> dict:
        """Suggest tags for a file without writing tag metadata."""
        file_path = self.guard.resolve_read_path(path)
        self.guard.ensure_file_readable(file_path)
        text = extract_text(file_path)
        summarizer = Summarizer()
        keywords = (
            summarizer.extract_keywords(text, top_n=max(1, min(max_tags, 20))) if text else []
        )
        category = FileScanner.create_file_info(file_path).category.label
        tags = []
        for tag in [category, file_path.suffix.lower().lstrip("."), *keywords]:
            if tag and tag not in tags:
                tags.append(tag)
        return {"path": str(file_path), "suggested_tags": tags[:max_tags]}

    def add_tags(self, path: str, tags: list[str]) -> dict:
        """Write FilePilot tag metadata. Requires write mode."""
        file_path = self.guard.resolve_write_path(path)
        self.guard.ensure_file_readable(file_path)
        cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
        manager = TagManager()
        for tag in cleaned_tags:
            manager.add_tag(file_path, tag)
        manager.flush()
        return {"path": str(file_path), "tags": manager.get_tags(file_path)}

    def find_duplicates(
        self,
        root: str,
        min_size: int = 1,
        limit_groups: int = 50,
        include_hidden: bool = False,
    ) -> dict:
        """Find exact duplicate files inside an allowed directory."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        scanner = FileScanner()
        files = scanner.scan(root_path, include_hidden=include_hidden)
        groups = DuplicateFinder().find_duplicates(files, min_size=max(1, min_size))
        limited = groups[: max(1, min(limit_groups, 200))]
        stats = DuplicateFinder().get_duplicate_stats(groups)
        return {
            "root": str(root_path),
            "groups_returned": len(limited),
            "groups_total": len(groups),
            "stats": stats,
            "duplicates": [
                {
                    "size_bytes": group[0].size_bytes,
                    "size": group[0].size_str,
                    "files": [str(file_info.path) for file_info in group],
                }
                for group in limited
            ],
        }

    def propose_organization_plan(
        self,
        root: str,
        target_root: str,
        rules: list[str] | None = None,
        rename_pattern: str | None = None,
        limit: int = 500,
        include_hidden: bool = False,
    ) -> dict:
        """Create a dry-run organization plan. This never moves files."""
        root_path = self.guard.resolve_read_path(root, allow_hidden=include_hidden)
        self.guard.ensure_directory_readable(root_path)

        target = Path(target_root).expanduser().resolve()
        scanner = FileScanner()
        files = scanner.scan(root_path, include_hidden=include_hidden)[: max(1, min(limit, 2000))]
        organizer = FileOrganizer()
        operations = organizer.organize(
            files,
            target_root=target,
            rules=_rules_from_names(rules),
            dry_run=True,
            rename=bool(rename_pattern),
            rename_pattern=rename_pattern,
        )
        return {
            "root": str(root_path),
            "target_root": str(target),
            "count": len(operations),
            "dry_run": True,
            "operations": operations,
        }

    def _extract_for_index(self, file_info: FileInfo) -> str:
        try:
            self.guard.ensure_file_readable(file_info.path)
            return extract_text(file_info.path)[: self.guard.config.max_read_chars]
        except Exception:
            return ""

    def _read_limit(self, max_chars: int | None) -> int:
        if max_chars is None:
            return self.guard.config.max_read_chars
        return max(1, min(max_chars, self.guard.config.max_read_chars))


def extract_text(file_path: Path) -> str:
    """Extract text from supported files, falling back to UTF-8 text reads."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return PDFExtractor().extract_text(file_path)
    if ext in {".md", ".markdown", ".mdx"}:
        return MarkdownExtractor().extract_text(file_path)
    if ext == ".docx":
        return DocxExtractor().extract_text(file_path)
    if ext in {".xlsx", ".xls"}:
        return XlsxExtractor().extract_text(file_path)
    if ext in {".pptx", ".ppt"}:
        return PptxExtractor().extract_text(file_path)
    if ext in {".py", ".js", ".ts", ".java", ".cpp", ".c", ".rs", ".go"}:
        return CodeExtractor().extract_text(file_path)
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _rules_from_names(names: Iterable[str] | None) -> list[OrganizeRule]:
    rule_map: dict[str, Callable[[], OrganizeRule]] = {
        "category": CategoryRule,
        "type": CategoryRule,
        "date": DateRule,
        "extension": ExtensionRule,
        "size": SizeRule,
    }
    selected = []
    for name in names or ["category"]:
        rule_class = rule_map.get(name.lower())
        if rule_class:
            selected.append(rule_class())
    return selected or [CategoryRule()]


def _file_info_to_dict(file_info: FileInfo, root: Path | None = None) -> dict:
    return {
        "path": str(file_info.path),
        "relative_path": file_info.relative_path(root),
        "name": file_info.name,
        "extension": file_info.extension,
        "category": file_info.category.label,
        "size_bytes": file_info.size_bytes,
        "size": file_info.size_str,
        "modified": file_info.modified_time.isoformat(),
        "created": file_info.created_time.isoformat(),
        "mime_type": file_info.mime_type,
    }


def _normalize_extensions(extensions: list[str] | None) -> set[str]:
    if not extensions:
        return set()
    return {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}


def _extractive_summary(text: str, max_length: int) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = " ".join(lines)
    if len(summary) <= max_length:
        return summary
    return summary[: max_length - 3].rstrip() + "..."
