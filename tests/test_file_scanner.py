"""FileScanner 单元测试"""

import os
import tempfile
from pathlib import Path

import pytest

from filepilot.core.file_scanner import FileScanner, FileInfo
from filepilot.utils.file_utils import FileCategory


class TestFileScanner:
    """FileScanner 测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录结构"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # 创建一些测试文件
            (root / "test.txt").write_text("hello world")
            (root / "test.py").write_text("print('hello')")
            (root / "test.md").write_text("# Title\ncontent")
            (root / "test.pdf").write_bytes(b"%PDF-1.4 test")
            (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "sub").mkdir()
            (root / "sub" / "nested.txt").write_text("nested file")

            yield root

    def test_scan_basic(self, temp_dir):
        """测试基本扫描"""
        scanner = FileScanner()
        files = scanner.scan(temp_dir)

        assert len(files) >= 5
        paths = [f.name for f in files]
        assert "test.txt" in paths
        assert "test.py" in paths
        assert "test.md" in paths

    def test_scan_non_recursive(self, temp_dir):
        """测试非递归扫描"""
        scanner = FileScanner()
        files = scanner.scan(temp_dir, recursive=False)

        names = [f.name for f in files]
        assert "test.txt" in names
        # 子目录的文件不应出现
        assert "nested.txt" not in names

    def test_file_info_fields(self, temp_dir):
        """测试 FileInfo 字段正确性"""
        scanner = FileScanner()
        files = scanner.scan(temp_dir)
        txt_file = next(f for f in files if f.name == "test.txt")

        assert txt_file.extension == ".txt"
        assert txt_file.size_bytes > 0
        assert txt_file.size_str.endswith("B")
        assert txt_file.category == FileCategory.DOCUMENT
        assert not txt_file.is_directory
        assert txt_file.modified_time is not None

    def test_category_detection(self, temp_dir):
        """测试文件类型识别"""
        scanner = FileScanner()
        files = scanner.scan(temp_dir)

        for f in files:
            if f.extension == ".py":
                assert f.category == FileCategory.CODE
            elif f.extension == ".md":
                assert f.category == FileCategory.MARKDOWN
            elif f.extension == ".pdf":
                assert f.category == FileCategory.PDF
            elif f.extension == ".png":
                assert f.category == FileCategory.IMAGE

    def test_quick_scan_limit(self, temp_dir):
        """测试快速扫描限制"""
        scanner = FileScanner()
        files = scanner.quick_scan(temp_dir, max_files=2)
        assert len(files) <= 2

    def test_scan_nonexistent(self):
        """测试扫描不存在的路径"""
        scanner = FileScanner()
        with pytest.raises(FileNotFoundError):
            scanner.scan("/nonexistent/path")

    def test_progress_callback(self, temp_dir):
        """测试进度回调"""
        scanner = FileScanner()
        progress_updates = []

        def callback(count, path):
            progress_updates.append((count, path))

        scanner.scan(temp_dir, progress_callback=callback)
        assert len(progress_updates) > 0
        assert progress_updates[-1][0] > 0

    def test_stats(self, temp_dir):
        """测试统计信息"""
        scanner = FileScanner()
        scanner.scan(temp_dir)
        stats = scanner.stats

        assert stats["scanned_count"] > 0
        assert stats["total_size"] > 0
        assert stats["total_size_str"].endswith("B")
