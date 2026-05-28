"""Tests for UI-independent chat assistant query handling."""

from filepilot.core.chat_assistant import process_file_query


class FakeIndexer:
    def get_stats(self):
        return {"indexed_files": 42, "total_size_str": "10 MB"}

    def search_by_category(self, category, limit=20):
        if category == "Pdf":
            return [{"filename": "paper.pdf", "modified": "today"}]
        return []

    def search_metadata(self, **kwargs):
        return [{"filename": "big.bin", "size_str": "120 MB"}]

    def search_by_extension(self, ext, limit=20):
        return [{"filename": f"main{ext}"}]

    def search(self, query, limit=10):
        return [{"filename": "notes.txt", "score": 0.75, "size_str": "1 KB", "modified": "today"}]


class FakeAI:
    is_available = True

    def generate(self, **kwargs):
        return f"AI saw {kwargs['prompt']}"


def test_process_file_query_counts_indexed_files():
    response = process_file_query("How many files do I have?", FakeIndexer())

    assert "42" in response
    assert "10 MB" in response


def test_process_file_query_finds_large_files():
    response = process_file_query("find large files", FakeIndexer())

    assert "big.bin" in response


def test_process_file_query_uses_ai_after_local_parser_miss():
    response = process_file_query("what should I archive?", FakeIndexer(), FakeAI())

    assert response == "AI saw what should I archive?"
