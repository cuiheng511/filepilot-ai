"""Tests for OCR extractor."""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from filepilot.extractors.ocr_extractor import SUPPORTED_EXTENSIONS, OCRExtractor


class TestOCRExtractor(TestCase):
    def test_supported_extensions(self):
        self.assertIn(".png", SUPPORTED_EXTENSIONS)
        self.assertIn(".jpg", SUPPORTED_EXTENSIONS)
        self.assertIn(".jpeg", SUPPORTED_EXTENSIONS)
        self.assertIn(".tiff", SUPPORTED_EXTENSIONS)
        self.assertIn(".bmp", SUPPORTED_EXTENSIONS)
        self.assertIn(".gif", SUPPORTED_EXTENSIONS)
        self.assertIn(".webp", SUPPORTED_EXTENSIONS)

    def test_is_available_no_tesseract(self):
        extractor = OCRExtractor(tesseract_path=None)
        # In test environment, tesseract is likely not available
        # Just verify the method doesn't crash
        result = extractor.is_available()
        self.assertIsInstance(result, bool)

    def test_extract_text_nonexistent_file(self):
        extractor = OCRExtractor()
        result = extractor.extract_text("/nonexistent/image.png")
        self.assertIsNone(result)

    def test_extract_text_unsupported_format(self):
        extractor = OCRExtractor()
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            result = extractor.extract_text(f.name)
            self.assertIsNone(result)

    def test_get_supported_languages(self):
        langs = OCRExtractor.get_supported_languages()
        self.assertIn("eng", langs)
        self.assertIn("chi_sim", langs)
        self.assertIn("jpn", langs)
        self.assertGreater(len(langs), 5)

    @patch("filepilot.extractors.ocr_extractor.subprocess.run")
    def test_extract_text_with_mock(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Hello World", stderr="")
        extractor = OCRExtractor(tesseract_path="tesseract")

        temp_path = Path(tempfile.gettempdir()) / "test_ocr.png"
        temp_path.write_bytes(b"fake image data")
        try:
            result = extractor.extract_text(str(temp_path))
            self.assertEqual("Hello World", result)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @patch("filepilot.extractors.ocr_extractor.subprocess.run")
    def test_extract_text_batch_with_mock(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Text", stderr="")
        extractor = OCRExtractor(tesseract_path="tesseract")

        files = []
        try:
            for i in range(3):
                temp_path = Path(tempfile.gettempdir()) / f"test_ocr_{i}.png"
                temp_path.write_bytes(b"fake")
                files.append(str(temp_path))

            results = extractor.extract_text_batch(files)
            self.assertEqual(3, len(results))
        finally:
            for f in files:
                p = Path(f)
                if p.exists():
                    p.unlink()
