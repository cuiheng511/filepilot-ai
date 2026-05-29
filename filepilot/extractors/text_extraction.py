"""Shared text extraction dispatch used by the summarizer, MCP tools, and search.

Provides a single source of truth for mapping file extensions to extractors,
including plugin extractor fallback and a plain-text final fallback.
"""

from __future__ import annotations

from pathlib import Path

# Extension groups (single source of truth for extractor dispatch)
PDF_EXTS = {".pdf"}
MARKDOWN_EXTS = {".md", ".markdown", ".mdx"}
DOCX_EXTS = {".docx"}
XLSX_EXTS = {".xlsx", ".xls"}
PPTX_EXTS = {".pptx", ".ppt"}
CODE_EXTS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp", ".rs", ".go"}


def extract_text(file_path: str | Path, *, use_plugins: bool = True) -> str:
    """Extract text from a supported file, with plugin and plain-text fallback.

    Args:
        file_path: Path to the file.
        use_plugins: Whether to try plugin extractors before the plain-text fallback.

    Returns:
        Extracted text, or empty string on failure.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in PDF_EXTS:
        from filepilot.extractors.pdf_extractor import PDFExtractor

        return PDFExtractor().extract_text(path)
    if ext in MARKDOWN_EXTS:
        from filepilot.extractors.markdown_extractor import MarkdownExtractor

        return MarkdownExtractor().extract_text(path)
    if ext in DOCX_EXTS:
        from filepilot.extractors.docx_extractor import DocxExtractor

        return DocxExtractor().extract_text(path)
    if ext in XLSX_EXTS:
        from filepilot.extractors.xlsx_extractor import XlsxExtractor

        return XlsxExtractor().extract_text(path)
    if ext in PPTX_EXTS:
        from filepilot.extractors.pptx_extractor import PptxExtractor

        return PptxExtractor().extract_text(path)
    if ext in CODE_EXTS:
        from filepilot.extractors.code_extractor import CodeExtractor

        return CodeExtractor().extract_text(path)

    # Try plugin extractors before falling back to plain text
    if use_plugins:
        try:
            from filepilot.core.plugin_system import get_plugin_manager

            plugin_ext = get_plugin_manager().get_extractor_for(ext)
            if plugin_ext:
                text = plugin_ext.extract_text(path)
                if text:
                    return text
        except Exception:
            pass

    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def extract_code_with_context(file_path: str | Path, max_code_chars: int = 6000) -> str:
    """Extract code with a metadata header (language + definitions) for summarization."""
    from filepilot.extractors.code_extractor import CodeExtractor

    path = Path(file_path)
    extractor = CodeExtractor()
    meta = extractor.extract_metadata(path)
    code = extractor.extract_text(path)
    context_parts = [f"Language: {meta.get('language', 'unknown')}"]
    defs = meta.get("definitions", [])
    if defs:
        def_names = [d["name"] for d in defs[:20]]
        context_parts.append(f"Functions/Classes: {', '.join(def_names)}")
    return f"{' | '.join(context_parts)}\n\n{code[:max_code_chars]}"
