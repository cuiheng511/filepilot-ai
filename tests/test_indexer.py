"""FileIndexer integration tests."""

from datetime import datetime

from filepilot.core.file_scanner import FileInfo
from filepilot.core.indexer import FileIndexer
from filepilot.utils.file_utils import FileCategory


def test_file_indexer_creates_and_reopens_index(tmp_path):
    """The Whoosh index should initialize on a fresh path and reopen cleanly."""
    now = datetime.now()
    file_info = FileInfo(
        path=tmp_path / "market-notes.md",
        name="market-notes.md",
        extension=".md",
        size_bytes=128,
        size_str="128 B",
        category=FileCategory.MARKDOWN,
        mime_type="text/markdown",
        modified_time=now,
        created_time=now,
    )

    first = FileIndexer(tmp_path / "index")
    assert first.index_files([file_info], content_extractor=lambda _: "Japan pricing margin risk")

    second = FileIndexer(tmp_path / "index")
    results = second.search("Japan pricing")

    assert results
    assert results[0]["filename"] == "market-notes.md"


def test_remove_from_index_removes_embedding_cache(tmp_path):
    indexer = FileIndexer(tmp_path / "index")
    path = str(tmp_path / "notes.md")
    indexer._embed_cache.put(path, [0.1, 0.2])
    indexer._embed_cache.save()

    indexer.remove_from_index(path)
    indexer._embed_cache.save()
    fresh_cache = FileIndexer(tmp_path / "index")._embed_cache

    assert indexer._embed_cache.get(path) is None
    assert fresh_cache.get(path) is None


def test_clear_index_persists_empty_embedding_cache(tmp_path):
    indexer = FileIndexer(tmp_path / "index")
    indexer._embed_cache.put(str(tmp_path / "notes.md"), [0.1, 0.2])
    indexer._embed_cache.save()

    indexer.clear_index()
    fresh_cache = FileIndexer(tmp_path / "index")._embed_cache

    assert len(indexer._embed_cache) == 0
    assert len(fresh_cache) == 0
