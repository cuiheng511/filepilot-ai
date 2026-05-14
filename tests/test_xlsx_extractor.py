"""Tests for XlsxExtractor"""

import sys
from unittest.mock import MagicMock, patch

from filepilot.extractors.xlsx_extractor import XlsxExtractor


class TestXlsxExtractor:
    def setup_method(self):
        self.extractor = XlsxExtractor()

    def test_supported_extensions(self):
        assert ".xlsx" in XlsxExtractor.SUPPORTED_EXTENSIONS
        assert ".xls" in XlsxExtractor.SUPPORTED_EXTENSIONS

    @patch.dict("sys.modules", {"openpyxl": MagicMock()})
    def test_extract_text_success(self):
        """Test text extraction with mocked openpyxl"""
        mock_openpyxl = sys.modules["openpyxl"]
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1", "Sheet2"]

        mock_ws1 = MagicMock()
        # iter_rows(values_only=True) returns tuples of cell VALUES (not Cell objects)
        mock_ws1.iter_rows.return_value = [
            (None,),  # skipped (None value)
            ("A1", "B1"),
            ("A2", "B2"),
        ]
        mock_ws2 = MagicMock()
        mock_ws2.iter_rows.return_value = [
            ("Data1", "Data2"),
        ]

        def getitem(sheet_name):
            return {"Sheet1": mock_ws1, "Sheet2": mock_ws2}[sheet_name]

        mock_wb.__getitem__.side_effect = getitem
        mock_openpyxl.load_workbook.return_value = mock_wb

        text = self.extractor.extract_text("/mock/data.xlsx")
        assert "=== Sheet1 ===" in text
        assert "=== Sheet2 ===" in text
        assert "A1 | B1" in text
        assert "A2 | B2" in text
        assert "Data1 | Data2" in text

    @patch.dict("sys.modules", {"openpyxl": MagicMock()})
    def test_extract_text_empty_cells(self):
        """Cells with None values should be skipped"""
        mock_openpyxl = sys.modules["openpyxl"]
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = [
            (None, "B1", None),
        ]
        mock_wb.__getitem__.return_value = mock_ws
        mock_openpyxl.load_workbook.return_value = mock_wb

        text = self.extractor.extract_text("/mock/data.xlsx")
        assert "B1" in text
        # None values are filtered out before string conversion
        assert "None" not in text

    def test_extract_text_no_openpyxl_fallback_csv(self, tmp_path):
        """When openpyxl is not available, try csv fallback"""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n", encoding="utf-8")

        with patch.dict("sys.modules", {"openpyxl": None}):
            text = self.extractor.extract_text(test_file)
            assert "col1 | col2" in text
            assert "val1 | val2" in text

    def test_extract_metadata_no_openpyxl(self):
        with patch.dict("sys.modules", {"openpyxl": None}):
            meta = self.extractor.extract_metadata("/mock/data.xlsx")
            assert meta == {}

    @patch.dict("sys.modules", {"openpyxl": MagicMock()})
    def test_extract_metadata_success(self):
        mock_openpyxl = sys.modules["openpyxl"]
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1", "Sheet2", "Sheet3"]
        mock_wb.properties.title = "Test Spreadsheet"
        mock_wb.properties.creator = "Author"
        mock_openpyxl.load_workbook.return_value = mock_wb

        meta = self.extractor.extract_metadata("/mock/data.xlsx")
        assert meta["sheet_count"] == 3
        assert meta["sheets"] == ["Sheet1", "Sheet2", "Sheet3"]
        assert meta["title"] == "Test Spreadsheet"
        assert meta["author"] == "Author"

    @patch.dict("sys.modules", {"openpyxl": MagicMock()})
    def test_extract_metadata_no_properties(self):
        mock_openpyxl = sys.modules["openpyxl"]
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]
        mock_wb.properties = None
        mock_openpyxl.load_workbook.return_value = mock_wb

        meta = self.extractor.extract_metadata("/mock/data.xlsx")
        assert meta["sheet_count"] == 1
        assert meta["sheets"] == ["Sheet1"]
        # When properties is None, title/author are not added to meta
        assert "title" not in meta
        assert "author" not in meta
