<div align="center">

<img src="filepilot/resources/app.png" width="132" alt="FilePilot AI logo" />

# FilePilot AI

**A local-first AI file manager for scanning, searching, deduplicating, summarizing, and organizing your files.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/Desktop-PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![Search](https://img.shields.io/badge/Search-Whoosh-2563EB?style=for-the-badge)](https://whoosh.readthedocs.io/)
[![Privacy](https://img.shields.io/badge/Privacy-Local--first-111827?style=for-the-badge)](#security-and-privacy)
[![License](https://img.shields.io/badge/License-MIT-16A34A?style=for-the-badge)](LICENSE)

Version 0.3.0

</div>

---

## Overview

FilePilot AI is a desktop assistant for people who live inside large folders. It helps you inspect local storage, build a searchable file index, detect duplicate content, generate AI summaries, and reorganize messy directories with a preview-first workflow.

The app is designed around one principle: your files stay on your machine unless you explicitly choose a cloud AI provider for summarization.

## Demo

<div align="center">

![FilePilot AI demo](docs/assets/filepilot-demo.gif)

</div>

## Highlights

<table>
<tr>
<td width="33%">

### Smart scanning

- Recursive directory scanning
- File type and category detection
- Size, date, MIME, and hash metadata
- Hidden-file and depth controls

</td>
<td width="33%">

### Fast local search

- Whoosh full-text index
- Keyword and fuzzy matching
- Type, date, and size filters
- Exportable search results

</td>
<td width="33%">

### AI summaries

- PDF, Markdown, code, image, DOCX, XLSX, and PPTX extractors
- Local or cloud AI providers
- Batch-friendly summary workflow
- Unified provider interface

</td>
</tr>
<tr>
<td width="33%">

### Duplicate cleanup

- Size grouping
- Partial hash pre-check
- Full SHA256 verification
- Recycle-bin based deletion

</td>
<td width="33%">

### Safe organization

- Organize by type, date, extension, and size
- Rename templates
- Preview before moving
- Undo log support

</td>
<td width="33%">

### Desktop workflow

- PySide6 native interface
- Light and dark themes
- Tray and background watcher
- Toast notifications and 18 UI languages

</td>
</tr>
</table>

## Screenshots

| Browse | Search |
| --- | --- |
| ![Browse local folders](docs/assets/screenshots/01-browse.png) | ![Search indexed files](docs/assets/screenshots/02-search.png) |

| Organize | Duplicates |
| --- | --- |
| ![Preview file organization](docs/assets/screenshots/03-organize.png) | ![Detect duplicate files](docs/assets/screenshots/04-duplicates.png) |

| AI Summary | Index |
| --- | --- |
| ![Generate AI summaries](docs/assets/screenshots/05-summary.png) | ![Manage search index](docs/assets/screenshots/06-index.png) |

## Icon

The application icon lives in:

- `filepilot/resources/app.png`
- `filepilot/resources/app.ico`

The current icon uses a folder, document, and connected AI nodes to make the product signal clear at small desktop sizes.

## Quick Start

### Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- Optional: Ollama, llama.cpp, or LM Studio for local AI
- Optional: OpenAI, Anthropic, or any OpenAI-compatible endpoint for cloud AI

### Install and Run

```bash
git clone https://github.com/cuiheng511/filepilot-ai.git
cd filepilot-ai

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m filepilot.main
```

### Development Setup

```bash
pip install -e ".[test,dev]"
pytest
ruff check .
ruff format --check .
mypy filepilot
```

## CLI Examples

```bash
# Scan a folder
python -m filepilot.cli scan ~/Documents

# Find duplicate files
python -m filepilot.cli duplicates ~/Downloads

# Export an inventory report
python -m filepilot.cli export ~/Projects --format csv -o report.csv

# Analyze disk usage
python -m filepilot.cli disk-usage ~/

# Search indexed files
python -m filepilot.cli search ~/Documents "machine learning"

# Preview an organization plan before moving anything
python -m filepilot.cli organize ~/Downloads ~/Sorted --dry-run --rules category date
```

## AI Providers

| Provider | Mode | Notes |
| --- | --- | --- |
| Ollama | Local | Good default for private summaries on your own machine |
| llama.cpp / LM Studio | Local | Works with compatible local HTTP servers |
| OpenAI | Cloud | Uses OpenAI-compatible chat completions |
| Anthropic | Cloud | Claude provider support |
| Custom endpoint | Cloud or local | Supports OpenAI-compatible APIs such as self-hosted gateways |

Cloud providers only receive the content you choose to summarize. Local scanning, indexing, organization, and duplicate detection do not require AI.

## Project Structure

```text
filepilot-ai/
|-- filepilot/
|   |-- ai/                  # AI providers and summarization
|   |-- core/                # Scanner, indexer, organizer, duplicates, watcher
|   |-- extractors/          # PDF, Markdown, code, image, DOCX, XLSX, PPTX
|   |-- resources/           # Application icons
|   |-- styles/              # Theme manager and QSS themes
|   |-- ui/                  # PySide6 panels, tray, settings, notifications
|   |-- app.py               # Application bootstrap
|   |-- cli.py               # Command-line interface
|   |-- i18n.py              # Translation catalog
|   `-- main.py              # GUI entry point
|-- tests/                   # Unit and UI tests
|-- scripts/                 # Helper scripts
|-- .github/workflows/       # CI pipeline
|-- FilePilot.spec           # PyInstaller build config
|-- pyproject.toml           # Package metadata and tooling
`-- requirements.txt         # Runtime dependencies
```

## Architecture

```mermaid
flowchart LR
    UI["PySide6 UI"] --> Core["Core services"]
    CLI["CLI"] --> Core
    Core --> Scanner["File scanner"]
    Core --> Indexer["Whoosh indexer"]
    Core --> Duplicates["Duplicate finder"]
    Core --> Organizer["Organizer"]
    Core --> Watcher["Directory watcher"]
    Scanner --> Extractors["Content extractors"]
    Extractors --> Summarizer["AI summarizer"]
    Summarizer --> Providers["Local and cloud AI providers"]
```

## Security and Privacy

| Area | Design |
| --- | --- |
| Local-first workflow | File scanning, indexing, duplicate detection, and organization run locally |
| Optional AI | Summarization can use local models or explicit cloud providers |
| Key storage | API keys use OS keyring when available, with encrypted fallback storage |
| Deletion safety | Duplicate removal uses the system recycle bin through `send2trash` |
| Telemetry | No analytics, tracking, or background phone-home behavior |

## Quality Gates

The repository is set up for:

- `pytest` for unit and UI tests
- `ruff check .` for linting
- `ruff format --check .` for formatting
- `mypy filepilot` for type checking
- `pip check` for dependency consistency

## Build

```bash
pyinstaller FilePilot.spec --noconfirm
```

The PyInstaller spec includes icons, image resources, theme files, extractor dependencies, and watcher dependencies.

## Roadmap

- Application screenshots and demo GIFs
- Windows and macOS signed installers
- Summary cache with invalidation
- Large-folder indexing performance tuning
- More organization templates
- More end-to-end packaging tests

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for environment setup, style rules, and pull request guidance.

## License

FilePilot AI is released under the [MIT License](LICENSE).
