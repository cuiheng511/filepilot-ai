# Contributing to FilePilot AI

Thanks for your interest in contributing! This guide will help you get started.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running the App](#running-the-app)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Building with PyInstaller](#building-with-pyinstaller)
- [CI Pipeline](#ci-pipeline)
- [Code Style](#code-style)
- [Commit Conventions](#commit-conventions)
- [Pull Request Workflow](#pull-request-workflow)

---

## Development Setup

### Prerequisites

- **Python 3.10+**
- **Git**
- **pip** (latest version recommended)

### Step-by-step

```bash
# 1. Clone the repository
git clone https://github.com/<your-org>/filepilot-ai.git
cd filepilot-ai

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# Windows (cmd):
.venv\Scripts\activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 4. Install the project in editable mode with test dependencies
pip install -e ".[test]"

# 5. (Optional) Install linting tools
pip install ruff mypy

# 6. Verify everything works
python -m filepilot.main
```

> **Tip:** If you only need the runtime dependencies (e.g., to just run the app):
> ```bash
> pip install -r requirements.txt
> ```

### Linux Qt Requirements

If you're on Linux, PySide6 requires some system libraries. Install them with:

```bash
sudo apt-get update -qq
sudo apt-get install -y -qq \
  libegl1 \
  libgl1 \
  libxkbcommon-x11-0 \
  libxcb-cursor0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-randr0 \
  libxcb-render-util0 \
  libxcb-shape0 \
  libxcb-xfixes0 \
  libxcb-xinerama0 \
  libxcb-xkb1 \
  libxcb-xv0 \
  libxrender1 \
  xvfb
```

---

## Project Structure

```
filepilot-ai/
├── filepilot/              # Main application package
│   ├── ai/                 # AI provider integrations
│   │   ├── cloud_ai.py     #   OpenAI / Anthropic / Custom
│   │   ├── local_ai.py     #   Ollama / llama.cpp
│   │   └── summarizer.py   #   AI-powered summary generation
│   ├── core/               # Core business logic
│   │   ├── file_scanner.py #   Directory scanning
│   │   ├── duplicate_finder.py # Duplicate detection
│   │   ├── file_organizer.py #   File organization
│   │   └── indexer.py      #   Whoosh search index
│   ├── extractors/         # Content extractors
│   │   ├── pdf_extractor.py
│   │   ├── markdown_extractor.py
│   │   ├── code_extractor.py
│   │   └── image_extractor.py
│   ├── styles/             # QSS theme files
│   │   ├── manager.py      #   ThemeManager (hot-reload)
│   │   └── themes/
│   │       ├── dark.qss
│   │       └── light.qss
│   ├── ui/                 # Qt UI panels
│   │   ├── main_window.py  #   Main window, nav, theme toggle
│   │   ├── settings_dialog.py # Settings dialog
│   │   ├── base_panel.py   #   BasePanel (shared layouts)
│   │   ├── summary_panel.py
│   │   ├── search_panel.py
│   │   ├── index_panel.py
│   │   ├── file_browser.py
│   │   ├── organize_panel.py
│   │   └── duplicates_panel.py
│   ├── utils/              # Utility helpers
│   ├── app.py              # App bootstrap & settings
│   ├── cli.py              # CLI entry point
│   └── main.py             # GUI entry point
├── tests/                  # Test suite (pytest)
│   ├── conftest.py         #   Shared fixtures
│   ├── test_file_scanner.py
│   ├── test_file_organizer.py
│   ├── test_index_panel.py
│   ├── test_organize_panel.py
│   └── test_summary_panel.py
├── scripts/
│   └── push_to_github.py
├── .github/workflows/
│   └── ci.yml              # CI pipeline
├── pyproject.toml           # Project config & tool settings
├── requirements.txt         # Runtime dependencies
└── FilePilot.spec           # PyInstaller spec
```

---

## Running the App

### GUI Mode

```bash
python -m filepilot.main
```

### CLI Mode

FilePilot includes a CLI for headless file operations:

```bash
# Scan a directory
python -m filepilot.cli scan /path/to/dir

# Search indexed files
python -m filepilot.cli search /path/to/index "query"

# Find duplicates
python -m filepilot.cli duplicates /path/to/dir

# Organize files (dry-run first!)
python -m filepilot.cli organize /path/src /path/dst --dry-run

# Export metadata
python -m filepilot.cli export /path/to/dir --format json -o output.json

# Disk usage analysis
python -m filepilot.cli disk-usage /path/to/dir
```

---

## Running Tests

### Run all tests

```bash
python -m pytest tests/
```

### Run with coverage

```bash
python -m pytest tests/ --cov=filepilot --cov-report=term-missing
```

For an HTML report:

```bash
python -m pytest tests/ --cov=filepilot --cov-report=html
# then open htmlcov/index.html
```

### Run a specific test file

```bash
python -m pytest tests/test_file_scanner.py -v
```

### Run a specific test

```bash
python -m pytest tests/test_file_scanner.py::test_scan_directory -v
```

### Run with verbose output on failures

```bash
python -m pytest tests/ -v --tb=long
```

### Linux note (headless Qt)

Tests that create Qt widgets require a display. On Linux (headless or CI), use `xvfb-run`:

```bash
xvfb-run --auto-servernum python -m pytest tests/ -v --tb=short
```

### Windows note

Qt tests work out of the box on Windows — no special setup needed.

---

## Code Quality

### Syntax check

```bash
python check_syntax.py
```

This script (`check_syntax.py`) walks through all `.py` files in the project and validates them using Python's `ast` module.

### Linting (ruff)

```bash
# Check for lint errors
ruff check .

# Auto-fix what ruff can fix
ruff check --fix .
```

### Formatting (ruff)

```bash
# Check formatting
ruff format --check .

# Auto-format
ruff format .
```

### Type checking (mypy)

```bash
mypy filepilot/
```

### Run all quality checks at once

```bash
ruff check . && ruff format --check . && mypy filepilot/ && python check_syntax.py && python -m pytest tests/ --cov=filepilot -v --tb=short
```

---

## Building with PyInstaller

FilePilot AI is packaged with **PyInstaller** on all three platforms. See [docs/BUILD.md](docs/BUILD.md) for complete build instructions covering Windows (Inno Setup installer, code signing), Linux (AppImage, Docker), and macOS (.app + .dmg, signing, notarization).

For a quick local build on Windows:

```bash
pip install pyinstaller
pyinstaller FilePilot.spec
```

The built executable will be at `dist/FilePilot/FilePilot.exe`.

---

## CI Pipeline

The project uses GitHub Actions for continuous integration. The pipeline is defined in `.github/workflows/ci.yml` and includes three jobs:

| Job | Runner | What it does |
|-----|--------|-------------|
| **lint** | ubuntu-latest (×3 Python versions) | `ruff check` + `ruff format --check` |
| **test** | ubuntu-latest, windows-latest (×3 Python versions) | `pytest` with coverage. Linux runs via `xvfb-run`. Coverage reported to Codecov. |
| **build-windows** | windows-latest | PyInstaller + Inno Setup → `.exe` installer |
| **build-linux** | ubuntu-latest | PyInstaller + appimagetool → `.AppImage` |
| **build-macos** | macos-latest | PyInstaller + create-dmg → `.dmg` |

To trigger CI manually:

```bash
gh workflow run CI
```

Or go to the Actions tab on GitHub and click **Run workflow**.

See [docs/BUILD.md](docs/BUILD.md) for detailed build and CI pipeline information.

---

## Code Style

### Python

- **Target:** Python 3.10+
- **Formatter:** `ruff format` (double quotes, spaces, 100 char line length)
- **Linter:** `ruff` with rulesets: `F` (pyflakes), `E`/`W` (pycodestyle), `I` (isort), `N` (pep8-naming)
- **Type hints:** Encouraged but not strictly enforced (`mypy` with `disallow_untyped_defs = false`)

### Qt / UI

- Use `setObjectName()` on widgets instead of inline `setStyleSheet()`.
- All styles should live in `filepilot/styles/themes/*.qss`.
- New panels should inherit from `BasePanel`.
- Connect signals in `__init__`, not in separate setup methods.

### QSS

- When adding a new styled widget, add its selector to **both** `dark.qss` and `light.qss`.
- Object names should follow the pattern `camelCase` (e.g., `btnGenerate`, `fileList`).
- Use the `ThemeManager` (`filepilot/styles/manager.py`) to apply themes — never call `QApplication.setStyleSheet()` directly.

### Imports

Import order (handled by `ruff` isort):

1. Standard library
2. Third-party (PySide6, Whoosh, etc.)
3. Local (`filepilot.*`)

---

## Internationalization (i18n)

FilePilot has a lightweight translation framework at `filepilot/i18n.py`. It currently supports **Chinese (zh)** and **English (en)**, with English as the default.

### API

| Function | Description |
|----------|-------------|
| `t(key, **kwargs)` | Translate a string by key. Falls back to English, then the key itself if not found. Supports `str.format()` via kwargs. |
| `set_language(lang)` | Switch language (`"zh"` or `"en"`). |
| `get_language()` | Get the current language code. |
| `load_language_from_settings()` | Load language preference from `~/.filepilot/settings.json`. |

### How to use

```python
from filepilot.i18n import t

# Simple translation
label.setText(t("nav_search"))          # "🔍  Search" (en) / "🔍  文件搜索" (zh)

# With format arguments (in translation string, use {name})
#   "greeting": "Hello, {name}!"         (en)
#   "greeting": "你好，{name}！"          (zh)
label.setText(t("greeting", name="World"))
```

### How to add a new language

1. Add a new key to `_translations` dict in `filepilot/i18n.py`:

   ```python
   _translations: dict[str, dict[str, str]] = {
       "zh": { ... },
       "en": { ... },
       "ja": {                       # ← new language
           "ok": "OK",
           "cancel": "キャンセル",
           # ... translate all keys
       },
   }
   ```

2. Add the language option to `settings_dialog.py` (language selector in the General tab).

### How to add a new translation key

1. Add the key to **all** language entries in `_translations`:

   ```python
   "en": {
       # ... existing keys
       "my_new_feature_title": "New Feature",
       "my_new_feature_desc": "Description of the new feature",
   },
   "zh": {
       # ... existing keys
       "my_new_feature_title": "新功能",
       "my_new_feature_desc": "新功能描述",
   },
   ```

2. Replace hardcoded strings in UI code with `t("my_new_feature_title")` calls.

### Best practices

- **Key naming:** Use `snake_case`, grouped by feature area (e.g., `browse_title`, `search_placeholder`, `summary_generate`).
- **Always update both languages:** Adding a key to only one language will cause fallback to English, but keeping them in sync avoids confusion.
- **Keep keys in the same order** across languages for easy comparison.
- **Use format strings** for dynamic content rather than string concatenation:

  ```python
  # ✅ Good
  t("file_count", count=42)   # translation: "{count} files found"

  # ❌ Bad
  f"{count} files found"      # can't be translated
  ```

- **Do not translate** file paths, technical error messages, or debug logs.

### Current status

The i18n framework is set up but **not yet integrated** into the UI code (`filepilot/ui/*.py`). All UI strings are currently hardcoded in English. Migrating existing UI strings to use `t()` is an ongoing effort — contributions welcome!

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

[optional body]
```

### Types

| Type     | When to use                              |
|----------|------------------------------------------|
| `feat`   | A new feature                            |
| `fix`    | A bug fix                                |
| `refactor` | Code change that neither fixes nor adds |
| `style`  | Formatting, QSS changes                  |
| `test`   | Adding or updating tests                 |
| `docs`   | Documentation only                       |
| `ci`     | CI pipeline changes                      |
| `chore`  | Tooling, dependencies, misc config       |

### Examples

```
feat: add CLI export command with JSON/CSV support
fix: handle non-UTF-8 filenames during scan
refactor: extract duplicate detection into standalone service
style: add dark/light theme for SettingsDialog
test: add coverage for file_organizer edge cases
docs: update README with CLI usage examples
ci: add codecov integration to test workflow
```

---

## Pull Request Workflow

1. **(Optional) Create an issue** describing the change. Use the appropriate template:
   - [🐛 Bug Report](https://github.com/<your-org>/filepilot-ai/issues/new?template=bug_report.md) — for reporting bugs
   - [✨ Feature Request](https://github.com/<your-org>/filepilot-ai/issues/new?template=feature_request.md) — for suggesting new features
2. **Fork the repo** and create a branch from `main`:

   ```bash
   git checkout -b feat/my-feature
   ```

3. **Make your changes** following the [Code Style](#code-style) guidelines.
4. **Run quality checks** locally:

   ```bash
   ruff check . && ruff format --check . && python -m pytest tests/ -v --tb=short
   ```

5. **Commit** using [Conventional Commits](#commit-conventions).
6. **Push** and open a Pull Request against `main`.
7. **Ensure CI passes** — the pipeline runs lint, test (on all OS / Python versions), and build checks.
8. **Get a review** — at least one maintainer approval is required before merging.

### PR Checklist

- [ ] Code compiles and runs without errors
- [ ] All existing tests pass
- [ ] New tests added for new functionality (if applicable)
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] QSS changes applied to both dark and light themes (if applicable)
- [ ] CHANGELOG.md updated (if applicable)

---

## Security Notes

- **API keys** are stored in the OS credential manager via `keyring`, never in `settings.json` or `.env` files.
- Do not commit any real API keys, tokens, or credentials to the repository.
- If you add a new credential, store it via `keyring.set_password("filepilot-ai", "<key_name>", <value>)`.

---

## Need Help?

- [🐛 Report a Bug](https://github.com/<your-org>/filepilot-ai/issues/new?template=bug_report.md)
- [✨ Request a Feature](https://github.com/<your-org>/filepilot-ai/issues/new?template=feature_request.md)
- [💬 Start a Discussion](https://github.com/<your-org>/filepilot-ai/discussions)

Happy contributing! 🚀
