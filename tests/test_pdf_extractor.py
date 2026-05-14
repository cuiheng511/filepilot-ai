"""Tests for PDFExtractor"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from filepilot.extractors.pdf_extractor import PDFExtractor


class TestPDFExtractor:
    def setup_method(self):
        self.extractor = PDFExtractor()

    def test_supported_extensions(self):
        assert ".pdf" in PDFExtractor.SUPPORTED_EXTENSIONS

    @patch.dict("sys.modules", {"fitz": MagicMock()})
    def test_extract_text_success(self):
        """Test text extraction with mocked PyMuPDF"""
        mock_fitz = sys.modules["fitz"]
        mock_doc = MagicMock()
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__iter__.return_value = iter(
            [
                MagicMock(get_text=MagicMock(return_value="Page 1 content")),
                MagicMock(get_text=MagicMock(return_value="Page 2 content")),
            ]
        )
        mock_fitz.open.return_value = mock_doc

        text = self.extractor.extract_text("/mock/doc.pdf")
        assert "Page 1" in text
        assert "Page 2" in text
        assert "Page 1 content" in text
        assert "Page 2 content" in text

    def test_extract_text_no_pymupdf(self):
        """When PyMuPDF is not installed, return empty string"""
        with patch.dict("sys.modules", {"fitz": None}):
            text = self.extractor.extract_text("/mock/doc.pdf")
            assert text == ""

    @patch.dict("sys.modules", {"fitz": MagicMock()})
    def test_extract_metadata_success(self):
        mock_fitz = sys.modules["fitz"]
        mock_doc = MagicMock()
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.metadata = {
            "title": "Test PDF",
            "author": "Test Author",
            "subject": "Testing",
        }
        mock_doc.page_count = 5
        mock_fitz.open.return_value = mock_doc

        meta = self.extractor.extract_metadata("/mock/doc.pdf")
        assert meta["title"] == "Test PDF"
        assert meta["author"] == "Test Author"
        assert meta["subject"] == "Testing"
        assert meta["pages"] == 5
        assert meta["format"] == "5 pages"

    @patch.dict("sys.modules", {"fitz": MagicMock()})
    def test_extract_metadata_no_title(self):
        mock_fitz = sys.modules["fitz"]
        mock_doc = MagicMock()
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.metadata = {}
        mock_doc.page_count = 1
        mock_fitz.open.return_value = mock_doc

        meta = self.extractor.extract_metadata("/mock/doc.pdf")
        assert meta["title"] == ""
        assert meta["author"] == ""

    def test_extract_metadata_no_pymupdf(self):
        with patch.dict("sys.modules", {"fitz": None}):
            meta = self.extractor.extract_metadata("/mock/doc.pdf")
            assert meta == {}

    @patch.dict("sys.modules", {"fitz": MagicMock()})
    def test_extract_images_success(self, tmp_path):
        """Test image extraction from PDF"""
        mock_fitz = sys.modules["fitz"]
        mock_doc = MagicMock()
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.page_count = 1

        mock_page = MagicMock()
        mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]

        mock_base_image = {"image": b"fake_image_bytes", "ext": "png"}
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.extract_image.return_value = mock_base_image

        mock_fitz.open.return_value = mock_doc

        output_dir = tmp_path / "pdf_images"
        saved = self.extractor.extract_images("/mock/doc.pdf", output_dir)
        assert len(saved) == 1
        saved_path = Path(saved[0])
        assert saved_path.exists()
        assert saved_path.suffix == ".png"

    def test_extract_images_no_pymupdf(self):
        with patch.dict("sys.modules", {"fitz": None}):
            result = self.extractor.extract_images("/mock/doc.pdf")
            assert result == []
