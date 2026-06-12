"""First-run onboarding for FilePilot."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class OnboardingDialog(QDialog):
    """Small, non-blocking welcome dialog shown on first launch."""

    open_folder_requested = Signal()
    open_settings_requested = Signal()
    completed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to FilePilot AI")
        self.setMinimumSize(560, 420)
        self.setObjectName("OnboardingDialog")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Welcome to FilePilot AI")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(
            "Start with a local folder, then scan, search, summarize, deduplicate, "
            "or let an MCP agent work inside the folders you explicitly allow."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("onboardingSubtitle")
        layout.addWidget(subtitle)

        steps = [
            ("1. Choose a folder", "Open a local directory. FilePilot never needs a cloud sync."),
            (
                "2. Build local context",
                "Scan files, build a searchable index, and review duplicates.",
            ),
            (
                "3. Add AI only when useful",
                "Use local models by default, or configure a cloud provider yourself.",
            ),
            (
                "4. Keep agents scoped",
                "MCP access is limited to allowed folders, with write actions disabled by default.",
            ),
        ]
        for heading, body in steps:
            layout.addWidget(self._make_step(heading, body))

        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.skip_button = QPushButton("Skip for now")
        self.settings_button = QPushButton("Open Settings")
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("btnPrimary")
        buttons.addWidget(self.skip_button)
        buttons.addWidget(self.settings_button)
        buttons.addWidget(self.open_folder_button)
        layout.addLayout(buttons)

        self.skip_button.clicked.connect(self._complete)
        self.settings_button.clicked.connect(self._open_settings)
        self.open_folder_button.clicked.connect(self._open_folder)

    def _make_step(self, heading: str, body: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("onboardingStep")
        step_layout = QVBoxLayout(frame)
        step_layout.setContentsMargins(12, 10, 12, 10)
        step_layout.setSpacing(4)

        heading_label = QLabel(heading)
        heading_font = QFont()
        heading_font.setBold(True)
        heading_label.setFont(heading_font)

        body_label = QLabel(body)
        body_label.setWordWrap(True)

        step_layout.addWidget(heading_label)
        step_layout.addWidget(body_label)
        return frame

    def _complete(self) -> None:
        self.completed.emit()
        self.accept()

    def _open_settings(self) -> None:
        self.completed.emit()
        QTimer.singleShot(0, self.open_settings_requested.emit)
        self.accept()

    def _open_folder(self) -> None:
        self.completed.emit()
        QTimer.singleShot(0, self.open_folder_requested.emit)
        self.accept()
