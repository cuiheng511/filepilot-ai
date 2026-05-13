"""Image Content Extractor"""

import io
from pathlib import Path


class ImageExtractor:
    """Image file metadata extraction"""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".ico"}

    def extract_metadata(self, file_path: str | Path) -> dict:
        """Extract image metadata"""
        try:
            from PIL import ExifTags, Image
        except ImportError:
            return {"error": "Pillow not installed"}
        try:
            with Image.open(str(file_path)) as img:
                metadata = {
                    "format": img.format,
                    "mode": img.mode,
                    "width": img.width,
                    "height": img.height,
                    "size": f"{img.width} × {img.height}",
                    "aspect_ratio": round(img.width / img.height, 2) if img.height else 0,
                    "is_animated": getattr(img, "is_animated", False),
                }
                # Extract EXIF data
                exif_data = img.getexif()
                if exif_data:
                    exif_info = {}
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8", errors="replace")
                            except Exception:
                                continue
                        exif_info[tag_name] = str(value)
                    metadata["exif"] = exif_info
                return metadata
        except Exception as e:
            return {"error": str(e)}

    def extract_text(self, file_path: str | Path) -> str:
        """Extract text description from image metadata"""
        path = Path(file_path)
        meta = self.extract_metadata(file_path)
        parts = [
            f"File: {path.name}",
            f"Size: {meta.get('size', 'Unknown')}",
            f"Format: {meta.get('format', 'Unknown')}",
        ]
        if "exif" in meta:
            exif = meta["exif"]
            if "DateTimeOriginal" in exif:
                parts.append(f"Date taken: {exif['DateTimeOriginal']}")
            if "Make" in exif and "Model" in exif:
                parts.append(f"Device: {exif['Make']} {exif['Model']}")
        return "\n".join(parts)

    def get_thumbnail(self, file_path: str | Path, size: tuple[int, int] = (200, 200)) -> bytes | None:
        """Generate a thumbnail for the image"""
        try:
            from PIL import Image
            with Image.open(str(file_path)) as img:
                img.thumbnail(size)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
        except Exception:
            return None
