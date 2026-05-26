"""AI Chat Panel — conversational file assistant.

Users can ask natural language questions like:
- "Find PDF files modified last week"
- "Show me the largest files in Downloads"
- "How many Python files do I have?"

The AI parses intent and executes searches/actions via the indexer.
"""

from PySide6.QtCore import Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from filepilot.core.app_state import AppState
from filepilot.core.event_bus import EventBus
from filepilot.core.indexer import FileIndexer
from filepilot.core.worker import Worker
from filepilot.ui.base_panel import BasePanel


class ChatMessage(QWidget):
    """A single chat message bubble."""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setMaximumWidth(500)

        if is_user:
            bubble.setStyleSheet(
                "QLabel { background: #1a3a5c; color: #e0e0e0; padding: 10px 14px;"
                " border-radius: 12px; border-bottom-right-radius: 4px; }"
            )
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            bubble.setStyleSheet(
                "QLabel { background: #2d2d2d; color: #e0e0e0; padding: 10px 14px;"
                " border-radius: 12px; border-bottom-left-radius: 4px; }"
            )
            layout.addWidget(bubble)
            layout.addStretch()


class ChatPanel(BasePanel):
    """AI Chat panel for conversational file queries."""

    response_ready = Signal(str)

    def __init__(
        self,
        indexer: FileIndexer | None = None,
        app_state: AppState | None = None,
        event_bus: EventBus | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.indexer = indexer
        self.state = app_state
        self.event_bus = event_bus
        self._ai_provider = None
        self._pool = QThreadPool.globalInstance()
        self._setup_ui()
        self.response_ready.connect(self._on_response)

    def update_services(self, indexer=None, ai_provider=None):
        if indexer is not None:
            self.indexer = indexer
        if ai_provider is not None:
            self._ai_provider = ai_provider

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Title
        title = QLabel("AI File Assistant")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel(
            "Ask questions about your files in natural language.\n"
            'Examples: "Find large PDFs", "Show Python files modified today", '
            '"How many documents do I have?"'
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Chat history (scrollable)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)

        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_layout.setSpacing(4)
        self._chat_layout.addStretch()

        self._scroll.setWidget(self._chat_container)
        layout.addWidget(self._scroll, 1)

        # Input bar
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about your files...")
        self.input_field.setMinimumHeight(36)
        self.input_field.returnPressed.connect(self._on_send)
        input_layout.addWidget(self.input_field, 1)

        self.btn_send = QPushButton("Send")
        self.btn_send.setObjectName("btnPrimary")
        self.btn_send.setMinimumHeight(36)
        self.btn_send.clicked.connect(self._on_send)
        input_layout.addWidget(self.btn_send)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setMinimumHeight(36)
        self.btn_clear.clicked.connect(self._clear_chat)
        input_layout.addWidget(self.btn_clear)

        layout.addLayout(input_layout)

    def _add_message(self, text: str, is_user: bool = True):
        """Add a message bubble to the chat."""
        # Insert before the stretch
        idx = self._chat_layout.count() - 1
        msg = ChatMessage(text, is_user=is_user)
        self._chat_layout.insertWidget(idx, msg)
        # Scroll to bottom
        self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())

    @Slot()
    def _on_send(self):
        """Handle user message."""
        query = self.input_field.text().strip()
        if not query:
            return

        self.input_field.clear()
        self._add_message(query, is_user=True)
        self.btn_send.setEnabled(False)

        def process():
            response = self._process_query(query)
            self.response_ready.emit(response)

        worker = Worker(process)
        worker.signals.finished.connect(lambda _: None)
        self._pool.start(worker)

    @Slot()
    def _on_response(self, text: str):
        """Display AI response."""
        self._add_message(text, is_user=False)
        self.btn_send.setEnabled(True)

    def _process_query(self, query: str) -> str:
        """Process a user query — try local intent parsing first, then AI."""
        query_lower = query.lower()

        # Try local intent parsing (no AI needed for simple queries)
        result = self._try_local_query(query_lower, query)
        if result:
            return result

        # Try AI-powered response if provider available
        if self._ai_provider and self._ai_provider.is_available:
            return self._ai_query(query)

        return self._try_local_query_fallback(query_lower, query)

    def _try_local_query(self, query_lower: str, query: str) -> str | None:
        """Parse simple queries without AI."""
        if not self.indexer:
            return "No indexer available. Please build the index first."

        stats = self.indexer.get_stats()

        # "how many" queries
        if "how many" in query_lower or "count" in query_lower:
            if "file" in query_lower:
                return f"You have {stats['indexed_files']:,} indexed files ({stats.get('total_size_str', '?')})."
            for cat in ["pdf", "code", "image", "markdown", "video", "audio", "office"]:
                if cat in query_lower:
                    results = self.indexer.search_by_category(cat.capitalize(), limit=10000)
                    return f"You have {len(results)} {cat.capitalize()} files."

        # "find" / "show" / "search" queries
        if any(kw in query_lower for kw in ["find", "show", "search", "list"]):
            # Size-based queries
            if "large" in query_lower or "big" in query_lower:
                results = self.indexer.search_metadata(size_min=100 * 1024 * 1024, limit=10)
                if results:
                    lines = [f"Found {len(results)} large files (>100MB):"]
                    for r in results[:10]:
                        lines.append(f"  {r['filename']} ({r['size_str']})")
                    return "\n".join(lines)
                return "No files larger than 100MB found in the index."

            if "small" in query_lower:
                results = self.indexer.search_metadata(size_max=1024, limit=10)
                if results:
                    lines = [f"Found {len(results)} small files (<1KB):"]
                    for r in results[:10]:
                        lines.append(f"  {r['filename']} ({r['size_str']})")
                    return "\n".join(lines)
                return "No very small files found."

            # Category-based queries
            for cat in ["pdf", "code", "image", "markdown", "video", "audio", "document"]:
                if cat in query_lower:
                    results = self.indexer.search_by_category(cat.capitalize(), limit=20)
                    if results:
                        lines = [f"Found {len(results)} {cat} files:"]
                        for r in results[:10]:
                            lines.append(f"  {r['filename']} - {r.get('modified', '')}")
                        if len(results) > 10:
                            lines.append(f"  ... and {len(results) - 10} more")
                        return "\n".join(lines)
                    return f"No {cat} files found in the index."

            # Extension-based queries
            for ext in [".py", ".js", ".ts", ".pdf", ".md", ".docx", ".xlsx"]:
                if ext.lstrip(".") in query_lower:
                    results = self.indexer.search_by_extension(ext, limit=20)
                    if results:
                        lines = [f"Found {len(results)} {ext} files:"]
                        for r in results[:10]:
                            lines.append(f"  {r['filename']}")
                        return "\n".join(lines)

            # Full-text search fallback
            search_terms = (
                query_lower.replace("find", "")
                .replace("show", "")
                .replace("search", "")
                .replace("list", "")
                .strip()
            )
            if search_terms and len(search_terms) > 2:
                results = self.indexer.search(search_terms, limit=10)
                if results:
                    lines = [f"Found {len(results)} results for '{search_terms}':"]
                    for r in results[:10]:
                        lines.append(f"  {r['filename']} (match: {r['score']:.0%})")
                    return "\n".join(lines)

        return None

    def _try_local_query_fallback(self, query_lower: str, query: str) -> str:
        """Fallback when no AI is available."""
        if not self.indexer:
            return (
                "I can help you find files! But first, please:\n"
                "1. Open a folder\n"
                "2. Build the index (Index panel)\n\n"
                "Then ask me things like:\n"
                '- "How many PDF files do I have?"\n'
                '- "Find large files"\n'
                '- "Show Python files"'
            )

        # Try a general search
        results = self.indexer.search(query, limit=5)
        if results:
            lines = [f"I found {len(results)} files matching your query:"]
            for r in results:
                lines.append(f"  {r['filename']} ({r['size_str']}) - {r.get('modified', '')}")
            lines.append("\nTip: Configure an AI provider in Settings for smarter responses.")
            return "\n".join(lines)

        return (
            "I couldn't find files matching that query.\n\n"
            "Try:\n"
            '- "Find PDF files"\n'
            '- "Show large files"\n'
            '- "How many code files?"\n\n'
            "Tip: Configure an AI provider in Settings for natural language understanding."
        )

    def _ai_query(self, query: str) -> str:
        """Use AI provider to understand and respond to the query."""
        # Build context about indexed files
        stats = self.indexer.get_stats() if self.indexer else {}
        context = (
            f"You are a file management assistant. The user has {stats.get('indexed_files', 0)} "
            f"indexed files totaling {stats.get('total_size_str', 'unknown')}. "
            f"Help them find and manage their files. Be concise."
        )

        try:
            response = self._ai_provider.generate(
                prompt=query,
                system_prompt=context,
                temperature=0.3,
                max_tokens=500,
            )
            return response or "I couldn't generate a response. Please try again."
        except Exception as e:
            return f"AI error: {e}\n\nFalling back to local search..."

    @Slot()
    def _clear_chat(self):
        """Clear chat history."""
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
