# Changelog

## [Unreleased]

### Added
- **Semantic Search** — Embedding-based re-ranking of Whoosh full-text results (`filepilot/core/embeddings.py`). Uses the configured AI provider's `embed()` to cache file embeddings during indexing (stored in `~/.filepilot/embeddings.json`). Search queries are embedded and results re-ranked by cosine similarity (pure Python, no numpy). Toggle via "🔬 Semantic" checkbox in the search panel. 18 new tests.
- **ServiceContainer/AppState/EventBus** — Centralized service wiring, typed state accessors with QObject signals, and decoupled cross-panel event bus
- **DirectoryTreeWidget** — Standalone directory tree extracted from file_browser.py (`filepilot/ui/directory_tree.py`)
- **Worker helper** — `QRunnable`-based Worker for QThreadPool operations (`filepilot/core/worker.py`)
- **Error handling utility** — `try_safe` decorator for graceful degradation (`filepilot/core/errors.py`)
- **Multi-tab file browser** — `TabbedFileBrowser(QWidget)` wraps `QTabWidget` with closable/movable tabs, `Ctrl+T`/`Ctrl+W` shortcuts, auto-replace on last-close (`filepilot/ui/tabbed_browser.py`)
- **Inline filter bar** — Type (8 categories), Size (5 ranges), Date (5 ranges), Tag (dynamic from TagManager) filter combos in File Browser toolbar with "(N shown)" counter
- **Search result highlighting** — `SearchHighlightDelegate(QStyledItemDelegate)` renders Whoosh `<b class="match">` as styled rich text via `QTextDocument`
- **Batch rename undo** — `_regex_undo` list stores `(source, destination)` before execution; ↩ Undo button reverts in reverse order with confirmation dialog
- **SQLite metadata database** — `MetadataDB` in `core/index_db.py` stores file metadata (path, name, size, timestamps, extension, category) with WAL journaling for 10x faster type/size/date filtering; Whoosh retained for full-text search only
- **Plugin SDK documentation** — `docs/PLUGIN_SDK.md` with BaseFileExtractor API reference, discovery directory layout (`~/.filepilot/plugins/`), integration points, best practices, and troubleshooting table
- **Example extractor plugin** — `filepilot/extractors/example_plugin.py` with two reference implementations: `CSVAnalyzerExtractor` (structured CSV extraction) and `LogFileExtractor` (log level counts, error collection, last 20 lines)

### Changed
- **Panel architecture** — All 10 panels accept optional `app_state`/`event_bus` params; column config, search history, saved searches, and favorites migrated to AppState
- **File browser performance** — Incremental batch scan loading (every 100 files); text preview loaded asynchronously via background thread
- **Search/Index threading** — Migrated from bare `Thread` to QThreadPool (`Worker` + `WorkerSignals`)
- **PreviewPanel extracted** — Standalone preview widget in `filepilot/ui/preview_panel.py` with async text/code/markdown rendering and stale-result guard
- **`_setup_ui` split** — Organize (186→9 methods), File Browser (132→6), Index (132→7), Summary (127→6), Duplicates (127→7), Search (120→6) panels refactored into named sub-methods
- **Error reporting** — Silent `except Exception: pass` blocks in search plugin extraction and main_window file opening now surface error messages
- **Build configs** — All 4 build files updated with hidden imports: added `service_container`, `app_state`, `event_bus`, `worker`, `errors`, `notification`, `preview_panel`, `directory_tree`, `tag_rules`, and `index_db`
- **Indexer dual-store** — `index_files()` writes both SQLite and Whoosh; `search_metadata()`/`search_by_category()`/`search_by_extension()`/`search_by_date_range()` delegate to SQLite; `get_stats()` includes `total_size`/`total_size_str`
- **CI Linux build** — Removed blank line that broke PyInstaller continuation; added 7 missing extractor hidden imports (`markdown_extractor`, `code_extractor`, `image_extractor`, `ocr_extractor`, `docx_extractor`, `xlsx_extractor`, `pptx_extractor`) and `markdown`
- **CI macOS build** — Added missing `markdown` hidden import
- **Build scripts** — `build_appimage.sh` and `build_macos.sh`: fallback version `0.4.0` → `0.6.0`
- **MainWindow closeEvent** — Iterates `TabbedFileBrowser` tabs to cancel background scans on close

### Fixed
- **`Q_ARG(list, files)` RuntimeError** — Replaced with `batch_files_ready` signal + `scan_completed` signal in file_browser.py; removed `QMetaObject.invokeMethod` (incompatible with PySide6)
- **Scan worker thread crash on close** — Added `closeEvent` to MainWindow and `try/except RuntimeError` guards in scan_worker
- **Index panel undefined closure** — `action`/`_dir` → `rebuild`/`_dir` in `_start_indexing`
- **`_add_nav_separator` items** — Now use `Qt.NoItemFlags` (were missing flags set)
- **Duplicates panel async crash** — Replaced `Thread` + `Q_ARG(list, groups)` with `Worker` + `scan_results_ready` signal
- **Organize panel async crash** — Replaced 5 `Thread` + `Q_ARG(list, …)` calls with `Worker` + typed signals (`preview_ready`, `execute_ready`, `regex_preview_ready`, `regex_execute_ready`, `cancel_done`); all background ops use `QThreadPool.globalInstance()`
- **Plugin template encoding** — `plugin_system.py:182` sample `extract_metadata` now uses `encoding="utf-8", errors="replace"` to prevent `UnicodeDecodeError` on non-UTF-8 files
- **Ruff E501 violations** — Fixed 36 lines exceeding `line-length=100` across 8 files (SQL column lists, i18n translations, CSS strings, AI prompt strings, UI descriptions)
- **Embedding provider caching** — `get_embedding_provider()` now caches the AI provider instance to avoid re-creating on every file during indexing
- **Embedding persistence** — `EmbeddingCache.save()` called after `index_files()` completes; previously embeddings were kept only in memory
- **Search cache semantics** — Semantic search results no longer cached (embedding scores change over time as index grows); cache used only for plain-text Whoosh searches
- **Anthropic fallback** — `get_embedding_provider()` correctly returns `None` for Anthropic (no `embed()` method); `search_semantic()` falls back to Whoosh score ordering
- **i18n for semantic search** — Added `search_semantic` / `search_semantic_tip` keys across all 18 languages

### Added (tests)
- `test_dashboard_panel.py` — 17 tests covering stats, recent folders/files, signals, EventBus
- `test_main_window_navigation.py` — 8 new tests: separator skipping, invalid index, keyboard mapping, global search
- `test_integration.py` — 5 end-to-end tests: startup, navigation, open directory, toolbar state, global search
- `test_embeddings.py` — 18 tests: cosine similarity (6), EmbeddingCache CRUD+persistence+search (10), embed_text fallback (2)

## [0.6.0] - 2026-05-18

### Added
- **Dashboard panel** — New landing page with quick stats, recent folders/files, quick actions, and keyboard shortcuts reference
- **Global search shortcut** — `Ctrl+Shift+F` switches to Search panel and focuses input
- **Theme toggle shortcut** — `Ctrl+L` toggles dark/light theme

### Changed
- **Navigation sidebar** — Reorganized into categories: 📂 Browse, 🔍 Search, 🛠 Tools, ⚙️ Settings with visual separators
- **File Browser toolbar** — Batch operations (Copy/Move/Delete) grouped into "⚡ Actions" dropdown; removed standalone Stats button
- **Main toolbar** — Fixed duplicate "Scan" labels; buttons now clearly labeled "📂 Open Folder", "🔄 Scan", "📇 Index", "🌙 Theme"
- **Panel navigation** — Ctrl+1..9 updated to reflect new dashboard-first panel order
- **Version bump** — `0.5.0` → `0.6.0`

### Fixed
- **CI hidden imports** — Added `filepilot.ui.dashboard_panel` to `FilePilot.spec`, Linux/macOS PyInstaller flags, and `build_appimage.sh` spec template

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
