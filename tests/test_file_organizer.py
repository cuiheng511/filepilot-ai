"""FileOrganizer unit tests"""

import tempfile
from pathlib import Path

import pytest

from filepilot.core.file_organizer import (
    CategoryRule,
    DateRule,
    ExtensionRule,
    SizeRule,
)
from filepilot.core.file_scanner import FileScanner


class TestFileOrganizer:
    """FileOrganizer test suite"""

    @pytest.fixture
    def source_dir(self):
        """Create source directory with test files"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "report.pdf").write_bytes(b"%PDF-1.4")
            (root / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0")
            (root / "script.py").write_text("print('hello')")
            (root / "notes.md").write_text("# Notes")
            yield root

    @pytest.fixture
    def target_dir(self):
        """Create target directory"""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_category_rule(self):
        """Test category classification rule"""
        import pathlib
        import tempfile
        scanner = FileScanner()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF")
            path = pathlib.Path(f.name)

        try:
            files = scanner.scan(path.parent)
            rule = CategoryRule()
            pdf_file = next(f for f in files if f.extension == ".pdf")
            target = rule.apply(pdf_file)
            assert target == "PDF"
        finally:
            path.unlink()

    def test_date_rule(self):
        """Test date-based classification rule"""
        import pathlib
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            path = pathlib.Path(f.name)

        try:
            scanner = FileScanner()
            files = scanner.scan(path.parent)
            rule = DateRule()
            txt_file = next(f for f in files if f.name == path.name)
            target = rule.apply(txt_file)
            # Format: YYYY/MM
            import re
            assert re.match(r"\d{4}/\d{2}", target)
        finally:
            path.unlink()

    def test_extension_rule(self):
        """Test extension-based classification rule"""
        rule = ExtensionRule()

        import pathlib
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".PYTHON", delete=False) as f:
            f.write(b"test")
            path = pathlib.Path(f.name)

        try:
            scanner = FileScanner()
            files = scanner.scan(path.parent)
            py_file = next(f for f in files if f.name == path.name)
            target = rule.apply(py_file)
            assert target == "PYTHON"
        finally:
            path.unlink()

    def test_size_rule(self):
        """Test size-based classification rule"""
        import pathlib
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"x" * 100)
            path = pathlib.Path(f.name)

        try:
            scanner = FileScanner()
            files = scanner.scan(path.parent)
            rule = SizeRule()
            txt_file = next(f for f in files if f.name == path.name)
            target = rule.apply(txt_file)
            assert target is not None
        finally:
            path.unlink()
