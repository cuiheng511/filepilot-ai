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
| AI summaries | Supports Ollama, llama.cpp, OpenAI, Anthropic, and any OpenAI-compatible API. |
| Smart organization | Suggests and applies file organization actions with one-click undo. |
| Drag-and-drop | Drop folders onto the file browser to navigate instantly. |
| File preview | Select a file to preview its content in the bottom panel. |
| Export | Export scan results as CSV or JSON for downstream processing. |
| Disk usage | Category size breakdown with bar chart visualization. |
| Theme toggle | Dark/light theme switch from the toolbar. |
| CLI interface | Power users can scan, search, organize, and export from the command line. |

## Quick Start

### Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- Optional: Ollama, llama.cpp, or any OpenAI-compatible server for local AI
- Optional: OpenAI / Anthropic API key for cloud AI

### Installation

```bash
git clone https://github.com/cuiheng511/filepilot-ai.git
cd filepilot-ai
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the App

```bash
python -m filepilot.main
```

### Run the CLI

```bash
python -m filepilot.cli scan /path/to/dir
python -m filepilot.cli duplicates /path/to/dir
python -m filepilot.cli export /path/to/dir --format csv -o results.csv
python -m filepilot.cli disk-usage /path/to/dir
```

## AI Configuration

FilePilot AI supports 5 AI providers through a unified interface:

| Provider | Type | Use Case |
|----------|------|----------|
| **Ollama** | Local | qwen, llama, mistral and other Ollama models |
| **llama.cpp / LM Studio** | Local | Any model served via llama.cpp server or LM Studio |
| **OpenAI** | Cloud | GPT-4o, GPT-4o-mini, and any OpenAI-compatible API (DeepSeek, Moonshot, etc.) |
| **Anthropic** | Cloud | Claude Sonnet, Opus, Haiku |
| **Custom** | Cloud | Any endpoint that implements the OpenAI chat completions API |

Open Settings → AI Provider to select and configure your preferred provider.

## Project Structure

```text
filepilot-ai/
|-- filepilot/
|   |-- ai/           # AI providers (base class + Ollama/llama.cpp/OpenAI/Anthropic)
|   |-- core/         # Scanner, indexer, organizer, duplicate finder
|   |-- extractors/   # Text and metadata extraction modules
|   |-- ui/           # PySide6 desktop interface
|   |-- cli.py        # CLI entry point
|   `-- utils/        # Shared utilities
|-- tests/            # Test suite
|-- pyproject.toml    # Project metadata
|-- requirements.txt  # Runtime dependencies
`-- README.md
```

## Development

```bash
pip install -e ".[test]"
pytest
```

## Roadmap

- [ ] Add a packaged Windows/macOS installer
- [ ] Add application screenshots and demo GIFs
- [ ] Improve large-folder indexing performance
- [ ] Add persistent AI summary caching
- [ ] Expand document extractor coverage (DOCX, XLSX, PPTX)
- [ ] Add multilingual UI support
- [ ] Add file watching for auto-organization

## Security and Privacy

FilePilot AI is built around local file workflows. Folder scanning, indexing, duplicate detection, and metadata extraction are designed to run locally.

Cloud AI features are optional. If you enable a cloud provider, review which selected file content may be sent to that provider. For sensitive folders, use local AI mode or disable AI summaries.

Do not commit API keys, passwords, or personal access tokens.

## License

MIT License. See [LICENSE](LICENSE).

## Acknowledgements

- [PySide6](https://pypi.org/project/PySide6/) — Desktop interface
- [Whoosh](https://whoosh.readthedocs.io/) — Full-text search
- [Ollama](https://ollama.com/) — Local model execution
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF extraction
