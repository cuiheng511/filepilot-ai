"""Tests for UI-independent chat assistant query handling."""

from filepilot.core.chat_assistant import (
    ai_query,
    local_query_fallback,
    process_file_query,
    try_local_query,
)


class FakeIndexer:
    def __init__(
        self,
        stats: dict | None = None,
        category_results: dict[str, list[dict]] | None = None,
        metadata_results: list[dict] | None = None,
        extension_results: dict[str, list[dict]] | None = None,
        search_results: dict[str, list[dict]] | None = None,
    ) -> None:
        self._stats = (
            stats if stats is not None else {"indexed_files": 42, "total_size_str": "10 MB"}
        )
        self._category = (
            category_results
            if category_results is not None
            else {"Pdf": [{"filename": "paper.pdf", "modified": "today"}]}
        )
        self._metadata = (
            metadata_results
            if metadata_results is not None
            else [{"filename": "big.bin", "size_str": "120 MB"}]
        )
        self._extension = extension_results if extension_results is not None else None
        self._search = search_results or {}

    def get_stats(self):
        return self._stats

    def search_by_category(self, category, limit=20):
        return self._category.get(category, [])

    def search_metadata(self, **kwargs):
        return self._metadata

    def search_by_extension(self, ext, limit=20):
        if self._extension is None:
            return [{"filename": f"main{ext}"}]
        return self._extension.get(ext, [])

    def search(self, query, limit=10):
        if query in self._search:
            return self._search[query]
        return [{"filename": "notes.txt", "score": 0.75, "size_str": "1 KB", "modified": "today"}]


class FakeAI:
    def __init__(
        self,
        response: str | None = None,
        *,
        available: bool = True,
        raise_exc: Exception | None = None,
    ) -> None:
        self.is_available = available
        self._explicit_response = response
        self._raise = raise_exc
        self.calls: list[dict] = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise is not None:
            raise self._raise
        if self._explicit_response is not None:
            return self._explicit_response
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


def test_process_file_query_local_miss_without_ai_returns_fallback():
    response = process_file_query("what should I archive?", FakeIndexer(), None)

    assert (
        "I can help you find files" in response or "I found" in response or "I couldn't" in response
    )


def test_process_file_query_local_miss_with_unavailable_ai_returns_fallback():
    response = process_file_query("what should I archive?", FakeIndexer(), FakeAI(available=False))

    assert "I couldn't" in response or "I found" in response or "I can help" in response


def test_try_local_query_without_indexer_returns_helpful_message():
    result = try_local_query("how many files", None)

    assert "No indexer available" in result
    assert "build the index" in result


def test_try_local_query_counts_specific_category():
    indexer = FakeIndexer(
        category_results={
            "Pdf": [{"filename": "a.pdf"}, {"filename": "b.pdf"}, {"filename": "c.pdf"}]
        }
    )
    result = try_local_query("how many pdf", indexer)

    assert "3" in result
    assert "Pdf" in result


def test_try_local_query_finds_small_files():
    indexer = FakeIndexer(metadata_results=[{"filename": "tiny.txt", "size_str": "100 B"}])
    result = try_local_query("find small files", indexer)

    assert "tiny.txt" in result
    assert "small files" in result


def test_try_local_query_finds_small_files_when_empty():
    indexer = FakeIndexer(metadata_results=[])
    result = try_local_query("find small files", indexer)

    assert "No very small files" in result


def test_try_local_query_finds_large_files_when_empty():
    indexer = FakeIndexer(metadata_results=[])
    result = try_local_query("find large files", indexer)

    assert "No files larger than 100MB" in result


def test_try_local_query_finds_files_by_category():
    indexer = FakeIndexer(
        category_results={"Pdf": [{"filename": "paper.pdf", "modified": "yesterday"}]}
    )
    result = try_local_query("find pdf files", indexer)

    assert "paper.pdf" in result
    assert "yesterday" in result


def test_try_local_query_truncates_long_category_result_list():
    many_files = [{"filename": f"f{i}.pdf", "modified": ""} for i in range(15)]
    indexer = FakeIndexer(category_results={"Pdf": many_files})
    result = try_local_query("find pdf files", indexer)

    assert "and 5 more" in result


def test_try_local_query_returns_no_files_message_when_category_empty():
    indexer = FakeIndexer(category_results={})
    result = try_local_query("find pdf files", indexer)

    assert "No pdf files found" in result


def test_try_local_query_finds_files_by_extension():
    indexer = FakeIndexer(extension_results={".py": [{"filename": "main.py"}]})
    result = try_local_query("find .py files", indexer)

    assert "main.py" in result
    assert ".py" in result


def test_try_local_query_finds_files_by_generic_search_term():
    indexer = FakeIndexer(
        search_results={"meeting notes": [{"filename": "meeting.md", "score": 0.95}]}
    )
    result = try_local_query("find meeting notes", indexer)

    assert "meeting.md" in result
    assert "95%" in result


def test_try_local_query_returns_none_when_no_branch_matches():
    result = try_local_query("completely unrelated query", FakeIndexer())

    assert result is None


def test_try_local_query_skips_short_search_terms_after_stripping_keywords():
    result = try_local_query("find", FakeIndexer())

    assert result is None


def test_local_query_fallback_without_indexer_returns_help():
    result = local_query_fallback("anything", "anything", None)

    assert "I can help you find files" in result
    assert "Open a folder" in result
    assert "Build the index" in result


def test_local_query_fallback_with_results_lists_them():
    indexer = FakeIndexer(
        search_results={
            "report": [{"filename": "report.pdf", "size_str": "2 MB", "modified": "yesterday"}]
        }
    )
    result = local_query_fallback("report", "report", indexer)

    assert "report.pdf" in result
    assert "2 MB" in result
    assert "Configure an AI provider" in result


def test_local_query_fallback_with_no_results_returns_tip():
    result = local_query_fallback("xyzzy", "xyzzy", FakeIndexer(search_results={"xyzzy": []}))

    assert "I couldn't find files" in result
    assert "Find PDF files" in result


def test_ai_query_returns_provider_response():
    ai = FakeAI(response="Here's what I suggest...")
    result = ai_query("organize my files", FakeIndexer(), ai)

    assert result == "Here's what I suggest..."
    assert len(ai.calls) == 1
    assert ai.calls[0]["prompt"] == "organize my files"
    assert "file management assistant" in ai.calls[0]["system_prompt"]
    assert "42" in ai.calls[0]["system_prompt"]


def test_ai_query_handles_indexer_none():
    ai = FakeAI(response="response without indexer")
    result = ai_query("hi", None, ai)

    assert result == "response without indexer"
    assert "0" in ai.calls[0]["system_prompt"]


def test_ai_query_handles_empty_response():
    ai = FakeAI(response="")
    result = ai_query("hi", FakeIndexer(), ai)

    assert "couldn't generate" in result


def test_ai_query_handles_provider_exception():
    ai = FakeAI(raise_exc=RuntimeError("API down"))
    result = ai_query("hi", FakeIndexer(), ai)

    assert "AI error" in result
    assert "API down" in result
    assert "Falling back" in result
