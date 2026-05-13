<div align="center">

# 🚀 FilePilot AI

### Smart File Management — Powered by AI

**Scan · Search · Deduplicate · Summarize · Organize**

A local-first desktop assistant that helps you understand large folders, find files faster, detect duplicates, and generate AI-powered summaries — all without leaving your machine.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?style=flat&logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![Whoosh](https://img.shields.io/badge/Search-Whoosh-2563EB?style=flat)](https://whoosh.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)
[![CI](https://github.com/cuiheng511/filepilot-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/cuiheng511/filepilot-ai/actions)

</div>

---

## ✨ Highlights

<table>
<tr>
<td width="50%">

### 📂 Smart Scanning
Recursive folder scanning with metadata collection, file type detection, and size breakdown visualization.

### 🔍 Full-Text Search
Whoosh-powered local index. Search by filename, content, type, or date — no cloud dependency.

### 🤖 AI Summaries
Extract key points from PDFs, code, Markdown, and Office documents using local or cloud AI.

</td>
<td width="50%">

### 🔗 Duplicate Detection
Three-stage dedup: size grouping → partial hash → full SHA256 confirmation. Reclaim disk space.

### 📋 Smart Organization
Auto-categorize files by type, date, or size. One-click undo if anything goes wrong.

### 🖱️ Drag & Drop
Drop folders onto the file browser to navigate instantly. Preview file content with a single click.

</td>
</tr>
</table>

---

## 🎬 Features at a Glance

| Feature | Description |
|---------|-------------|
| 📂 **File Browser** | Tree navigation + table view + file preview + drag-and-drop |
| 🔍 **Search** | Natural language search with fuzzy matching and content indexing |
| 📋 **Organizer** | Auto-classify, smart rename, preview before execute, one-click undo |
| 🔗 **Duplicates** | Content-hash dedup with group visualization and space savings |
| 📝 **AI Summary** | Single file or batch processing with keyword extraction |
| 🗂️ **Index Manager** | Build, update, and manage Whoosh full-text search indexes |
| 🎨 **Themes** | Dark/light mode with hot-reload QSS stylesheets |
| 🌐 **i18n** | English/Chinese language support via `t()` translation framework |
| 📊 **Disk Usage** | Category size breakdown with bar chart in scan results |
| 📥 **Export** | Save scan results as CSV or JSON for downstream processing |
| ⌨️ **CLI** | Full command-line interface for power users and automation |

---

## 🚀 Quick Start

### Requirements

- **Python 3.10+** (Windows / macOS / Linux)
- **Optional:** Ollama, llama.cpp, or OpenAI-compatible server for local AI
- **Optional:** OpenAI / Anthropic API key for cloud AI

### Install & Run

```bash
# Clone
git clone https://github.com/cuiheng511/filepilot-ai.git
cd filepilot-ai

# Setup
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run GUI
python -m filepilot.main

# Or use CLI
python -m filepilot.cli scan ~/Documents
python -m filepilot.cli duplicates ~/Downloads
python -m filepilot.cli export ~/Projects --format csv -o report.csv
python -m filepilot.cli disk-usage ~/
```

---

## 🤖 AI Providers

FilePilot AI supports **5 providers** through a unified interface:

<table>
<tr>
<th>Provider</th>
<th>Type</th>
<th>Models</th>
<th>Setup</th>
</tr>
<tr>
<td><b>Ollama</b></td>
<td>🏠 Local</td>
<td>qwen, llama, mistral, gemma</td>
<td><code>ollama pull qwen2.5:7b</code></td>
</tr>
<tr>
<td><b>llama.cpp</b></td>
<td>🏠 Local</td>
<td>Any GGUF model</td>
<td>Start llama.cpp server</td>
</tr>
<tr>
<td><b>OpenAI</b></td>
<td>☁️ Cloud</td>
<td>GPT-4o, GPT-4o-mini</td>
<td>Set <code>OPENAI_API_KEY</code></td>
</tr>
<tr>
<td><b>Anthropic</b></td>
<td>☁️ Cloud</td>
<td>Claude Sonnet, Opus, Haiku</td>
<td>Set <code>ANTHROPIC_API_KEY</code></td>
</tr>
<tr>
<td><b>Custom</b></td>
<td>☁️ Cloud</td>
<td>DeepSeek, Moonshot, etc.</td>
<td>Any OpenAI-compatible API</td>
</tr>
</table>

> Configure in **Settings → AI Provider** dropdown.

---

## 📁 Project Structure

```
filepilot-ai/
├── filepilot/
│   ├── ai/              # AI providers (base + Ollama/llama.cpp/OpenAI/Anthropic)
│   ├── core/            # Scanner, indexer, organizer, duplicate finder
│   ├── extractors/      # PDF, Markdown, Code, Image, DOCX, XLSX, PPTX
│   ├── styles/          # QSS themes (dark.qss, light.qss) + ThemeManager
│   ├── ui/              # PySide6 desktop panels
│   ├── cli.py           # CLI entry point
│   ├── i18n.py          # Internationalization (zh/en)
│   ├── log.py           # Logging configuration
│   └── utils/           # File utilities, categories
├── tests/               # 93 unit tests
├── .github/
│   ├── workflows/ci.yml # CI: lint + test on 3 platforms × 3 Python versions
│   ├── dependabot.yml   # Auto dependency updates
│   └── ISSUE_TEMPLATE/  # Bug report + feature request
├── FilePilot.spec       # PyInstaller build config
├── CONTRIBUTING.md      # Contribution guide
├── CHANGELOG.md         # Release notes
└── requirements.txt     # Dependencies
```

---

## 🛠️ Development

```bash
# Install dev dependencies
pip install -e ".[test]"

# Run tests
pytest

# Lint
ruff check filepilot/ --select E,F,W --ignore E501

# Build executable
pyinstaller FilePilot.spec --noconfirm
```

---

## 🗺️ Roadmap

- [ ] Packaged Windows/macOS installers
- [ ] Application screenshots and demo GIFs
- [ ] Persistent AI summary caching
- [ ] File watching for auto-organization
- [ ] Multilingual UI (Korean, Japanese)
- [ ] Large-folder indexing performance optimization

---

## 🔒 Security & Privacy

- **Local-first:** Scanning, indexing, dedup, and extraction run entirely on your machine
- **AI is optional:** Cloud providers only receive content you explicitly send for summarization
- **No telemetry:** Zero analytics, zero tracking, zero phone-home
- **API keys stay local:** Stored in `~/.filepilot/settings.json`, never transmitted except to your chosen AI provider

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

| Project | Purpose |
|---------|---------|
| [PySide6](https://pypi.org/project/PySide6/) | Desktop UI framework |
| [Whoosh](https://whoosh.readthedocs.io/) | Full-text search engine |
| [Ollama](https://ollama.com/) | Local LLM runtime |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF text extraction |
| [python-docx](https://python-docx.readthedocs.io/) | Word document extraction |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel spreadsheet extraction |
| [python-pptx](https://python-pptx.readthedocs.io/) | PowerPoint extraction |

---

<div align="center">

**Built with ❤️ using Python + PySide6 + Whoosh + AI**

</div>
