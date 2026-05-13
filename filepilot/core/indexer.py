"""文件索引器 — 基于 Whoosh 的全文搜索引擎"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from whoosh import fields, index
from whoosh.analysis import StandardAnalyzer
from whoosh.filedb.filestore import FileStorage
from whoosh.query import Every
from whoosh.qparser import MultifieldParser, FuzzyTermPlugin

from filepilot.core.file_scanner import FileInfo
from filepilot.utils.file_utils import get_file_category

logger = logging.getLogger("filepilot.indexer")


class FileIndexer:
    """文件索引器

    使用 Whoosh 对文件元数据和内容建立全文搜索索引。
    支持按文件名、路径、内容、类型、日期等字段搜索。
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
        """打开或创建索引"""
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
        """将文件列表加入索引

        Args:
            files: 文件列表
            content_extractor: 自定义内容提取函数
            summary_extractor: 自定义摘要提取函数
            progress_callback: 进度回调

        Returns:
            索引的文件数量
        """
        writer = self._ix.writer()
        indexed = 0
        total = len(files)

        for i, file_info in enumerate(files):
            try:
                # 跳过目录
                if file_info.is_directory:
                    continue

                # 提取内容
                content = ""
                if content_extractor:
                    content = content_extractor(file_info) or ""

                # 提取摘要
                summary = ""
                if summary_extractor:
                    summary = summary_extractor(file_info) or ""

                # 写入索引
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
                    progress_callback(i + 1, f"索引 {file_info.name} ({i + 1}/{total})")

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
        """搜索索引

        Args:
            query_str: 搜索关键词
            fields: 搜索字段列表，默认搜索所有文本字段
            limit: 最大返回结果数
            fuzzy: 是否启用模糊搜索

        Returns:
            搜索结果列表
        """
        fields = fields or ["filename", "content", "summary", "category"]
        parser = MultifieldParser(fields, schema=self._ix.schema)

        if fuzzy:
            parser.add_plugin(FuzzyTermPlugin())

        # 支持自然语言查询：自动添加模糊匹配
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
        """按文件类别搜索"""
        return self.search(f"category:{category}", fields=["category"], fuzzy=False, limit=limit)

    def search_by_extension(self, extension: str, limit: int = 100) -> list[dict]:
        """按扩展名搜索"""
        ext = extension if extension.startswith(".") else f".{extension}"
        return self.search(f"extension:{ext}", fields=["extension"], fuzzy=False, limit=limit)

    def search_by_date_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """按日期范围搜索"""
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
        """获取所有已索引文件"""
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
        """从索引中移除文件"""
        writer = self._ix.writer()
        writer.delete_by_term("path", str(file_path))
        writer.commit()

    def clear_index(self) -> None:
        """清空索引"""
        writer = self._ix.writer()
        writer.commit(mergetype=index.CLEAR)

    def get_stats(self) -> dict:
        """获取索引统计信息"""
        with self._ix.searcher() as searcher:
            doc_count = searcher.doc_count()
            return {
                "indexed_files": doc_count,
                "index_dir": str(self.index_dir),
                "index_size": self._get_index_size(),
            }

    def _get_highlights(self, result, query_str: str) -> str:
        """生成搜索结果高亮片段"""
        try:
            for field_name in ["content", "summary", "filename"]:
                fragment = result.highlights(field_name, top=2)
                if fragment:
                    return fragment
        except Exception:
            pass
        return ""

    def _format_dt(self, dt: datetime | None) -> str:
        """格式化日期时间"""
        if dt is None:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M")

    def _get_index_size(self) -> str:
        """获取索引目录大小"""
        total = 0
        for f in self.index_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        from filepilot.utils.file_utils import get_file_size_str
        return get_file_size_str(total)
