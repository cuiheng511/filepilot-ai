"""Tests for filepilot.utils.file_utils — FileCategory, hashing, path utilities"""

from pathlib import Path

from filepilot.utils.file_utils import (
    FileCategory,
    compute_file_hash,
    get_file_category,
    get_file_size_str,
    get_file_extension,
    is_file_locked,
    normalize_path,
    safe_filename,
)


class TestFileCategory:
    def test_has_all_categories(self):
        assert len(FileCategory) == 14
        names = [c.name for c in FileCategory]
        assert "DOCUMENT" in names
        assert "CODE" in names
        assert "PDF" in names

    def test_category_extensions(self):
        pdf = FileCategory.PDF
        assert ".pdf" in pdf.extensions
        code = FileCategory.CODE
        assert ".py" in code.extensions
        assert ".js" in code.extensions

    def test_category_icons(self):
        assert FileCategory.IMAGE.icon == "🖼️"
        assert FileCategory.ARCHIVE.icon == "🗜️"
        assert FileCategory.UNKNOWN.icon == "❓"

    def test_unknown_has_no_extensions(self):
        assert FileCategory.UNKNOWN.extensions == set()


class TestGetFileCategory:
    def test_pdf(self):
        assert get_file_category("doc.pdf") == FileCategory.PDF

    def test_code(self):
        assert get_file_category("script.py") == FileCategory.CODE
        assert get_file_category("app.ts") == FileCategory.CODE

    def test_image(self):
        assert get_file_category("photo.jpg") == FileCategory.IMAGE

    def test_unknown(self):
        assert get_file_category("file.xyz") == FileCategory.UNKNOWN

    def test_no_extension(self):
        assert get_file_category("README") == FileCategory.UNKNOWN


class TestGetFileSizeStr:
    def test_bytes(self):
        assert get_file_size_str(0) == "0 B"
        assert get_file_size_str(500) == "500.0 B"

    def test_kb(self):
        assert get_file_size_str(1024) == "1.0 KB"
        assert get_file_size_str(2048) == "2.0 KB"

    def test_mb(self):
        assert get_file_size_str(1048576) == "1.0 MB"

    def test_gb(self):
        assert get_file_size_str(1073741824) == "1.0 GB"

    def test_large(self):
        result = get_file_size_str(1099511627776)
        assert "TB" in result


class TestSafeFilename:
    def test_removes_path_chars(self):
        assert "/" not in safe_filename("a/b")
        assert "\\" not in safe_filename("a\\b")

    def test_preserves_normal(self):
        assert safe_filename("hello.txt") == "hello.txt"

    def test_empty_string(self):
        assert safe_filename("") == "untitled"


class TestGetFileExtension:
    def test_normal(self):
        assert get_file_extension("file.txt") == ".txt"

    def test_no_extension(self):
        assert get_file_extension("README") == ""

    def test_multiple_dots(self):
        assert get_file_extension("archive.tar.gz") == ".gz"

    def test_path_object(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("")
        assert get_file_extension(f) == ".py"


class TestNormalizePath:
    def test_returns_absolute(self):
        result = normalize_path(".")
        assert result.is_absolute()

    def test_resolves_relative(self):
        result = normalize_path(".")
        assert result.is_absolute()

    def test_preserves_absolute(self):
        result = normalize_path("C:\\Windows" if Path("C:\\Windows").exists() else "/tmp")
        assert result.is_absolute()


class TestComputeFileHash:
    def test_sha256(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"hello world")
        h = compute_file_hash(str(f))
        assert len(h) == 64
        assert isinstance(h, str)

    def test_md5(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"test data")
        h = compute_file_hash(str(f), algorithm="md5")
        assert len(h) == 32

    def test_nonexistent_file(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist.bin"
        import pytest
        with pytest.raises(FileNotFoundError):
            compute_file_hash(str(nonexistent))


class TestIsFileLocked:
    def test_nonexistent(self):
        locked, _ = is_file_locked(Path("/nonexistent"))
        assert locked is False

    def test_unlocked_file(self, tmp_path):
        f = tmp_path / "free.txt"
        f.write_text("hello")
        locked, _ = is_file_locked(f)
        assert locked is False
