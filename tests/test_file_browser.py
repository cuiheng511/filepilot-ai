"""Tests for file_browser — extension categorization, export, and filter bar"""

import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from filepilot.core.file_scanner import FileInfo
from filepilot.utils.file_utils import (
    CAT_AUDIO,
    CAT_CODE,
    CAT_IMAGE,
    CAT_MARKDOWN,
    CAT_OFFICE,
    CAT_PDF,
    CAT_TEXT,
    CAT_VIDEO,
    FileCategory,
    get_category_name,
)


class TestExtensionConstants:
    """Verify CAT_* sets contain the expected extensions"""

    def test_cat_pdf_contents(self):
        assert {".pdf"} == CAT_PDF

    def test_cat_markdown_contents(self):
        assert {".md", ".markdown", ".mdx", ".rst"} == CAT_MARKDOWN

    def test_cat_code_contents(self):
        expected = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".sql",
            ".sh",
            ".bash",
            ".ps1",
            ".lua",
        }
        assert expected == CAT_CODE

    def test_cat_image_contents(self):
        assert {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"} == CAT_IMAGE

    def test_cat_office_contents(self):
        assert {".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"} == CAT_OFFICE

    def test_cat_text_contents(self):
        expected = {
            ".txt",
            ".log",
            ".cfg",
            ".ini",
            ".conf",
            ".yaml",
            ".yml",
            ".toml",
            ".json",
            ".xml",
        }
        assert expected == CAT_TEXT

    def test_cat_video_contents(self):
        assert {".mp4", ".avi", ".mov", ".mkv"} == CAT_VIDEO

    def test_cat_audio_contents(self):
        assert {".mp3", ".wav", ".flac"} == CAT_AUDIO

    def test_sets_are_disjoint(self):
        """No extension should belong to more than one category"""
        all_sets = [
            CAT_PDF,
            CAT_MARKDOWN,
            CAT_CODE,
            CAT_IMAGE,
            CAT_VIDEO,
            CAT_AUDIO,
            CAT_OFFICE,
            CAT_TEXT,
        ]
        for i, s1 in enumerate(all_sets):
            for j, s2 in enumerate(all_sets):
                if i < j:
                    assert s1.isdisjoint(s2), f"Sets {i} and {j} overlap: {s1 & s2}"


class TestGetCategory:
    """Verify get_category_name returns the correct category for each extension"""

    @staticmethod
    def known_extensions():
        """Generate (extension, expected_category) pairs from CAT_* constants"""
        cases = []
        for ext in CAT_PDF:
            cases.append((ext, "PDF"))
        for ext in CAT_MARKDOWN:
            cases.append((ext, "Markdown"))
        for ext in CAT_CODE:
            cases.append((ext, "Code"))
        for ext in CAT_IMAGE:
            cases.append((ext, "Image"))
        for ext in CAT_OFFICE:
            cases.append((ext, "Office"))
        for ext in CAT_TEXT:
            cases.append((ext, "Text"))
        for ext in CAT_VIDEO:
            cases.append((ext, "Video"))
        for ext in CAT_AUDIO:
            cases.append((ext, "Audio"))
        return cases

    @pytest.mark.parametrize(("ext", "expected"), known_extensions())
    def test_known_extension(self, ext: str, expected: str):
        assert get_category_name(ext) == expected

    @pytest.mark.parametrize(
        "ext",
        [
            ".exe",
            ".dll",
            ".so",
            ".dmg",
            ".zip",
            ".tar",
            ".gz",
            ".wma",
            ".webm",
            ".flv",
            "",
            ".noext",
        ],
    )
    def test_unknown_extension_returns_other(self, ext: str):
        assert get_category_name(ext) == "Other"

    def test_case_insensitivity(self):
        """Extensions with mixed/upper case should still match"""
        assert get_category_name(".PY") == "Code"
        assert get_category_name(".Pdf") == "PDF"
        assert get_category_name(".MD") == "Markdown"
        assert get_category_name(".JPG") == "Image"
        assert get_category_name(".DOCX") == "Office"
        assert get_category_name(".YAML") == "Text"
        assert get_category_name(".MP4") == "Video"
        assert get_category_name(".MP3") == "Audio"


class TestFileBrowserExport:
    """Verify file list export uses FileInfo fields correctly."""

    @pytest.fixture
    def file_info(self, tmp_path: Path) -> FileInfo:
        now = datetime.now()
        path = tmp_path / "report.txt"
        return FileInfo(
            path=path,
            name=path.name,
            extension=".txt",
            size_bytes=12,
            size_str="12 B",
            category=FileCategory.DOCUMENT,
            mime_type="text/plain",
            modified_time=now,
            created_time=now,
        )

    def test_export_json_uses_extension(self, qtbot, monkeypatch, tmp_path, file_info):
        from filepilot.ui.file_browser import FileBrowserPanel, QFileDialog

        export_path = tmp_path / "files.json"
        panel = FileBrowserPanel()
        qtbot.addWidget(panel)
        panel.files = [file_info]
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            lambda *args, **kwargs: (str(export_path), "JSON (*.json)"),
        )

        panel._on_export()

        data = json.loads(export_path.read_text(encoding="utf-8"))
        assert data[0]["suffix"] == ".txt"

    def test_export_csv_uses_extension(self, qtbot, monkeypatch, tmp_path, file_info):
        from filepilot.ui.file_browser import FileBrowserPanel, QFileDialog

        export_path = tmp_path / "files.csv"
        panel = FileBrowserPanel()
        qtbot.addWidget(panel)
        panel.files = [file_info]
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            lambda *args, **kwargs: (str(export_path), "CSV (*.csv)"),
        )

        panel._on_export()

        rows = list(csv.reader(export_path.read_text(encoding="utf-8").splitlines()))
        assert rows[1][-1] == ".txt"


class TestFilterBar:
    """Filter bar unit tests — _get_filtered_files logic."""

    @pytest.fixture(autouse=True)
    def _setup(self, qtbot):
        from filepilot.ui.file_browser import FileBrowserPanel

        self.panel = FileBrowserPanel()
        qtbot.addWidget(self.panel)
        now = datetime.now()
        self.files = [
            FileInfo(
                path=Path(f"/tmp/{name}"),
                name=name,
                extension=Path(name).suffix,
                size_bytes=size,
                size_str=f"{size} B",
                category=FileCategory[cat.upper()] if cat else FileCategory.UNKNOWN,
                mime_type="",
                modified_time=now,
                created_time=now,
            )
            for name, size, cat in [
                ("doc.pdf", 500, "PDF"),
                ("photo.png", 2_000_000, "IMAGE"),
                ("video.mp4", 50_000_000, "VIDEO"),
                ("script.py", 100, "CODE"),
                ("notes.txt", 5_000_000, "DOCUMENT"),
            ]
        ]
        self.panel.files = self.files

    def test_filter_all_types(self):
        self.panel.filter_type.setCurrentText("All Types")
        result = self.panel._get_filtered_files()
        assert len(result) == 5

    def test_filter_by_pdf_type(self):
        self.panel.filter_type.setCurrentText("PDF")
        result = self.panel._get_filtered_files()
        assert len(result) == 1
        assert "pdf" in result[0].name

    def test_filter_by_office_type(self):
        self.panel.filter_type.setCurrentText("Office")
        result = self.panel._get_filtered_files()
        assert len(result) == 0  # no Office files in fixture

    def test_filter_by_text_type(self):
        self.panel.filter_type.setCurrentText("Text")
        result = self.panel._get_filtered_files()
        assert len(result) == 1
        assert "txt" in result[0].name

    def test_filter_by_image_type(self):
        self.panel.filter_type.setCurrentText("Image")
        result = self.panel._get_filtered_files()
        assert all("png" in f.name for f in result)

    def test_filter_by_code_type(self):
        self.panel.filter_type.setCurrentText("Code")
        result = self.panel._get_filtered_files()
        assert all("py" in f.name for f in result)

    def test_filter_small_size(self):
        self.panel.filter_size.setCurrentText("< 1 MB")
        result = self.panel._get_filtered_files()
        assert all(f.size_bytes < 1_048_576 for f in result)

    def test_filter_large_size(self):
        self.panel.filter_size.setCurrentText("> 100 MB")
        result = self.panel._get_filtered_files()
        assert all(f.size_bytes >= 104_857_600 for f in result)

    def test_filter_size_10_100(self):
        self.panel.filter_size.setCurrentText("10–100 MB")
        result = self.panel._get_filtered_files()
        assert all(10_485_760 <= f.size_bytes < 104_857_600 for f in result)

    def test_filter_date_today(self):
        self.panel.filter_date.setCurrentText("Today")
        result = self.panel._get_filtered_files()
        assert len(result) == 5  # all have now() modified_time

    def test_filter_type_and_size_combo(self):
        self.panel.filter_type.setCurrentText("Image")
        self.panel.filter_size.setCurrentText("< 1 MB")
        result = self.panel._get_filtered_files()
        # photo.png is 2MB, so should be excluded by size
        assert len(result) == 0

    def test_filter_count_label_updated(self):
        self.panel.filter_type.setCurrentText("Code")
        self.panel._apply_filter()
        text = self.panel.filter_count.text()
        assert "(1 shown)" in text or "1" in text

    def test_hidden_files_filtered_when_unchecked(self):
        hidden = FileInfo(
            path=Path("/tmp/.hidden.txt"),
            name=".hidden.txt",
            extension=".txt",
            size_bytes=50,
            size_str="50 B",
            category=FileCategory.DOCUMENT,
            mime_type="",
            modified_time=datetime.now(),
            created_time=datetime.now(),
        )
        self.panel.files.append(hidden)
        self.panel.cb_show_hidden.setChecked(False)
        result = self.panel._get_filtered_files()
        assert not any(f.name.startswith(".") for f in result)

    def test_hidden_files_included_when_checked(self):
        from pathlib import Path

        hidden = FileInfo(
            path=Path("/tmp/.secret.pdf"),
            name=".secret.pdf",
            extension=".pdf",
            size_bytes=100,
            size_str="100 B",
            category=FileCategory.PDF,
            mime_type="",
            modified_time=datetime.now(),
            created_time=datetime.now(),
        )
        self.panel.files.append(hidden)
        self.panel.cb_show_hidden.setChecked(True)
        result = self.panel._get_filtered_files()
        assert any(f.name.startswith(".") for f in result)
