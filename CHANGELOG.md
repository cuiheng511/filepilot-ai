# Changelog

## [Unreleased]

## [0.6.7] - 2026-06-02

### Added
- **Pre-commit hooks** — `.pre-commit-config.yaml` with pinned ruff (`astral-sh/ruff-pre-commit` v0.8.6) plus local mypy for fast lint and type-check feedback before commit.
- **Main entrypoint tests** — `test_main_entrypoint.py` covers `main.py` startup branches (start_minimized, missing primary screen) and `python -m filepilot` delegation. `main.py` and `__main__.py` coverage 0% → 100%.
- **Chat assistant branch tests** — 20 new tests for `try_local_query`, `local_query_fallback`, and `ai_query` edge cases (no indexer, category counts, file extension lookup, AI provider exception, etc.). `chat_assistant.py` coverage 44% → 99%.
- **Preview panel widget tests** — 14 new tests for image, archive, text/markdown worker paths, and PDF fallback. `preview_panel.py` coverage 34% → 77%.

### Changed
- **CI coverage split** — Per-test-file coverage runs now use `--cov-report=` (empty) so `fail_under` is only checked once on the final combined `coverage report`, never per-subprocess. Annotated in `ci.yml`.
- **Coverage baseline** — `pyproject.toml` `fail_under` raised to `67.5` to lock in current coverage and prevent regression.

### Fixed
- **Preview panel truncation** — Text preview's "more lines" message was unreachable because the read loop was capped at `max_lines`. The loop now reads `max_lines + 1` lines and uses the extra line as a sentinel; the truncation message correctly appears for files with more than 200 lines. The visible 200-line cap is unchanged.
- **CI per-test-file loop** — GitHub Actions runs `run:` blocks with `bash -e`, and pytest-cov 7.x enforces `fail_under` per subprocess. The for loop over test files was aborting on the first subprocess that failed coverage, so the final combined report ran against ~1% of files and also failed. Disabled errexit (`set +e`) and passed `--cov-fail-under=0` to each subprocess so coverage is collected across all files before the threshold is evaluated once at the end.

## [0.6.6] - 2026-05-29

### Added
- **MCP read-only flag** - Added `--read-only` to force read-only mode even when write mode is enabled through the environment.
- **MCP plan cleanup** - Added `cleanup_plans` for dry-run-first cleanup of expired saved organization plan metadata.
- **MCP workflow docs** - Added a Mermaid workflow diagram and richer agent prompt examples for scan, summarize, deduplicate, organize, and plan cleanup flows.

### Changed
- **MCP plan listing** - Extended `list_plans` with root, status, and max-age filters so agents can focus on one workspace or stale plan set.
- **MCP client snippets** - Updated client examples to prefer explicit `--read-only` for shared agent configurations.

## [0.6.5] - 2026-05-29

### Added
- **FilePilot MCP server** - Added `filepilot-mcp` with directory-scoped access for MCP clients such as Claude Code, Codex, and Cursor.
- **MCP safety layer** - Added allowed-directory validation, read limits, hidden-path blocking, and explicit write-mode checks.
- **MCP file tools** - Added scan, filename search, indexing, indexed search, bounded file reads, text extraction, summaries, tag suggestions, duplicate detection, and dry-run organization plans.
- **MCP documentation** - Added `docs/MCP.md` and refreshed the README around Desktop, CLI, and MCP usage.
- **MCP index-scope tests** - Added coverage to ensure stale indexed results outside the current allowlist or requested root are not returned.
- **MCP audit log** - Added JSONL audit records for write-like MCP operations, including denied writes.
- **MCP CI smoke** - Added a GitHub Actions job that installs the optional MCP extra and verifies the server entry point.
- **MCP organization apply** - Added saved organization plans and an explicit `apply_organization_plan` flow guarded by write mode, confirmation, path re-validation, and overwrite refusal.
- **MCP organization undo** - Added `undo_organization_plan` for reversing successful moves from an applied plan, guarded by write mode and confirmation.
- **MCP plan discovery** - Added `list_plans` so agents can rediscover saved organization plan IDs and inspect proposed/applied/undone status.
- **MCP client docs** - Added ready-to-adapt client snippets for Claude Desktop, Claude Code, Cursor, and Codex.
- **Optional desktop extra** - Split Qt/watchdog desktop dependencies into a `desktop` extra while keeping requirements-based desktop installs documented.

### Changed
- **Shared text extraction** - Centralized file text extraction dispatch in `filepilot.extractors.text_extraction` for MCP tools and summaries.
- **MCP index reuse** - Reused a cached MCP `FileIndexer` instance to avoid reopening the local search index on every index/search call.
- **MCP file reads** - Updated bounded text reads to stream only the requested slice instead of loading the whole file first.
- **MCP duplicate stats** - Reused one `DuplicateFinder` instance for duplicate grouping and stats.

### Fixed
- **MCP organization apply** - Already applied organization plans are now rejected to prevent repeated agent calls from moving the same plan twice.
- **MCP large-file writes** - Tagging and organization apply/undo now validate file existence without applying read-size limits to operations that do not load file content.
- **MCP organization undo** - Already undone organization plans are now rejected with a clear error instead of producing misleading per-file failures.

## [0.6.4] - 2026-05-28

### Added
- **Shared file operation service** — Copy, move, and trash workflows now use one conflict-safe service with preview support and event emission.
- **Embedding cache maintenance** — SQLite-backed embedding cache now supports stats, missing-file pruning, provider pruning, and compaction from Settings.
- **Release asset verification** — Added `scripts/verify_release_assets.py` and CI checks to verify `.sha256` release sidecars before upload.

### Changed
- **Plugin registry trust model** — Remote registry plugins now require SHA-256 pins before installation.
- **README and release docs** — Updated current-version docs, release integrity guidance, and security model notes for v0.6.4.

### Fixed
- **Batch file operations** — Copy/move actions avoid overwriting existing destinations and show planned renames before execution.
- **Search result undo** — Move undo now avoids overwriting if the original path has been reused.
- **Embedding cache cleanup** — Removing or clearing indexed files now persists embedding-cache cleanup.
- **Rename templates** — Patterns that include `{ext}` no longer produce duplicated extensions such as `report.txt.txt`.
- **Update downloads** — Downloaded installers are removed when SHA-256 verification fails.
- **Index panel build/update methods** — Implemented `_build_index` and `_update_index` that were previously stubs; added content extraction pipeline with both registered extractors and plain-text fallback.
- **Index panel `_cancelled`** — Attribute now initialized in `__init__` to prevent `AttributeError` if cancel is called before first build.

## [0.6.3] - 2026-05-26

### Added
- **AI Chat Panel** — Conversational file assistant (`filepilot/ui/chat_panel.py`). Supports natural language queries ("find large PDFs", "how many code files?") with local intent parsing (no AI required for simple queries) and AI-enhanced mode for complex questions. Bubble-style chat UI with async processing.
- **PDF Content Preview** — PreviewPanel now extracts and renders text from the first 5 pages of PDF files using PyMuPDF, with page numbers and styled HTML output.
- **Incremental Indexing** — `FileIndexer.index_files(incremental=True)` compares file mtimes against MetadataDB to skip unchanged files. "Incremental Update" button in IndexPanel now uses true incremental logic (10-100x faster for repeat indexing).
- **File Diff Highlighting** — File comparison dialog now shows unified diff with color-coded lines (green=added, red=removed, blue=headers) plus a side-by-side view tab using `difflib.SequenceMatcher`.
- **Regex Rename Live Preview** — OrganizePanel shows real-time preview of regex rename results as user types pattern/replacement (first 5 matching files displayed instantly).
- **Notification History** — `NotificationHistory` widget records all toast notifications with timestamps and level colors. Integrated into MainWindow's `_notify` method.
- **Tag Cloud Visualization** — TagsPanel now has a "Tag Cloud" tab with font-size proportional to usage count, 15-color palette, click-to-filter interaction.
- **File Version Snapshot** — `FileSnapshot` (`filepilot/core/file_snapshot.py`) records file move/rename/delete/organize operations in SQLite for history tracking. Integrated into FileOrganizer.
- **Drag-and-Drop to Summary Panel** — SummaryPanel accepts file/folder drops directly into the file list for quick summarization.
- **Cloud Sync Detection** — `filepilot/core/cloud_sync.py` detects OneDrive/Dropbox/Google Drive/iCloud Drive folders. FileBrowser has optional "Cloud" column showing sync provider. Windows OneDrive file status detection via file attributes.
- **Plugin Registry/Marketplace** — `filepilot/core/plugin_registry.py` fetches community plugins from GitHub with local cache. PluginManagerPanel has "Browse Registry" button and "Available" tab with one-click install/uninstall.
- **Search Result Double-Click** — Double-clicking a search result opens the file with the system default application.

### Changed
- **TagManager deferred save** — Writes are now batched with a 300ms debounce timer instead of saving on every single tag operation. Bulk tagging is 10-50x faster. Added `flush()` method for explicit save.
- **Search extractors lazy-loaded** — `_EXTRACTORS` dict replaced with `_get_extractor()` function that creates instances on first use, reducing import-time overhead.
- **Cloud label caching** — `_get_cloud_label()` caches results per parent directory to avoid repeated `Path.resolve()` calls for files in the same folder.
- **TagCloud FlowLayout** — Replaced with proper `_FlowContainer` widget that handles `resizeEvent` for correct reflow on window resize.

### Fixed
- **settings_dialog.py** — Fixed `from filepilot.updater import __version__` (module doesn't export it) to `from filepilot import __version__`.
- **main_window.py** — Fixed `_on_nav_changed` names list missing "File Stats" entry causing index mismatch.
- **CI workflow** — Fixed invalid GitHub Actions versions (v6/v7 don't exist) and repaired UTF-8 encoding corruption from PowerShell string operations.

## [0.6.2] - 2026-05-25

### Added
- **Semantic Search** — Embedding-based re-ranking of Whoosh full-text results (`filepilot/core/embeddings.py`). Uses the configured AI provider's `embed()` to cache file embeddings during indexing (stored in `~/.filepilot/embeddings.json`). Search queries are embedded and results re-ranked by cosine similarity (pure Python, no numpy). Toggle via "🔬 Semantic" checkbox in the search panel. 18 new tests.
- **Full i18n coverage** — All 310 translation keys filled for all 18 languages; ~180 missing strings completed across zh-CN/zh-TW/ja/ko/ar/he/th/vi/hi/bn/tr/fr/de/es/it/pt-BR/ru. Includes search filter labels, settings descriptions, directory tree placeholders, and semantic search UI.
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
- **README version attribution** — Corrected version history: 0.6.1 features are now credited to 0.6.1, 0.6.2 features credited to 0.6.2

### Added (tests)
- `test_dashboard_panel.py` — 17 tests covering stats, recent folders/files, signals, EventBus
- `test_main_window_navigation.py` — 8 new tests: separator skipping, invalid index, keyboard mapping, global search
- `test_integration.py` — 5 end-to-end tests: startup, navigation, open directory, toolbar state, global search
- `test_embeddings.py` — 18 tests: cosine similarity (6), EmbeddingCache CRUD+persistence+search (10), embed_text fallback (2)
- `test_i18n.py` — 9 tests: 310 key completeness across all 18 languages (3240 pairs), `t()` interpolation, missing fallback
- `test_index_panel.py` — 41 tests: build/update/clear index, progress signals, cancellation, context menu, error handling, stat refresh

## [0.6.1] - 2026-05-20

### Added
- **19 test files across all 10 panels** — Dashboard (5), Duplicates (11), File Browser (17), Index (6), Organize (9), Preview (4), Search (10), Settings (4), Summary (7), Main Window (7); total 80 new panel tests
- **i18n completeness check** — `tests/test_i18n.py` validates that all 18 languages have every translation key defined
- **Refined test framework** — Named `_TestSignals` classes for QObject signal-based panels, `FixtureFactory` with `scan_test_directory` context manager, `categorization_test_data` fixture for 21-file category test set

### Fixed
- **Dashboard panel `_refresh_stats` crash** — Guards against missing `app_state` with null-safe attribute access
- **Search panel `t()` interpolation** — `settings_search` key missing `{0}` placeholder in 14 languages caused `KeyError` on format; all 14 fixed
- **Search panel thread‑safety** — `search_text` / `settings_search` EmittingStr → typed `WorkerSignals(str, list)`, fixes runtime `QObject` parent warning
- **Settings panel thread‑safety** — 6 EmittingStr → typed `WorkerSignals` fixes
- **File browser `dirname` unbound variable** — `_on_open` now correctly uses `self.source_dir`
- **Markdown extractor `ModuleNotFoundError`** — Added guard with user‑visible warning message
- **Warning-free test run** — All 12 detected `DeprecationWarning`s and `ResourceWarning`s resolved (QTimer deleteLater, QThreadPool reparent, QPixmap default construct, QLayout addLayout spacing, QDialog setResult after close, QProcess kill guard)

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
