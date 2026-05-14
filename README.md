<div align="center">

<img src="filepilot/resources/app.ico" width="96" alt="FilePilot AI" />

# FilePilot AI

**Smart File Manager — Scan · Search · Deduplicate · Summarize · Organize**

A local-first desktop assistant that helps you understand large folders, find files faster, detect duplicates, and generate AI-powered summaries — all without leaving your machine.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/UI-PySide6%20(Qt6)-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![Whoosh](https://img.shields.io/badge/Search-Whoosh-2563EB?style=for-the-badge)](https://whoosh.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/cuiheng511/filepilot-ai/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/cuiheng511/filepilot-ai/actions)
[![Tests](https://img.shields.io/badge/Tests-198%2F198%20passed-brightgreen?style=for-the-badge)]()

</div>

---

## Why FilePilot AI?

> How many files on your drive have you forgotten about? How much space is wasted on duplicates?

FilePilot AI is a **fully local** intelligent file management tool. It doesn't upload your data, doesn't track your behavior — it just helps you keep your files organized.

---

## ✨ Features

<table>
<tr>
<td width="33%" align="center">

### 📂 Smart Scanning

Recursive directory traversal<br/>
File type detection<br/>
Disk usage breakdown<br/>
Drag-and-drop folders

</td>
<td width="33%" align="center">

### 🔍 Full-Text Search

Whoosh-powered local index<br/>
Fuzzy + content search<br/>
Filter by type / date / size<br/>
Result highlighting

</td>
<td width="33%" align="center">

### 🤖 AI Summaries

PDF / Markdown / Code summaries<br/>
Automatic keyword extraction<br/>
Local + cloud AI support<br/>
Batch processing

</td>
</tr>
<tr>
<td align="center">

### 🔗 Duplicate Detection

Three-stage dedup algorithm<br/>
Size grouping → partial hash → full SHA256<br/>
One-click space reclaim<br/>
Similar filename detection

</td>
<td align="center">

### 📋 Smart Organization

Classify by type / date / size / extension<br/>
Smart rename templates<br/>
Preview before execute<br/>
One-click undo

</td>
<td align="center">

### 🎨 Modern UI

Dark / light theme toggle<br/>
QSS hot-reload<br/>
Keyboard shortcuts (Ctrl+1~6)<br/>
Floating notification toasts

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FilePilot AI                          │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  UI      │  AI      │  Core    │Extractors│   Utilities    │
│ PySide6  │ Provider │ Scanner  │ PDF      │ file_utils     │
│ Panels   │ Ollama   │ Indexer  │ Markdown │ config         │
│ Themes   │ OpenAI   │ Organizer│ Code     │ task_queue     │
│ Toast    │ Anthropic│ Finder   │ DOCX     │ file_watcher   │
│ i18n     │ llama.cpp│ Watcher  │ XLSX/PPTX│ logging        │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
```

---

## 🚀 Quick Start

### Requirements

- **Python 3.10+** (Windows / macOS / Linux)
- **Optional:** Ollama or llama.cpp for local AI
- **Optional:** OpenAI / Anthropic API key for cloud AI

### Install & Run

```bash
# Clone
git clone https://github.com/cuiheng511/filepilot-ai.git
cd filepilot-ai

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Launch GUI
python -m filepilot.main
```

### CLI Mode

```bash
# Scan a directory
python -m filepilot.cli scan ~/Documents

# Find duplicate files
python -m filepilot.cli duplicates ~/Downloads

# Export file inventory
python -m filepilot.cli export ~/Projects --format csv -o report.csv

# Disk usage analysis
python -m filepilot.cli disk-usage ~/

# Search indexed files
python -m filepilot.cli search ~/Documents "machine learning"

# Organize files (dry-run first)
python -m filepilot.cli organize ~/Downloads ~/Sorted --dry-run --rules category date
```

---

## 🤖 AI Providers

FilePilot supports **5 providers** through a unified `AIProvider` interface:

| Provider | Type | Recommended Models | Setup |
|----------|------|-------------------|-------|
| **Ollama** | 🏠 Local | `qwen2.5:7b`, `llama3.1:8b` | `ollama pull qwen2.5:7b` |
| **llama.cpp** | 🏠 Local | Any GGUF model | Start llama.cpp server |
| **OpenAI** | ☁️ Cloud | `gpt-4o-mini`, `gpt-4o` | Settings → AI Engine → API Key |
| **Anthropic** | ☁️ Cloud | `claude-sonnet-4-20250514` | Settings → AI Engine → API Key |
| **Custom** | ☁️ Cloud | DeepSeek, Moonshot, etc. | Any OpenAI-compatible endpoint |

> **Security:** API keys are stored in your OS credential manager (Windows Credential Manager / macOS Keychain / Linux Secret Service), never written to config files.

---

## 📁 Project Structure

```
filepilot-ai/
├── filepilot/
│   ├── ai/                  # AI engine layer
│   │   ├── base.py          #   AIProvider abstract base class
│   │   ├── local_ai.py      #   Ollama / llama.cpp providers
│   │   ├── cloud_ai.py      #   OpenAI / Anthropic (with retry)
│   │   └── summarizer.py    #   Intelligent summary generator
│   ├── core/                # Core business logic
│   │   ├── file_scanner.py  #   Directory scanning
│   │   ├── indexer.py       #   Whoosh full-text index
│   │   ├── file_organizer.py#   File classification & rename
│   │   ├── duplicate_finder.py # Content-hash deduplication
│   │   ├── file_watcher.py  #   Directory monitoring (watchdog)
│   │   ├── task_queue.py    #   Background task queue
│   │   └── config.py        #   Unified settings persistence
│   ├── extractors/          # Content extractors
│   │   ├── pdf_extractor.py
│   │   ├── markdown_extractor.py
│   │   ├── code_extractor.py
│   │   ├── image_extractor.py
│   │   ├── docx_extractor.py
│   │   ├── xlsx_extractor.py
│   │   └── pptx_extractor.py
│   ├── styles/              # Theme system
│   │   ├── manager.py       #   ThemeManager (hot-reload)
│   │   └── themes/          #   dark.qss / light.qss
│   ├── ui/                  # Desktop UI (PySide6)
│   │   ├── main_window.py   #   Main window + navigation
│   │   ├── notification.py  #   Floating toast notifications
│   │   ├── base_panel.py    #   Panel base class
│   │   └── ...              #   6 feature panels
│   ├── app.py               # App bootstrap & service injection
│   ├── cli.py               # CLI entry point
│   ├── i18n.py              # Internationalization (en/zh)
│   └── log.py               # Logging configuration
├── tests/                   # 198 unit tests
├── .github/
│   ├── workflows/ci.yml     # CI: 2 platforms × 3 Python versions
│   └── dependabot.yml       # Automatic dependency updates
├── FilePilot.spec           # PyInstaller build config
├── CONTRIBUTING.md          # Contribution guide
└── CHANGELOG.md             # Release notes
```

---

## 🛠️ Development

```bash
# Install dev + test dependencies
pip install -e ".[test,dev]"

# Run tests
pytest                                    # Full suite
pytest --cov=filepilot --cov-report=html  # With coverage report

# Lint & format
ruff check .          # Lint
ruff format --check . # Format check
mypy filepilot/       # Type checking

# Build standalone executable
pyinstaller FilePilot.spec --noconfirm
```

### CI Pipeline

| Job | Runner | Description |
|-----|--------|-------------|
| **Lint** | Ubuntu × py3.10–3.12 | `ruff check` + `ruff format --check` |
| **Test** | Ubuntu + Windows × py3.10–3.12 | `pytest --cov` + Codecov upload |
| **Build** | Windows (after lint+test pass) | PyInstaller package + artifact upload |

---

## 🗺️ Roadmap

- [x] File scanning & browsing
- [x] Full-text search indexing
- [x] AI summary generation
- [x] Duplicate file detection
- [x] Auto-organization with undo
- [x] CLI tool
- [x] Dark / light themes
- [x] English / Chinese i18n
- [x] Background task queue
- [x] Directory watching (watchdog)
- [x] Notification toast system
- [ ] Windows / macOS installers
- [ ] Application screenshots & demo GIFs
- [ ] Persistent AI summary caching
- [ ] Large-folder indexing optimization
- [ ] Additional language support (Japanese, Korean)

---

## 🔒 Security & Privacy

| Principle | Details |
|-----------|---------|
| **Local-first** | Scanning, indexing, dedup, and extraction run entirely on your machine |
| **AI is optional** | Cloud providers only receive content you explicitly send for summarization |
| **Zero telemetry** | No analytics, no tracking, no phone-home |
| **Secure key storage** | API keys stored in OS credential manager via `keyring`, never in config files |
| **Safe deletion** | Duplicate removal uses system recycle bin (`send2trash`) |

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development environment setup
- Code style guidelines (ruff + mypy)
- Commit conventions (Conventional Commits)
- Pull request workflow

---

## 📄 License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

## 🙏 Acknowledgements

| Project | Purpose |
|---------|---------|
| [PySide6](https://pypi.org/project/PySide6/) | Qt6 desktop UI framework |
| [Whoosh](https://whoosh.readthedocs.io/) | Pure-Python full-text search engine |
| [Ollama](https://ollama.com/) | Local LLM runtime |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF text extraction |
| [watchdog](https://github.com/gorakhargosh/watchdog) | Filesystem monitoring |
| [send2trash](https://github.com/arsenetar/send2trash) | Cross-platform safe deletion |
| [python-docx](https://python-docx.readthedocs.io/) | Word document extraction |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel spreadsheet extraction |
| [python-pptx](https://python-pptx.readthedocs.io/) | PowerPoint extraction |

---

<div align="center">

**Built with ❤️ in Python**

[⬆ Back to top](#filepilot-ai)

</div>
