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
