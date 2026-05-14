"""Tests for file_browser extension categorization

Tests the module-level get_category_name() function and CAT_* constants
to ensure every defined extension maps to the correct category.
"""

import pytest

from filepilot.utils.file_utils import (
    CAT_AUDIO,
    CAT_CODE,
    CAT_IMAGE,
    CAT_MARKDOWN,
    CAT_OFFICE,
    CAT_PDF,
    CAT_TEXT,
    CAT_VIDEO,
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
            ".py", ".js", ".ts", ".tsx", ".jsx",
            ".java", ".cpp", ".c", ".h", ".hpp",
            ".cs", ".go", ".rs", ".rb", ".php",
            ".swift", ".kt", ".scala", ".sql",
            ".sh", ".bash", ".ps1", ".lua",
        }
        assert expected == CAT_CODE

    def test_cat_image_contents(self):
        assert {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"} == CAT_IMAGE

    def test_cat_office_contents(self):
        assert {".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"} == CAT_OFFICE

    def test_cat_text_contents(self):
        expected = {
            ".txt", ".log", ".cfg", ".ini", ".conf",
            ".yaml", ".yml", ".toml", ".json", ".xml",
        }
        assert expected == CAT_TEXT

    def test_cat_video_contents(self):
        assert {".mp4", ".avi", ".mov", ".mkv"} == CAT_VIDEO

    def test_cat_audio_contents(self):
        assert {".mp3", ".wav", ".flac"} == CAT_AUDIO

    def test_sets_are_disjoint(self):
        """No extension should belong to more than one category"""
        all_sets = [CAT_PDF, CAT_MARKDOWN, CAT_CODE, CAT_IMAGE, CAT_VIDEO, CAT_AUDIO, CAT_OFFICE, CAT_TEXT]
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

    @pytest.mark.parametrize("ext", [
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
    ])
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
