"""pytest configuration — shared fixtures and pytest-qt support"""

import os
import sys
from pathlib import Path

import pytest

# Configure Qt before any test module imports PySide6. Linux CI has shown
# occasional PySide teardown segfaults when Qt picks the xcb backend under Xvfb.
if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")


def pytest_sessionfinish(session, exitstatus):
    """Drain Qt work and close top-level widgets before interpreter teardown."""
    try:
        from PySide6.QtCore import QThreadPool
        from PySide6.QtWidgets import QApplication
    except Exception:
        return

    app = QApplication.instance()
    if app is None:
        return

    QThreadPool.globalInstance().waitForDone(5000)
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    app.processEvents()


@pytest.fixture(scope="session")
def qapp_class():
    """Provide QApplication subclass for pytest-qt"""
    from PySide6.QtWidgets import QApplication

    return QApplication


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with test files"""
    root = tmp_path

    # Create various test file types
    (root / "test_doc.txt").write_text("This is a test document for AI summarization.")
    (root / "readme.md").write_text("# Project Title\n\nThis is a sample markdown file.")
    (root / "script.py").write_text(
        "# script.py\n"
        "def hello():\n"
        '    """Say hello"""\n'
        "    print('Hello, World!')\n"
        "\n"
        "class Calculator:\n"
        "    def add(self, a, b):\n"
        "        return a + b\n",
    )
    (root / "notes.pdf").write_bytes(b"%PDF-1.4 dummy pdf content for testing")
    (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    # Subdirectory files
    sub = root / "subfolder"
    sub.mkdir()
    (sub / "nested.md").write_text("## Nested File\n\nContent in subfolder.")

    return root
