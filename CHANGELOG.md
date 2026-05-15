# Changelog

## [0.5.0] - 2026-05-15

### Added
- **Batch regex rename** — Regex pattern/replacement in Organize panel with preview
- **OCR text extraction** — Tesseract integration in AI Summary panel for images
- **File statistics & treemap** — Stats button in File Browser opens distribution dialog
- **Scheduled tasks** — Auto scan/index/dedup in Settings dialog
- **Shortcut editor** — Customizable keyboard shortcuts in Settings dialog
- **Search history** — QComboBox-based history dropdown in Search panel
- **Recent files** — Track and reopen recently used files
- **Favorites** — Quick-access directory bookmarks panel

### Changed
- **UI consolidation** — 10 panels reduced to 7 (Stats→Browse, OCR→Summary, Tasks→Settings)
- **Version bump** — `0.4.1` → `0.5.0`

## [0.4.1] - 2026-05-15

### Fixed
- **Windows PyInstaller crash** — Removed unused `python-magic` dependency that required missing libmagic DLL
- **Thread safety** — Watcher signals now use `Qt.QueuedConnection` to prevent cross-thread widget access
- **File change debounce** — `_on_file_changed` debounced to 2s; dict cleared on directory switch
- **Settings data loss** — `get_settings()` now preserves `recent_dirs`, `theme` and other non-UI keys
- **Search cache** — Integrated into search flow; auto-invalidated on index rebuild
- **AppImage build** — Added `<launchable>`, `<content_rating>`, `<developer>` to AppStream XML
- **Inno Setup** — Process detection via WMI instead of always-true `tasklist`; fixed `VersionInfoCopyright` directive
- **Tray icon** — Correct `QStyle.SP_ComputerIcon` enum path
- **Notification** — Stop old animation before starting new one to prevent GC issues
- **FileWatcher** — Removed redundant `self._observer` field; added directory existence guard
- **Main entry** — Tray reference saved on window to prevent GC

### Changed
- **Version bump** — `0.4.0` → `0.4.1`

## [0.4.0] - 2026-05-14

### Added
- **Linux AppImage builder** — `scripts/build_appimage.sh` generates portable `.AppImage` via PyInstaller + appimagetool
- **macOS .app + .dmg builder** — `scripts/build_macos.sh` builds signed/notarized `.app` bundles with `create-dmg` or `hdiutil` fallback
- **Cross-platform CI** — GitHub Actions now builds on all 3 platforms: Windows (exe + Inno Setup), Linux (AppImage), macOS (.app + .dmg)
- **Unified build entry point** — `scripts/build.sh` auto-detects OS and dispatches to the right builder; `--docker-linux` flag enables Linux AppImage builds from any OS
- **macOS .icns icon** — Auto-generated from `app.png` during macOS builds
- **docs/BUILD.md** — Comprehensive cross-platform build guide covering Windows Inno Setup (including Chinese localization), Linux AppImage, macOS .app+.dmg, CI pipeline, and troubleshooting

### Fixed
- **README Windows Installer** — "Bilingual installer" corrected to "English-only installer" with complete Chinese Simplified language setup guide (download `.isl` + ISS config)
- **README Quality Gates** — Separated CI-pipeline tools from local-only recommendations; `mypy`/`pip check` properly annotated
- **Windows infinite recursion** — `scripts/build.sh` no longer calls itself on Git Bash/MSYS/Cygwin
- **build_macos.sh create-dmg syntax** — Misplaced `|| true` in the middle of command chain, causing all options after `--volicon` to be ignored
- **CI macOS icon missing** — `$ICON_PATH` variable was undefined in CI job, causing `--icon` flag to never be passed

### Changed
- **Version bump** — `0.3.0` → `0.4.0`
- **GitHub Actions** — `build` job split into `build-windows`, `build-linux`, `build-macos` with proper `needs: [lint, test]` gating
- **CI quality gates expanded** — `mypy` + `pip check` now run in all three build jobs (`build-windows`, `build-linux`, `build-macos`) before PyInstaller build
- **Inno Setup URL auto-tracking** — CI now fetches latest version from `jrsoftware.org/isdl.php` instead of hardcoding 6.2.2
- **macOS create-dmg warning** — Failed `brew install create-dmg` now outputs a visible warning before falling back to `hdiutil`
- **FilePilot.spec** — Now Windows-only; Linux and macOS builds use inline PyInstaller CLI flags directly
- **pyproject.toml entry points** — Added `[project.scripts]` (`filepilot`) and `[project.gui-scripts]` (`filepilot-gui`) per PEP 621
- **watchdog version alignment** — `>=4.0.0` → `>=6.0.0` in `pyproject.toml` to match `requirements.txt`
- **`mypy` unified to default usage** — `mypy filepilot` → `mypy` (no argument) in CI, README Quality Gates, and Development Setup
- **Architecture diagram** — Added `send2trash` → Recycle Bin path to Mermaid flowchart
- **build_installer.ps1** — Added PyInstaller existence check before build
- **README.md** — Removed unprofessional Icon section; replaced verbose per-platform build instructions with concise summary linking to docs/BUILD.md; polished Overview, Highlights, and Quality Gates copy

## [0.3.0] - 2026-05-14

### Added
- **CI dependency verification** — Pre-test step validates watchdog + PySide6 are importable
- **API key encryption** — Fernet-based encryption for stored API keys with keyring fallback
- **File lock detection** — Windows exclusive locking check prevents organizing in-use files
- **Main window centering** — Automatic screen-center on startup
- **System tray i18n** — Tooltips, pause/resume menu, and toast notifications now translated
- **File watcher directory validation** — Friendly error when watching a nonexistent directory
- **Settings dialog helper** — `_get_supported_lang_keys()` for dynamic language list updates

### Fixed
- **CJK font display** — QSS font fallback for QComboBox, QCheckBox, QMenu, QTableWidget, QGroupBox, context menu text truncation
- **File browser category stats** — Dead loop `_ = f"..."` now actually updates card file count + size
- **Search panel highlight truncation** — Emoji/multi-byte safe: now splits at whitespace instead of raw byte boundary
- **Test file_watcher fixture** — `_watched_dir` parameter missing in 5 test methods
- **Test settings_dialog accept()** — QDialog base class not initialized before mock
- **push_to_github.py** — BOM character removed, emoji replaced with cross-platform ASCII
- **Dead code cleanup** — 6 unused imports/variables removed across config.py, file_organizer.py, test_image_extractor.py, test_summarizer.py

### Changed
- **watchdog** — Added to `requirements.txt` (was missing, causing all watcher tests to fail)
- **GitHub Actions upgrade** — `actions/checkout` v4→v6, `actions/setup-python` v5→v6, `actions/upload-artifact` v4→v7, `codecov/codecov-action` v5→v6

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
