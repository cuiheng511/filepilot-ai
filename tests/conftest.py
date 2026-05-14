"""pytest configuration — shared fixtures and pytest-qt support"""

from pathlib import Path

import pytest


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
