"""图片元数据和内容提取器"""

from pathlib import Path


class ImageExtractor:
    """图片文件信息提取"""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".ico"}

    def extract_metadata(self, file_path: str | Path) -> dict:
        """提取图片元数据"""
        try:
            from PIL import Image, ExifTags
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

                # 提取 EXIF 信息
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
        """提取图片描述文本（基于文件名和元数据）"""
        path = Path(file_path)
        meta = self.extract_metadata(file_path)

        parts = [
            f"文件: {path.name}",
            f"尺寸: {meta.get('size', '未知')}",
            f"格式: {meta.get('format', '未知')}",
        ]

        if "exif" in meta:
            exif = meta["exif"]
            if "DateTimeOriginal" in exif:
                parts.append(f"拍摄时间: {exif['DateTimeOriginal']}")
            if "Make" in exif and "Model" in exif:
                parts.append(f"设备: {exif['Make']} {exif['Model']}")

        return "\n".join(parts)

    def get_thumbnail(self, file_path: str | Path, size: tuple[int, int] = (200, 200)) -> bytes | None:
        """生成缩略图"""
        try:
            from PIL import Image
            import io

            with Image.open(str(file_path)) as img:
                img.thumbnail(size)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
        except Exception:
            return None
