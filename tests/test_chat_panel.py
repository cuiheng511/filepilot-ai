"""Tests for AI chat panel local query behavior."""

from filepilot.ui.chat_panel import ChatPanel


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


def test_chat_panel_counts_indexed_files(qtbot):
    panel = ChatPanel(indexer=FakeIndexer())
    qtbot.addWidget(panel)

    response = panel._process_query("How many files do I have?")

    assert "42" in response
    assert "10 MB" in response
    assert panel.input_field.accessibleName() == "Chat message input"


def test_chat_panel_finds_large_files(qtbot):
    panel = ChatPanel(indexer=FakeIndexer())
    qtbot.addWidget(panel)

    response = panel._process_query("find large files")

    assert "big.bin" in response


def test_chat_panel_returns_setup_hint_without_indexer(qtbot):
    panel = ChatPanel(indexer=None)
    qtbot.addWidget(panel)

    response = panel._process_query("find docs")

    assert "build the index" in response.lower()
