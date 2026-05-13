"""FileOrganizer 单元测试"""

import tempfile
from pathlib import Path

import pytest

from filepilot.core.file_organizer import (
    CategoryRule,
    DateRule,
    ExtensionRule,
    FileOrganizer,
    SizeRule,
)
from filepilot.core.file_scanner import FileScanner


class TestFileOrganizer:
    """FileOrganizer 测试"""

    @pytest.fixture
    def source_dir(self):
        """创建源目录"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "report.pdf").write_bytes(b"%PDF-1.4")
            (root / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0")
            (root / "script.py").write_text("print('hello')")
            (root / "notes.md").write_text("# Notes")
            yield root

    @pytest.fixture
    def target_dir(self):
        """创建目标目录"""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_category_rule(self):
        """测试分类规则"""
        scanner = FileScanner()
        files = scanner.scan(Path(tempfile.mkdtemp()), recursive=False)
        # 创建临时文件来测试
        import tempfile, pathlib
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
        """测试日期规则"""
        import tempfile, pathlib
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            path = pathlib.Path(f.name)

        try:
            scanner = FileScanner()
            files = scanner.scan(path.parent)
            rule = DateRule()
            txt_file = next(f for f in files if f.name == path.name)
            target = rule.apply(txt_file)
            # 格式: YYYY/MM月
            import re
            assert re.match(r"\d{4}/\d{2}月", target)
        finally:
            path.unlink()

    def test_extension_rule(self):
        """测试扩展名规则"""
        rule = ExtensionRule()

        import tempfile, pathlib
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
        """测试大小规则"""
        import tempfile, pathlib
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
