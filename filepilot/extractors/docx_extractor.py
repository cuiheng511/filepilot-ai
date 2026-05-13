"""DOCX Content Extractor"""

from pathlib import Path


class DocxExtractor:
    """Word document content extraction"""

    SUPPORTED_EXTENSIONS = {".docx"}

    def extract_text(self, file_path: str | Path) -> str:
        """Extract text content from a DOCX file"""
        try:
            from docx import Document
        except ImportError:
            return ""
        try:
            doc = Document(str(file_path))
            parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
            return "\n".join(parts)
        except Exception:
            return ""

    def extract_metadata(self, file_path: str | Path) -> dict:
        """Extract DOCX metadata"""
        try:
            from docx import Document
        except ImportError:
            return {}
        try:
            doc = Document(str(file_path))
            props = doc.core_properties
            return {
                "title": props.title or "",
                "author": props.author or "",
                "subject": props.subject or "",
                "paragraphs": len(doc.paragraphs),
                "tables": len(doc.tables),
            }
        except Exception:
            return {}
