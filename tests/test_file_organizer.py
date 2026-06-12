"""FileOrganizer unit tests"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from filepilot.core.file_organizer import (
    CategoryRule,
    DateRule,
    ExtensionRule,
    FileOrganizer,
    SizeRule,
)
from filepilot.core.file_scanner import FileInfo, FileScanner
from filepilot.utils.file_utils import FileCategory, is_file_locked


class TestFileLockDetection:
    """Tests for the standalone is_file_locked() helper in file_utils"""

    def test_unlocked_file_on_windows(self, tmp_path):
        """Accessible file returns (False, "") on Windows"""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        with patch("filepilot.utils.file_utils.sys.platform", "win32"):
            locked, msg = is_file_locked(f)
        assert locked is False
        assert msg == ""

    def test_locked_file_on_windows(self, tmp_path):
        """PermissionError simulates a locked file on Windows"""
        f = tmp_path / "locked.txt"
        f.write_text("locked")
        with (
            patch("filepilot.utils.file_utils.sys.platform", "win32"),
            patch("builtins.open", side_effect=PermissionError("locked by another process")),
        ):
            locked, msg = is_file_locked(f)
        assert locked is True
        assert "in use" in msg

    def test_nonexistent_file_on_windows(self, tmp_path):
        """Non-existent file returns (False, error_msg) on Windows"""
        f = tmp_path / "nonexistent.txt"
        with patch("filepilot.utils.file_utils.sys.platform", "win32"):
            locked, msg = is_file_locked(f)
        assert locked is False
        assert len(msg) > 0  # OSError message

    @pytest.mark.parametrize("platform", ["linux", "darwin", "cygwin"])
    def test_non_windows_always_unlocked(self, platform, tmp_path):
        """On non-Windows, is_file_locked always returns (False, "")"""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        with patch("filepilot.utils.file_utils.sys.platform", platform):
            locked, msg = is_file_locked(f)
        assert locked is False
        assert msg == ""

    def test_non_windows_ignores_locked_file(self, tmp_path):
        """Even a 'locked' file is reported as unlocked on non-Windows"""
        f = tmp_path / "locked.txt"
        f.write_text("locked")
        with patch("filepilot.utils.file_utils.sys.platform", "linux"):
            # open() is never called on non-Windows; lock check always returns False
            locked, msg = is_file_locked(f)
        assert locked is False
        assert msg == ""


class TestFileOrganizerLockHandling:
    """Tests for lock handling within FileOrganizer.organize()"""

    @pytest.fixture
    def scanner(self):
        return FileScanner()

    @pytest.fixture
    def organizer(self):
        return FileOrganizer()

    def test_locked_file_recorded_in_errors(self, scanner, organizer, tmp_path):
        """Locked file is recorded in organizer._errors"""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "report.pdf").write_bytes(b"%PDF-1.4")

        files = scanner.scan(src)

        with patch(
            "filepilot.core.file_organizer.is_file_locked",
            return_value=(True, "File is in use by another process: report.pdf"),
        ):
            organizer.organize(files, dst, dry_run=False)

        assert len(organizer._errors) >= 1
        assert any("report.pdf" in name for name, _ in organizer._errors)

    def test_unlocked_files_are_moved(self, scanner, organizer, tmp_path):
        """Unlocked files are actually moved to destination"""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "free.txt").write_text("free")

        files = scanner.scan(src)

        with patch("filepilot.core.file_organizer.is_file_locked", return_value=(False, "")):
            ops = organizer.organize(files, dst, dry_run=False)

        # Source file should be gone
        assert not (src / "free.txt").exists()
        # File should be somewhere under dst (CategoryRule places .txt in Documents/)
        assert len(list(dst.rglob("*.txt"))) == 1, (
            f"Expected 1 .txt file under dst, found: {list(dst.rglob('*'))}"
        )
        assert ops[0]["dry_run"] is False
        assert len(organizer._errors) == 0

    def test_locked_file_skipped_others_moved(self, scanner, organizer, tmp_path):
        """Locked file is skipped, other files are still moved"""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()

        (src / "locked.pdf").write_bytes(b"%PDF-1.4")
        (src / "free.txt").write_text("free")

        files = scanner.scan(src)

        # Use separate organize calls for each file to avoid side_effect issues
        # with @staticmethod patching
        free_file = next(f for f in files if f.name == "free.txt")
        locked_file = next(f for f in files if f.name == "locked.pdf")

        # free.txt should be movable (not locked)
        with patch("filepilot.core.file_organizer.is_file_locked", return_value=(False, "")):
            organizer.organize([free_file], dst, dry_run=False)

        # locked.pdf should be locked (error recorded, not moved)
        with patch("filepilot.core.file_organizer.is_file_locked", return_value=(True, "in use")):
            organizer.organize([locked_file], dst, dry_run=False)

        # free.txt should have been moved somewhere under dst
        moved_files = [p for p in dst.rglob("*") if p.is_file()]
        assert len(moved_files) == 1, (
            f"Expected 1 file moved under dst, found {len(moved_files)}: {moved_files}"
        )
        # locked.pdf should still be in source
        assert (src / "locked.pdf").exists(), "Locked file was incorrectly moved"
        # Error should be recorded about the locked file
        assert any("locked.pdf" in name for name, _ in organizer._errors)

    def test_dry_run_skips_lock_check(self, scanner, organizer, tmp_path):
        """In dry_run mode, is_file_locked is never called"""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "test.pdf").write_bytes(b"%PDF-1.4")

        files = scanner.scan(src)

        with patch("filepilot.core.file_organizer.is_file_locked") as mock_lock:
            organizer.organize(files, dst, dry_run=True)

        mock_lock.assert_not_called()

    def test_dry_run_returns_operations_without_moving(self, scanner, organizer, tmp_path):
        """Dry run returns operations but does not move files"""
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "test.pdf").write_bytes(b"%PDF-1.4")

        files = scanner.scan(src)
        ops = organizer.organize(files, dst, dry_run=True)

        # Should return operation metadata
        assert len(ops) == 1
        assert ops[0]["dry_run"] is True
        # File should NOT have been moved
        assert (src / "test.pdf").exists()
        assert len(list(dst.rglob("*"))) == 0

    def test_dry_run_resolves_conflicts_between_planned_destinations(self, organizer, tmp_path):
        """Dry run should not preview duplicate destinations for same-name files."""
        dst = tmp_path / "dst"
        now = datetime.now()
        files = [
            FileInfo(
                path=tmp_path / "a" / "same.txt",
                name="same.txt",
                extension=".txt",
                size_bytes=10,
                size_str="10 B",
                category=FileCategory.DOCUMENT,
                mime_type="text/plain",
                modified_time=now,
                created_time=now,
            ),
            FileInfo(
                path=tmp_path / "b" / "same.txt",
                name="same.txt",
                extension=".txt",
                size_bytes=20,
                size_str="20 B",
                category=FileCategory.DOCUMENT,
                mime_type="text/plain",
                modified_time=now,
                created_time=now,
            ),
        ]

        operations = organizer.organize(files, dst, dry_run=True)
        destinations = [Path(op["destination"]) for op in operations]

        assert destinations[0].name == "same.txt"
        assert destinations[1].name == "same_1.txt"
        assert len(set(destinations)) == 2

    def test_rename_pattern_with_ext_does_not_duplicate_extension(self, organizer, tmp_path):
        now = datetime.now()
        file_info = FileInfo(
            path=tmp_path / "report.txt",
            name="report.txt",
            extension=".txt",
            size_bytes=10,
            size_str="10 B",
            category=FileCategory.DOCUMENT,
            mime_type="text/plain",
            modified_time=now,
            created_time=now,
        )

        assert organizer._determine_filename(file_info, True, "{name}.{ext}") == "report.txt"

    def test_undo_renames_when_original_path_is_occupied(self, organizer, tmp_path):
        import json

        moved = tmp_path / "sorted" / "report.txt"
        original = tmp_path / "source" / "report.txt"
        moved.parent.mkdir()
        original.parent.mkdir()
        moved.write_text("restored", encoding="utf-8")
        original.write_text("new file", encoding="utf-8")
        undo_log = tmp_path / "undo.json"
        undo_log.write_text(
            json.dumps([{"source": str(original), "dest": str(moved)}]),
            encoding="utf-8",
        )

        result = organizer.undo(undo_log)

        assert result == {"restored": 1, "errors": 0}
        assert original.read_text(encoding="utf-8") == "new file"
        assert (original.parent / "report_1.txt").read_text(encoding="utf-8") == "restored"


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
