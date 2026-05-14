"""Tests for ImageExtractor"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from filepilot.extractors.image_extractor import ImageExtractor


class TestImageExtractor:
    def setup_method(self):
        self.extractor = ImageExtractor()

    def test_supported_extensions(self):
        assert ".jpg" in ImageExtractor.SUPPORTED_EXTENSIONS
        assert ".jpeg" in ImageExtractor.SUPPORTED_EXTENSIONS
        assert ".png" in ImageExtractor.SUPPORTED_EXTENSIONS
        assert ".gif" in ImageExtractor.SUPPORTED_EXTENSIONS
        assert ".webp" in ImageExtractor.SUPPORTED_EXTENSIONS

    @patch.dict("sys.modules", {"PIL": MagicMock()})
    def test_extract_metadata_success(self):
        """Test metadata extraction with mocked PIL Image"""
        mock_pil = sys.modules["PIL"]
        mock_img = MagicMock()
        mock_img.format = "PNG"
        mock_img.mode = "RGB"
        mock_img.width = 800
        mock_img.height = 600
        mock_img.is_animated = False
        mock_img.getexif.return_value = {}
        mock_pil.Image.open.return_value.__enter__.return_value = mock_img

        test_file = Path("/mock/image.png")
        meta = self.extractor.extract_metadata(test_file)

        assert meta["format"] == "PNG"
        assert meta["mode"] == "RGB"
        assert meta["width"] == 800
        assert meta["height"] == 600
        assert "800" in meta["size"] and "600" in meta["size"]
        assert meta["aspect_ratio"] == 1.33
        assert meta["is_animated"] is False

    @patch.dict("sys.modules", {"PIL": MagicMock()})
    def test_extract_metadata_with_exif(self):
        """Test EXIF data extraction"""
        mock_pil = sys.modules["PIL"]
        mock_img = MagicMock()
        mock_img.format = "JPEG"
        mock_img.width = 400
        mock_img.height = 300
        mock_img.is_animated = False
        # Mock EXIF data via patching ExifTags.TAGS
        mock_exif = {271: "CameraMaker", 272: "CameraModel"}
        mock_img.getexif.return_value = mock_exif

        mock_pil.ExifTags.TAGS = {271: "Make", 272: "Model"}
        mock_pil.Image.open.return_value.__enter__.return_value = mock_img

        meta = self.extractor.extract_metadata("/mock/photo.jpg")
        assert "exif" in meta
        assert meta["exif"]["Make"] == "CameraMaker"
        assert meta["exif"]["Model"] == "CameraModel"

    def test_extract_metadata_no_pillow(self):
        """When Pillow is not installed, return error dict"""
        with patch.dict("sys.modules", {"PIL": None}):
            meta = self.extractor.extract_metadata("/mock/img.png")
            assert "error" in meta

    @patch.dict("sys.modules", {"PIL": MagicMock()})
    def test_extract_text(self):
        """extract_text returns a text description"""
        mock_pil = sys.modules["PIL"]
        mock_img = MagicMock()
        mock_img.format = "PNG"
        mock_img.width = 800
        mock_img.height = 600
        mock_img.is_animated = False
        mock_img.getexif.return_value = {}
        mock_pil.Image.open.return_value.__enter__.return_value = mock_img

        text = self.extractor.extract_text("/mock/image.png")
        assert "image.png" in text
        assert "800" in text and "600" in text
        assert "PNG" in text

    @patch.dict("sys.modules", {"PIL": MagicMock()})
    def test_get_thumbnail(self):
        mock_pil = sys.modules["PIL"]
        mock_img = MagicMock()
        mock_img.thumbnail.return_value = None
        mock_pil.Image.open.return_value.__enter__.return_value = mock_img

        result = self.extractor.get_thumbnail("/mock/image.png", size=(100, 100))
        mock_img.thumbnail.assert_called_once_with((100, 100))
