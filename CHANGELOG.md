# Changelog

## [0.1.0] - 2025-06-13

### Added
- Initial release of FilePilot AI
- File browser with directory scanning and file preview
- AI-powered file search with Whoosh full-text indexing
- File organizer with auto-categorization by type, date, extension, and size
- Duplicate file finder with MD5 hash comparison
- AI summary generation for PDF, Markdown, and code files
- Settings dialog with multiple AI provider support (Ollama, OpenAI, Anthropic, etc.)
- Dark/light theme toggle
- Keyboard shortcuts for panel navigation (Ctrl+1~6)

### Technical
- PySide6-based desktop GUI
- Whoosh full-text search engine
- Support for local (Ollama/LM Studio) and cloud (OpenAI/Anthropic) AI providers
- Modular extractor architecture for PDF, DOCX, PPTX, XLSX, images, and code files
