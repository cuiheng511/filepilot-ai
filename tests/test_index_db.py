"""MetadataDB unit tests — CRUD, search, filters, and stats."""

from datetime import datetime

import pytest

from filepilot.core.file_scanner import FileInfo
from filepilot.core.index_db import MetadataDB
from filepilot.utils.file_utils import FileCategory


@pytest.fixture
def db(tmp_path):
    return MetadataDB(tmp_path / "test_meta.db")


@pytest.fixture
def sample_files():
    now = datetime.now()
    return [
        FileInfo(
            path=f"/tmp/doc{i}.pdf",
            name=f"doc{i}.pdf",
            extension=".pdf",
            size_bytes=1024 * (i + 1),
            size_str=f"{1024 * (i + 1)} B",
            category=FileCategory.PDF,
            mime_type="application/pdf",
            modified_time=now,
            created_time=now,
        )
        for i in range(5)
    ]


class TestMetadataDBCRUD:
    def test_insert_and_get(self, db):
        info = FileInfo(
            path="/tmp/test.pdf",
            name="test.pdf",
            extension=".pdf",
            size_bytes=1024,
            size_str="1 KB",
            category=FileCategory.PDF,
            mime_type="application/pdf",
            modified_time=datetime.now(),
            created_time=datetime.now(),
        )
        db.insert_file(info)
        row = db.get_by_path("/tmp/test.pdf")
        assert row is not None
        assert row["name"] == "test.pdf"
        assert row["extension"] == ".pdf"
        assert row["size_bytes"] == 1024

    def test_insert_replace(self, db):
        info = FileInfo(
            path="/tmp/a.pdf",
            name="a.pdf",
            extension=".pdf",
            size_bytes=100,
            size_str="100 B",
            category=FileCategory.PDF,
            mime_type="application/pdf",
            modified_time=datetime.now(),
            created_time=datetime.now(),
        )
        db.insert_file(info)
        info.size_bytes = 200
        db.insert_file(info)
        row = db.get_by_path("/tmp/a.pdf")
        assert row["size_bytes"] == 200

    def test_get_nonexistent(self, db):
        assert db.get_by_path("/nonexistent") is None

    def test_remove(self, db):
        info = FileInfo(
            path="/tmp/removeme.txt",
            name="removeme.txt",
            extension=".txt",
            size_bytes=10,
            size_str="10 B",
            category=FileCategory.DOCUMENT,
            mime_type="text/plain",
            modified_time=datetime.now(),
            created_time=datetime.now(),
        )
        db.insert_file(info)
        db.remove("/tmp/removeme.txt")
        assert db.get_by_path("/tmp/removeme.txt") is None

    def test_remove_prefix(self, db):
        now = datetime.now()
        for i in range(3):
            info = FileInfo(
                path=f"/tmp/dir/file{i}.txt",
                name=f"file{i}.txt",
                extension=".txt",
                size_bytes=10,
                size_str="10 B",
                category=FileCategory.DOCUMENT,
                mime_type="text/plain",
                modified_time=now,
                created_time=now,
            )
            db.insert_file(info)
        db.remove_prefix("/tmp/dir")
        assert db.count() == 0

    def test_clear(self, db, sample_files):
        db.bulk_insert(sample_files)
        assert db.count() == 5
        db.clear()
        assert db.count() == 0

    def test_count_and_total_size(self, db, sample_files):
        assert db.count() == 0
        assert db.total_size() == 0
        db.bulk_insert(sample_files)
        assert db.count() == 5
        expected = sum(1024 * (i + 1) for i in range(5))
        assert db.total_size() == expected

    def test_get_stats(self, db, sample_files):
        db.bulk_insert(sample_files)
        stats = db.get_stats()
        assert stats["indexed_files"] == 5
        assert stats["total_size"] > 0
        assert "total_size_str" in stats


class TestMetadataDBSearch:
    def test_search_all(self, db, sample_files):
        db.bulk_insert(sample_files)
        results = db.search_metadata()
        assert len(results) == 5

    def test_search_by_category(self, db, sample_files):
        db.bulk_insert(sample_files)
        # Add a non-PDF file
        now = datetime.now()
        txt = FileInfo(
            path="/tmp/readme.txt",
            name="readme.txt",
            extension=".txt",
            size_bytes=50,
            size_str="50 B",
            category=FileCategory.DOCUMENT,
            mime_type="text/plain",
            modified_time=now,
            created_time=now,
        )
        db.insert_file(txt)
        results = db.search_metadata(category="PDF")
        assert all(r["category"] == "PDF" for r in results)
        results2 = db.search_metadata(category="Document")
        assert all(r["category"] == "Document" for r in results2)

    def test_search_by_extension(self, db, sample_files):
        db.bulk_insert(sample_files)
        results = db.search_metadata(extension=".pdf")
        assert len(results) == 5

    def test_search_by_size_range(self, db, sample_files):
        db.bulk_insert(sample_files)
        results = db.search_metadata(size_min=2048, size_max=4096)
        assert all(2048 <= r["size"] < 4096 for r in results)

    def test_search_by_date(self, db, sample_files):
        db.bulk_insert(sample_files)
        today = datetime.now().strftime("%Y-%m-%d")
        results = db.search_metadata(date_from=today)
        assert len(results) == 5

    def test_search_limit(self, db, sample_files):
        db.bulk_insert(sample_files)
        results = db.search_metadata(limit=2)
        assert len(results) == 2

    def test_search_by_paths(self, db, sample_files):
        db.bulk_insert(sample_files)
        paths = {"/tmp/doc0.pdf", "/tmp/doc1.pdf"}
        results = db.search_metadata(paths=paths)
        assert len(results) == 2
        result_paths = {r["path"] for r in results}
        assert result_paths == paths

    def test_search_no_match(self, db, sample_files):
        db.bulk_insert(sample_files)
        results = db.search_metadata(extension=".xyz")
        assert len(results) == 0


class TestMetadataDBEdgeCases:
    def test_empty_bulk_insert(self, db):
        db.bulk_insert([])
        assert db.count() == 0

    def test_bulk_insert_with_progress(self, db):
        now = datetime.now()
        many_files = [
            FileInfo(
                path=f"/tmp/unique_{i}.pdf",
                name=f"unique_{i}.pdf",
                extension=".pdf",
                size_bytes=100,
                size_str="100 B",
                category=FileCategory.PDF,
                mime_type="application/pdf",
                modified_time=now,
                created_time=now,
            )
            for i in range(25)
        ]
        calls = []

        def cb(count, msg):
            calls.append((count, msg))

        db.bulk_insert(many_files, progress_callback=cb)
        assert db.count() == 25

    def test_per_thread_connection(self, db):
        """Verify each thread gets its own connection."""
        conn1 = db._conn()
        conn2 = db._conn()
        assert conn1 is conn2  # same thread

    def test_format_dt_str_valid(self, db):
        result = db._format_dt_str("2024-01-15T10:30:00")
        assert result == "2024-01-15 10:30"

    def test_format_dt_str_none(self, db):
        assert db._format_dt_str(None) == ""

    def test_format_dt_str_invalid(self, db):
        assert db._format_dt_str("not-a-date") == "not-a-date"
