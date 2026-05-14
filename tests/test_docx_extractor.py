"""Tests for DocxExtractor"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from filepilot.extractors.docx_extractor import DocxExtractor


class TestDocxExtractor:
    def setup_method(self):
        self.extractor = DocxExtractor()

    def test_supported_extensions(self):
        assert ".docx" in DocxExtractor.SUPPORTED_EXTENSIONS

    def test_extract_text_no_python_docx(self):
        """When python-docx is not installed, return empty string"""
        with patch.dict("sys.modules", {"docx": None}):
            text = self.extractor.extract_text("/mock/doc.docx")
            assert text == ""

    @patch.dict("sys.modules", {"docx": MagicMock()})
    def test_extract_text_success(self):
        """Test text extraction with mocked python-docx"""
        mock_docx = sys.modules["docx"]
        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            MagicMock(text="Title Paragraph"),
            MagicMock(text=""),
            MagicMock(text="Second paragraph with content."),
        ]
        mock_doc.tables = [
            MagicMock(rows=[
                MagicMock(cells=[MagicMock(text="A"), MagicMock(text="B")]),
                MagicMock(cells=[MagicMock(text="1"), MagicMock(text="2")]),
            ])
        ]
        mock_docx.Document.return_value = mock_doc

        text = self.extractor.extract_text("/mock/doc.docx")
        assert "Title Paragraph" in text
        assert "Second paragraph with content." in text
        assert "A | B" in text
        assert "1 | 2" in text

    def test_extract_metadata_no_python_docx(self):
        with patch.dict("sys.modules", {"docx": None}):
            meta = self.extractor.extract_metadata("/mock/doc.docx")
            assert meta == {}

    @patch.dict("sys.modules", {"docx": MagicMock()})
    def test_extract_metadata_success(self):
        mock_docx = sys.modules["docx"]
        mock_doc = MagicMock()
        mock_doc.paragraphs = [MagicMock(text="p1"), MagicMock(text="p2")]
        mock_doc.tables = [MagicMock(), MagicMock()]
        mock_doc.core_properties.title = "Test Doc"
        mock_doc.core_properties.author = "Author Name"
        mock_doc.core_properties.subject = "Subject"
        mock_docx.Document.return_value = mock_doc

        meta = self.extractor.extract_metadata("/mock/doc.docx")
        assert meta["title"] == "Test Doc"
        assert meta["author"] == "Author Name"
        assert meta["subject"] == "Subject"
        assert meta["paragraphs"] == 2
        assert meta["tables"] == 2
