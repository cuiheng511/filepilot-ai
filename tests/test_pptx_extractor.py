"""Tests for PptxExtractor"""

import sys
from unittest.mock import MagicMock, patch


from filepilot.extractors.pptx_extractor import PptxExtractor


class TestPptxExtractor:
    def setup_method(self):
        self.extractor = PptxExtractor()

    def test_supported_extensions(self):
        assert ".pptx" in PptxExtractor.SUPPORTED_EXTENSIONS
        assert ".ppt" in PptxExtractor.SUPPORTED_EXTENSIONS

    def test_extract_text_no_pptx(self):
        """When python-pptx is not installed, return empty string"""
        with patch.dict("sys.modules", {"pptx": None}):
            text = self.extractor.extract_text("/mock/pres.pptx")
            assert text == ""

    @patch.dict("sys.modules", {"pptx": MagicMock()})
    def test_extract_text_success(self):
        """Test text extraction with mocked python-pptx"""
        mock_pptx = sys.modules["pptx"]
        mock_prs = MagicMock()

        # Create mock slides with shapes
        mock_slide1 = MagicMock()
        mock_shape1 = MagicMock()
        mock_shape1.has_text_frame = True
        mock_shape1.text_frame.paragraphs = [
            MagicMock(text="Slide 1 Title"),
            MagicMock(text="Slide 1 content"),
        ]
        mock_shape1.has_table = False
        mock_slide1.shapes = [mock_shape1]

        mock_slide2 = MagicMock()
        mock_shape2 = MagicMock()
        mock_shape2.has_text_frame = True
        mock_shape2.text_frame.paragraphs = [
            MagicMock(text="Slide 2 Title"),
        ]
        mock_shape2.has_table = False
        mock_slide2.shapes = [mock_shape2]

        mock_prs.slides = [mock_slide1, mock_slide2]
        mock_pptx.Presentation.return_value = mock_prs

        text = self.extractor.extract_text("/mock/pres.pptx")
        assert "Slide 1 Title" in text
        assert "Slide 1 content" in text
        assert "Slide 2 Title" in text
        assert "--- Slide 1 ---" in text
        assert "--- Slide 2 ---" in text

    @patch.dict("sys.modules", {"pptx": MagicMock()})
    def test_extract_text_with_table(self):
        """Test extraction includes table content"""
        mock_pptx = sys.modules["pptx"]
        mock_prs = MagicMock()
        mock_slide = MagicMock()

        mock_table_shape = MagicMock()
        mock_table_shape.has_text_frame = False
        mock_table_shape.has_table = True
        mock_cell_row = MagicMock()
        cell1 = MagicMock()
        cell1.text.strip.return_value = "Header1"
        cell2 = MagicMock()
        cell2.text.strip.return_value = "Header2"
        mock_cell_row.cells = [cell1, cell2]
        mock_table_shape.table.rows = [mock_cell_row]

        mock_slide.shapes = [mock_table_shape]
        mock_prs.slides = [mock_slide]
        mock_pptx.Presentation.return_value = mock_prs

        text = self.extractor.extract_text("/mock/pres.pptx")
        assert "Header1 | Header2" in text

    def test_extract_metadata_no_pptx(self):
        with patch.dict("sys.modules", {"pptx": None}):
            meta = self.extractor.extract_metadata("/mock/pres.pptx")
            assert meta == {}

    @patch.dict("sys.modules", {"pptx": MagicMock()})
    def test_extract_metadata_success(self):
        mock_pptx = sys.modules["pptx"]
        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock(), MagicMock(), MagicMock()]
        mock_prs.core_properties.title = "Test Presentation"
        mock_prs.core_properties.author = "Author"
        mock_pptx.Presentation.return_value = mock_prs

        meta = self.extractor.extract_metadata("/mock/pres.pptx")
        assert meta["slide_count"] == 3
        assert meta["title"] == "Test Presentation"
        assert meta["author"] == "Author"
