"""pytest 配置 — 共享 fixtures 和 pytest-qt 支持"""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
@pytest.fixture(scope="session")
def qapp_class():
    """为 pytest-qt 提供 QApplication 子类"""
    from PySide6.QtWidgets import QApplication
    return QApplication


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """创建含测试文件的临时目录"""
    root = tmp_path

    # 创建各种类型的测试文件
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
        "        return a + b\n"
    )
    (root / "notes.pdf").write_bytes(b"%PDF-1.4 dummy pdf content for testing")
    (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    # 子目录文件
    sub = root / "subfolder"
    sub.mkdir()
    (sub / "nested.md").write_text("## Nested File\n\nContent in subfolder.")

    return root
