# Changelog

## [0.2.0] - 2026-05-14

### Added
- **CLI interface** — `python -m filepilot.cli` with scan, search, duplicates, organize, export, disk-usage commands
- **Drag-and-drop** — Drop folders onto file browser to navigate
- **File preview** — Click a file to preview content (PDF, code, images) in bottom panel
- **Export** — Export scan results as CSV or JSON
- **Undo mechanism** — One-click rollback for file organization operations
- **Theme toggle** — Dark/light theme switch with QSS hot-reload
- **Disk usage visualization** — Category size breakdown bar chart in scan results
- **5 AI providers** — Ollama, llama.cpp, OpenAI, Anthropic, Custom (OpenAI-compatible)
- **Office extractors** — DOCX, XLSX, PPTX content extraction
- **i18n support** — `t()` translation framework with zh/en language switching
- **Logging system** — Structured logging to `~/.filepilot/logs/filepilot.log`
- **GitHub Actions CI** — Lint + test on Ubuntu/macOS/Windows × Python 3.10-3.12
- **Dependabot** — Automatic dependency updates
- **Issue templates** — Bug report + feature request
- **CONTRIBUTING.md** — Contribution guide
- **PyInstaller packaging** — `FilePilot.spec` + build script

### Fixed
- `_partial_hash` collision — length prefix prevents head/tail overlap producing same hash
- `FileCategory` overlap — `.txt` and `.pdf` removed from duplicate categories
- Settings duplication — `app.load_settings()` and `MainWindow._load_settings()` unified
- Ollama/OpenAI URL settings not used — `create_services()` now passes `api_base`
- Cancel race conditions — `_cancelling` guard prevents double UI state reset in 4 panels
- `CategoryRule.category_map` — was `Field` object (not a dict) due to missing `@dataclass`
- `file_browser.py` indentation error in `_on_file_double_click`
- `summary_panel._init_ai` missing `api_base` for AI providers

### Changed
- Refactored AI layer with `AIProvider` abstract base class
- Extractors updated to handle new file types (DOCX, XLSX, PPTX)
- README rewritten with badges, feature matrix, provider table
- All UI strings internationalized via `t()` function

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
