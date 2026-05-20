"""File Indexer — SQLite metadata + Whoosh full-text search engine"""

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from whoosh import fields, index
from whoosh.analysis import StandardAnalyzer
from whoosh.qparser import FuzzyTermPlugin, MultifieldParser

from filepilot.core.embeddings import EmbeddingCache, embed_text
from filepilot.core.file_scanner import FileInfo
from filepilot.core.index_db import MetadataDB

logger = logging.getLogger("filepilot.indexer")


class FileIndexer:
    """File Indexer

    Hybrid indexer: SQLite for fast metadata queries (type, size, date, extension),
    Whoosh for full-text content search. Provides up to 10x faster metadata-only queries.
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
        self._meta_db = MetadataDB(self.index_dir.parent / "file_meta.db")
        self._embed_cache = EmbeddingCache(self.index_dir.parent)
        self._total_indexed = 0

    def _open_or_create_index(self) -> index.Index:
        """Open or create index"""
        index_path = str(self.index_dir)
        if index.exists_in(index_path):
            return index.open_dir(index_path)
        return index.create_in(index_path, self.SCHEMA)

    def index_files(
        self,
        files: list[FileInfo],
        content_extractor: Callable[[FileInfo], str] | None = None,
        summary_extractor: Callable[[FileInfo], str] | None = None,
        embedding_extractor: Callable[[FileInfo], str] | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> int:
        """Add file list to index

        Writes metadata to SQLite and full-text content to Whoosh.

        Args:
            files: List of files
            content_extractor: Custom content extraction function
            summary_extractor: Custom summary extraction function
            embedding_extractor: Custom text extraction for embedding (AI semantic search)
            progress_callback: Progress callback

        Returns:
            Number of indexed files

        """
        # Bulk insert metadata into SQLite
        self._meta_db.bulk_insert(files, progress_callback)

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
                # Compute and cache embedding for semantic search
                if embedding_extractor:
                    embed_text_content = embedding_extractor(file_info) or ""
                    if embed_text_content:
                        emb = embed_text(embed_text_content)
                        if emb:
                            self._embed_cache.put(str(file_info.path), emb)

                indexed += 1

                if progress_callback:
                    progress_callback(i + 1, f"Indexing {file_info.name} ({i + 1}/{total})")

            except (OSError, PermissionError, ValueError) as e:
                logger.debug("Skipped indexing %s: %s", file_info.name, e)
                continue

        self._embed_cache.save()
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
        """Search index (Whoosh full-text search)

        For full-text content searches. Metadata-only queries are faster
        via :meth:`search_metadata`.

        Args:
            query_str: Search query
            fields: Fields to search, defaults to all text fields
            limit: Maximum results
            fuzzy: Whether to enable fuzzy search

        Returns:
            List of search results with highlights

        """
        fields = fields or ["filename", "content", "summary", "category"]
        parser = MultifieldParser(fields, schema=self._ix.schema)

        if fuzzy:
            parser.add_plugin(FuzzyTermPlugin())

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

    def search_metadata(
        self,
        category: str | None = None,
        extension: str | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        paths: set[str] | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """Fast metadata-only search via SQLite.

        Use this for queries that filter by type, size, date, or extension
        without full-text content search. 10x faster than Whoosh for these queries.
        """
        return self._meta_db.search_metadata(
            category=category,
            extension=extension,
            size_min=size_min,
            size_max=size_max,
            date_from=date_from,
            date_to=date_to,
            paths=paths,
            limit=limit,
        )

    def search_by_category(self, category: str, limit: int = 100) -> list[dict]:
        """Search by file category (uses SQLite metadata)"""
        return self._meta_db.search_metadata(category=category, limit=limit)

    def search_by_extension(self, extension: str, limit: int = 100) -> list[dict]:
        """Search by file extension (uses SQLite metadata)"""
        ext = extension if extension.startswith(".") else f".{extension}"
        return self._meta_db.search_metadata(extension=ext.lower(), limit=limit)

    def search_combined(
        self,
        query_str: str,
        category: str | None = None,
        extension: str | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        fuzzy: bool = True,
        limit: int = 100,
    ) -> list[dict]:
        """Hybrid search: Whoosh full-text + SQLite metadata filter.

        First searches Whoosh for content matches, then filters by metadata criteria.
        Best for mixed queries like "machine learning pdf".
        """
        results = self.search(query_str, fuzzy=fuzzy, limit=limit * 2)
        if not (category or extension or size_min is not None or size_max is not None):
            return results[:limit]

        filtered = []
        for r in results:
            if category and category != "All" and r.get("category", "") != category:
                continue
            if extension:
                ext = extension if extension.startswith(".") else f".{extension}"
                if r.get("extension", "") != ext.lower():
                    continue
            if size_min is not None and (r.get("size", 0) or 0) < size_min:
                continue
            if size_max is not None and (r.get("size", 0) or 0) >= size_max:
                continue
            filtered.append(r)
            if len(filtered) >= limit:
                break
        return filtered

    def search_by_date_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Search by date range (uses SQLite metadata)"""
        date_from = start.isoformat() if start else None
        date_to = end.isoformat() if end else None
        return self._meta_db.search_metadata(date_from=date_from, date_to=date_to, limit=limit)

    def get_all_indexed(self, limit: int = 1000) -> list[dict]:
        """Get all indexed files (uses SQLite metadata)"""
        return self._meta_db.search_metadata(limit=limit)

    def remove_from_index(self, file_path: str | Path) -> None:
        """Remove file from index"""
        self._meta_db.remove(str(file_path))
        writer = self._ix.writer()
        writer.delete_by_term("path", str(file_path))
        writer.commit()

    def clear_index(self) -> None:
        """Clear index"""
        self._meta_db.clear()
        self._embed_cache.clear()
        writer = self._ix.writer()
        writer.commit(mergetype=index.CLEAR)

    def search_semantic(
        self,
        query_str: str,
        limit: int = 50,
        fuzzy: bool = True,
    ) -> list[dict]:
        """Semantic search: Whoosh full-text + embedding re-ranking.

        First runs a Whoosh full-text search, then re-ranks results
        by cosine similarity using cached embeddings.
        """
        results = self.search(query_str, fuzzy=fuzzy, limit=limit * 2)
        if not results:
            return results

        query_embedding = embed_text(query_str)
        if not query_embedding:
            return results[:limit]

        ranked = self._embed_cache.search(query_embedding, results)
        return ranked[:limit]

    def get_stats(self) -> dict:
        """Get index statistics"""
        meta_stats = self._meta_db.get_stats()
        return {
            "indexed_files": meta_stats["indexed_files"],
            "index_dir": str(self.index_dir),
            "index_size": self._get_index_size(),
            "total_size": meta_stats["total_size"],
            "total_size_str": meta_stats["total_size_str"],
        }

    def _get_highlights(self, result, query_str: str) -> str:
        """Generate search result highlight snippets"""
        try:
            for field_name in ["content", "summary", "filename"]:
                fragment = result.highlights(field_name, top=2)
                if fragment:
                    return fragment  # type: ignore[no-any-return]
        except Exception as e:
            logger.debug("Failed to generate highlights: %s", e)
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
