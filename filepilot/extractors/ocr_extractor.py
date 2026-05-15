"""OCR Extractor — extract text from images/scans using Tesseract."""

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("filepilot.ocr_extractor")

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"}


class OCRExtractor:
    """Extract text from images using Tesseract OCR."""

    def __init__(self, tesseract_path: str | None = None):
        self.tesseract_path = tesseract_path or self._find_tesseract()

    @staticmethod
    def _find_tesseract() -> str | None:
        """Try to find tesseract executable in PATH."""
        cmd = "tesseract" if sys.platform != "win32" else "tesseract.exe"
        try:
            subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                timeout=5,
            )
            return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def is_available(self) -> bool:
        """Check if Tesseract is available."""
        if not self.tesseract_path:
            return False
        try:
            result = subprocess.run(
                [self.tesseract_path, "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def extract_text(
        self,
        image_path: str | Path,
        lang: str = "eng",
        timeout: int = 60,
    ) -> str | None:
        """Extract text from an image file.

        Args:
            image_path: Path to the image file.
            lang: Language code (e.g., 'eng', 'chi_sim', 'jpn').
            timeout: Maximum seconds to wait for OCR.

        Returns:
            Extracted text or None on failure.
        """
        if not self.is_available():
            logger.warning("Tesseract is not available")
            return None

        path = Path(image_path)
        if not path.exists():
            logger.warning("Image file not found: %s", path)
            return None

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.warning("Unsupported image format: %s", path.suffix)
            return None

        tesseract_path = self.tesseract_path
        if tesseract_path is None:
            logger.warning("Tesseract path is not set")
            return None

        try:
            result = subprocess.run(
                [
                    tesseract_path,
                    str(path),
                    "stdout",
                    "-l",
                    lang,
                    "--psm",
                    "3",  # Fully automatic page segmentation
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                text = result.stdout.strip()
                return text if text else None
            else:
                logger.warning(
                    "Tesseract failed for %s: %s",
                    path.name,
                    result.stderr[:200],
                )
                return None

        except subprocess.TimeoutExpired:
            logger.warning("OCR timeout for %s", path.name)
            return None
        except Exception as e:
            logger.error("OCR error for %s: %s", path.name, e)
            return None

    def extract_text_batch(
        self,
        image_paths: list[str | Path],
        lang: str = "eng",
        timeout: int = 60,
        progress_callback=None,
    ) -> dict[str, str | None]:
        """Extract text from multiple images.

        Args:
            image_paths: List of image file paths.
            lang: Language code.
            timeout: Timeout per image.
            progress_callback: Optional callback(current, total).

        Returns:
            Dict mapping path -> extracted text (or None).
        """
        results = {}
        total = len(image_paths)

        for i, path in enumerate(image_paths):
            results[str(path)] = self.extract_text(path, lang, timeout)
            if progress_callback:
                progress_callback(i + 1, total)

        return results

    @staticmethod
    def get_supported_languages() -> list[str]:
        """Return common supported language codes."""
        return [
            "eng",
            "chi_sim",
            "chi_tra",
            "jpn",
            "kor",
            "fra",
            "deu",
            "spa",
            "rus",
            "ara",
            "hin",
            "tha",
            "vie",
        ]
