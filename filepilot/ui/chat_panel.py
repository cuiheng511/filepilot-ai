"""AI Chat Panel — conversational file assistant.

Users can ask natural language questions like:
- "Find PDF files modified last week"
- "Show me the largest files in Downloads"
- "How many Python files do I have?"

The AI parses intent and executes searches/actions via the indexer.
"""

from typing import cast

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
from filepilot.core.chat_assistant import FileQueryIndexer, process_file_query
from filepilot.core.event_bus import EventBus
from filepilot.core.indexer import FileIndexer
from filepilot.core.worker import Worker
from filepilot.i18n import t
from filepilot.ui.base_panel import BasePanel


class ChatMessage(QWidget):
    """A single chat message bubble."""

    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("chatMessage")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        bubble = QLabel(text)
        bubble.setObjectName("chatBubble")
        bubble.setProperty("role", "user" if is_user else "assistant")
        bubble.setAccessibleName(t("chat_user_message") if is_user else t("chat_assistant_message"))
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setMaximumWidth(500)

        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
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
        title = QLabel(t("chat_title"))
        title.setObjectName("sectionTitle")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel(t("chat_desc"))
        desc.setObjectName("sectionDesc")
        desc.setWordWrap(True)
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
        self.input_field.setPlaceholderText(t("chat_placeholder"))
        self.input_field.setAccessibleName(t("chat_input_accessible"))
        self.input_field.setMinimumHeight(36)
        self.input_field.returnPressed.connect(self._on_send)
        input_layout.addWidget(self.input_field, 1)

        self.btn_send = QPushButton(t("chat_send"))
        self.btn_send.setObjectName("btnPrimary")
        self.btn_send.setAccessibleName(t("chat_send"))
        self.btn_send.setMinimumHeight(36)
        self.btn_send.clicked.connect(self._on_send)
        input_layout.addWidget(self.btn_send)

        self.btn_clear = QPushButton(t("clear"))
        self.btn_clear.setAccessibleName(t("chat_clear_accessible"))
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
        indexer = cast("FileQueryIndexer | None", self.indexer)
        return process_file_query(query, indexer, self._ai_provider)

    @Slot()
    def _clear_chat(self):
        """Clear chat history."""
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
