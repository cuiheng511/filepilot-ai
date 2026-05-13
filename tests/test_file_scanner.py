"""FileScanner Unit Tests"""

import tempfile
from pathlib import Path

import pytest

from filepilot.core.file_scanner import FileScanner
from filepilot.utils.file_utils import FileCategory


class TestFileScanner:
    """FileScanner test suite"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory structure"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # Create some test files
            (root / "test.txt").write_text("hello world")
            (root / "test.py").write_text("print('hello')")
            (root / "test.md").write_text("# Title\ncontent")
            (root / "test.pdf").write_bytes(b"%PDF-1.4 test")
            (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (root / "sub").mkdir()
            (root / "sub" / "nested.txt").write_text("nested file")

            yield root

    def test_scan_basic(self, temp_dir):
        """Test basic scan"""
        scanner = FileScanner()
        files = scanner.scan(temp_dir)

        assert len(files) >= 5
        paths = [f.name for f in files]
        assert "test.txt" in paths
        assert "test.py" in paths
        assert "test.md" in paths

    def test_scan_non_recursive(self, temp_dir):
        """Test non-recursive scan"""
        scanner = FileScanner()
        files = scanner.scan(temp_dir, recursive=False)

        names = [f.name for f in files]
        assert "test.txt" in names
        # Files in subdirectory should not appear
        assert "nested.txt" not in names

    def test_file_info_fields(self, temp_dir):
        """Test FileInfo field correctness"""
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
        """Test file type detection"""
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
        """Test quick scan limit"""
        scanner = FileScanner()
        files = scanner.quick_scan(temp_dir, max_files=2)
        assert len(files) <= 2

    def test_scan_nonexistent(self):
        """Test scanning non-existent path"""
        scanner = FileScanner()
        with pytest.raises(FileNotFoundError):
            scanner.scan("/nonexistent/path")

    def test_progress_callback(self, temp_dir):
        """Test progress callback"""
        scanner = FileScanner()
        progress_updates = []

        def callback(count, path):
            progress_updates.append((count, path))

        scanner.scan(temp_dir, progress_callback=callback)
        assert len(progress_updates) > 0
        assert progress_updates[-1][0] > 0

    def test_stats(self, temp_dir):
        """Test statistics"""
        scanner = FileScanner()
        scanner.scan(temp_dir)
        stats = scanner.stats

        assert stats["scanned_count"] > 0
        assert stats["total_size"] > 0
        assert stats["total_size_str"].endswith("B")
