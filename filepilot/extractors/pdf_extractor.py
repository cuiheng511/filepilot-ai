"""PDF 内容提取器"""

from pathlib import Path


class PDFExtractor:
    """PDF 文件内容提取"""

    SUPPORTED_EXTENSIONS = {".pdf"}

    def extract_text(self, file_path: str | Path) -> str:
        """提取 PDF 中的文本内容"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return ""

        text_parts: list[str] = []
        try:
            with fitz.open(str(file_path)) as doc:
                for page_num, page in enumerate(doc, 1):
                    page_text = page.get_text().strip()
                    if page_text:
                        text_parts.append(f"--- 第 {page_num} 页 ---\n{page_text}")
        except Exception:
            pass

        return "\n\n".join(text_parts)

    def extract_metadata(self, file_path: str | Path) -> dict:
        """提取 PDF 元数据"""
        try:
            import fitz
        except ImportError:
            return {}

        try:
            with fitz.open(str(file_path)) as doc:
                metadata = doc.metadata or {}
                return {
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "subject": metadata.get("subject", ""),
                    "pages": doc.page_count,
                    "format": f"{doc.page_count} 页",
                }
        except Exception:
            return {}

    def extract_images(self, file_path: str | Path, output_dir: str | Path | None = None) -> list[str]:
        """提取 PDF 中的图片"""
        try:
            import fitz
        except ImportError:
            return []

        saved_images: list[str] = []
        try:
            with fitz.open(str(file_path)) as doc:
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    images = page.get_images()
                    for img_idx, img in enumerate(images):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        if output_dir:
                            output_path = Path(output_dir)
                            output_path.mkdir(parents=True, exist_ok=True)
                            img_name = f"page{page_num + 1}_img{img_idx + 1}.{image_ext}"
                            img_path = output_path / img_name
                            with open(img_path, "wb") as f:
                                f.write(image_bytes)
                            saved_images.append(str(img_path))
        except Exception:
            pass

        return saved_images
