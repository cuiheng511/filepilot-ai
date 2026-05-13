"""File Indexer — Whoosh-based full-text search engine"""

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from whoosh import fields, index
from whoosh.analysis import StandardAnalyzer
from whoosh.filedb.filestore import FileStorage
from whoosh.qparser import FuzzyTermPlugin, MultifieldParser
from whoosh.query import Every

from filepilot.core.file_scanner import FileInfo

logger = logging.getLogger("filepilot.indexer")


class FileIndexer:
    """File Indexer

    Builds a full-text search index on file metadata and content using Whoosh.
    Supports search by filename, path, content, type, date, etc.
    """

    SCHEMA = fields.Schema(
        path=fields.ID(unique=True, stored=True),
        filename=fields.TEXT(stored=True, analyzer=StandardAnalyzer()),
        extension=fields.ID(stored=True),
        category=fields.ID(stored=True),
        size=fields.NUMERIC(stored=True),
        size_str=fields.STORED,
        modified=fields.DATETIME(stored=True),
        created=fields.DATETIME(stored=True),
        content=fields.TEXT(analyzer=StandardAnalyzer()),
        summary=fields.TEXT(analyzer=StandardAnalyzer()),
    )

    def __init__(self, index_dir: str | Path = "~/.filepilot/index"):
        self.index_dir = Path(index_dir).expanduser()
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._ix = self._open_or_create_index()
        self._total_indexed = 0

    def _open_or_create_index(self) -> index.Index:
        """Open or create index"""
        storage = FileStorage(str(self.index_dir))
        if index.exists_in(storage):
            return storage.open_index()
        return storage.create_index(self.SCHEMA)

    def index_files(
        self,
        files: list[FileInfo],
        content_extractor: Callable[[FileInfo], str] | None = None,
        summary_extractor: Callable[[FileInfo], str] | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> int:
        """Add file list to index

        Args:
            files: List of files
            content_extractor: Custom content extraction function
            summary_extractor: Custom summary extraction function
            progress_callback: Progress callback

        Returns:
            Number of indexed files
        """
        writer = self._ix.writer()
        indexed = 0
        total = len(files)

        for i, file_info in enumerate(files):
            try:
                # Skip directories
                if file_info.is_directory:
                    continue

                # Extract content
                content = ""
                if content_extractor:
                    content = content_extractor(file_info) or ""

                # Extract summary
                summary = ""
                if summary_extractor:
                    summary = summary_extractor(file_info) or ""

                # Write to index
                writer.update_document(
                    path=str(file_info.path),
                    filename=file_info.name,
                    extension=file_info.extension,
                    category=file_info.category.label,
                    size=file_info.size_bytes,
                    size_str=file_info.size_str,
                    modified=file_info.modified_time,
                    created=file_info.created_time,
                    content=content,
                    summary=summary,
                )
                indexed += 1

                if progress_callback:
                    progress_callback(i + 1, f"Indexing {file_info.name} ({i + 1}/{total})")

            except (OSError, PermissionError, ValueError) as e:
                logger.debug("Skipped indexing %s: %s", file_info.name, e)
                continue

        writer.commit()
        self._total_indexed += indexed
        return indexed

    def search(
        self,
        query_str: str,
        fields: list[str] | None = None,
        limit: int = 50,
        fuzzy: bool = True,
    ) -> list[dict]:
        """Search index

        Args:
            query_str: Search query
            fields: Fields to search, defaults to all text fields
            limit: Maximum results
            fuzzy: Whether to enable fuzzy search

        Returns:
            List of search results
        """
        fields = fields or ["filename", "content", "summary", "category"]
        parser = MultifieldParser(fields, schema=self._ix.schema)

        if fuzzy:
            parser.add_plugin(FuzzyTermPlugin())

        # Support natural language queries: auto-add fuzzy matching
        parsed_query = parser.parse(query_str)

        with self._ix.searcher() as searcher:
            results = searcher.search(parsed_query, limit=limit, terms=True)
            return [
                {
                    "path": r["path"],
                    "filename": r["filename"],
                    "extension": r["extension"],
                    "category": r.get("category", ""),
                    "size": r.get("size", 0),
                    "size_str": r.get("size_str", ""),
                    "modified": self._format_dt(r.get("modified")),
                    "score": r.score,
                    "highlights": self._get_highlights(r, query_str),
                }
                for r in results
            ]

    def search_by_category(self, category: str, limit: int = 100) -> list[dict]:
        """Search by file category"""
        return self.search(f"category:{category}", fields=["category"], fuzzy=False, limit=limit)

    def search_by_extension(self, extension: str, limit: int = 100) -> list[dict]:
        """Search by file extension"""
        ext = extension if extension.startswith(".") else f".{extension}"
        return self.search(f"extension:{ext}", fields=["extension"], fuzzy=False, limit=limit)

    def search_by_date_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Search by date range"""
        from whoosh.query import DateRange

        start = start or datetime(2000, 1, 1)
        end = end or datetime.now()

        with self._ix.searcher() as searcher:
            query = DateRange("modified", start, end)
            results = searcher.search(query, limit=limit)
            return [
                {
                    "path": r["path"],
                    "filename": r["filename"],
                    "category": r.get("category", ""),
                    "modified": self._format_dt(r.get("modified")),
                    "size_str": r.get("size_str", ""),
                }
                for r in results
            ]

    def get_all_indexed(self, limit: int = 1000) -> list[dict]:
        """Get all indexed files"""
        with self._ix.searcher() as searcher:
            results = searcher.search(Every(), limit=limit)
            return [
                {
                    "path": r["path"],
                    "filename": r["filename"],
                    "category": r.get("category", ""),
                    "size_str": r.get("size_str", ""),
                    "modified": self._format_dt(r.get("modified")),
                }
                for r in results
            ]

    def remove_from_index(self, file_path: str | Path) -> None:
        """Remove file from index"""
        writer = self._ix.writer()
        writer.delete_by_term("path", str(file_path))
        writer.commit()

    def clear_index(self) -> None:
        """Clear index"""
        writer = self._ix.writer()
        writer.commit(mergetype=index.CLEAR)

    def get_stats(self) -> dict:
        """Get index statistics"""
        with self._ix.searcher() as searcher:
            doc_count = searcher.doc_count()
            return {
                "indexed_files": doc_count,
                "index_dir": str(self.index_dir),
                "index_size": self._get_index_size(),
            }

    def _get_highlights(self, result, query_str: str) -> str:
        """Generate search result highlight snippets"""
        try:
            for field_name in ["content", "summary", "filename"]:
                fragment = result.highlights(field_name, top=2)
                if fragment:
                    return fragment
        except Exception:
            pass
        return ""

    def _format_dt(self, dt: datetime | None) -> str:
        """Format datetime"""
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M")

    def _get_index_size(self) -> str:
        """Get index directory size"""
        total = 0
        for f in self.index_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        from filepilot.utils.file_utils import get_file_size_str
        return get_file_size_str(total)
