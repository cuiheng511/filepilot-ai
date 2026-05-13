# FilePilot AI

> A local-first desktop assistant for scanning, searching, deduplicating, summarizing, and organizing your files with AI.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![Whoosh](https://img.shields.io/badge/Search-Whoosh-2563EB?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-111827?style=for-the-badge)

FilePilot AI is a desktop file management application built with Python and PySide6. It helps users understand large folders, find files faster, detect duplicates, extract useful metadata, and generate optional AI summaries for documents, code, and research materials.

The project is designed for practical local workflows: cleaning download folders, organizing project archives, exploring personal knowledge bases, and reviewing file collections without relying on a cloud database.

## Key Features

| Area | What FilePilot AI does |
| --- | --- |
| Local scanning | Scans selected folders and collects structured file metadata. |
| Full-text search | Builds a local Whoosh index for fast filename and content search. |
| Duplicate detection | Uses file hashing to identify duplicate files and reduce storage waste. |
| Content extraction | Extracts text and metadata from code, Markdown, PDFs, images, and more. |
| AI summaries | Supports local Ollama models and optional cloud AI providers. |
| Smart organization | Suggests file organization actions based on type, content, and context. |
| Desktop interface | Provides a multi-panel PySide6 UI for non-command-line workflows. |

## Product Preview

The application is organized around focused desktop panels:

- File Browser
- Search
- Index Management
- Duplicate Finder
- Smart Organizer
- AI Summary
- Settings

Screenshots and packaged release assets will be added after the first stable build.

## Quick Start

### Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- Optional: Ollama for local AI summaries
- Optional: OpenAI API key for cloud AI summaries

### Installation

```bash
git clone https://github.com/cuiheng511/filepilot-ai.git
cd filepilot-ai
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the App

```bash
python -m filepilot.main
```

## AI Configuration

FilePilot AI can work with local AI models or cloud AI APIs.

### Local AI with Ollama

Install Ollama from [ollama.com](https://ollama.com), then pull a model:

```bash
ollama pull qwen2.5:7b
```

After that, open FilePilot AI settings and select the local AI mode.

### Cloud AI with OpenAI

Set your API key as an environment variable.

macOS / Linux:

```bash
export OPENAI_API_KEY="your_api_key"
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_api_key"
```

Then select the cloud AI mode in the application settings.

## Project Structure

```text
filepilot-ai/
|-- filepilot/
|   |-- ai/           # Local and cloud AI adapters
|   |-- core/         # Scanner, indexer, organizer, duplicate finder
|   |-- extractors/   # Text and metadata extraction modules
|   |-- ui/           # PySide6 desktop interface
|   `-- utils/        # Shared utilities
|-- scripts/          # Helper scripts
|-- tests/            # Test suite
|-- check_syntax.py   # Syntax validation helper
|-- pyproject.toml    # Project metadata
|-- requirements.txt  # Runtime dependencies
`-- README.md
```

## Core Modules

| Module | Purpose |
| --- | --- |
| `filepilot.core.file_scanner` | Scans folders and records file metadata. |
| `filepilot.core.indexer` | Builds and queries the local search index. |
| `filepilot.core.duplicate_finder` | Detects duplicate files using content hashes. |
| `filepilot.core.file_organizer` | Suggests and applies file organization actions. |
| `filepilot.extractors.*` | Extracts text and metadata from supported file formats. |
| `filepilot.ai.*` | Connects local and cloud AI providers for summaries. |
| `filepilot.ui.*` | Implements the desktop panels and main window. |

## Development

Install the project in editable mode:

```bash
pip install -e ".[test]"
```

Run tests:

```bash
pytest
```

Run a syntax check:

```bash
python check_syntax.py
```

## Roadmap

- [ ] Add a packaged Windows installer
- [ ] Add application screenshots and demo GIFs
- [ ] Improve large-folder indexing performance
- [ ] Add a safer preview workflow before moving files
- [ ] Add persistent AI summary caching
- [ ] Expand document extractor coverage
- [ ] Add multilingual UI support

## Security and Privacy

FilePilot AI is built around local file workflows. Folder scanning, indexing, duplicate detection, and metadata extraction are designed to run locally.

Cloud AI features are optional. If you enable a cloud provider, review which selected file content may be sent to that provider. For sensitive folders, use local AI mode or disable AI summaries.

Do not commit API keys, passwords, or personal access tokens. Use environment variables such as `OPENAI_API_KEY` and `GITHUB_TOKEN` instead.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgements

- [PySide6](https://pypi.org/project/PySide6/) for the desktop interface
- [Whoosh](https://whoosh.readthedocs.io/) for local full-text search
- [Ollama](https://ollama.com/) for local model execution
- [OpenAI](https://openai.com/) for optional cloud AI capabilities
