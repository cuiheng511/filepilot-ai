# Plugin SDK Guide

FilePilot AI supports third-party file content extractor plugins.
Plugins extend which file types the search engine can index and summarize.

## Quick Start

1. Create a `.py` file in `~/.filepilot/plugins/`
2. Subclass `BaseFileExtractor` and implement `supports()` and `extract_text()`
3. Restart FilePilot — your plugin is automatically discovered
4. To reload without restarting: go to **Plugins** panel and click **Reload**

## Reference Implementation

See `filepilot/extractors/example_plugin.py` for a complete working example with two extractors (CSV Analyzer and Log File Parser).

## BaseFileExtractor API

```python
from pathlib import Path
from filepilot.core.plugin_system import BaseFileExtractor

class MyExtractor(BaseFileExtractor):
    # ── Optional class-level metadata ──
    display_name = "My Extractor"          # Human-readable name
    description = "Extracts from .xyz"     # Short description
    version = "1.0.0"                      # Plugin version
    extensions = [".xyz", ".abc"]          # Supported file extensions

    # ── Required: must return True for extensions you support ──
    def supports(self, extension: str) -> bool:
        return extension.lower() in self.extensions

    # ── Required: extract full text content ──
    def extract_text(self, file_path: Path) -> str | None:
        # Return the file's text content, or None on failure
        if not file_path.exists():
            return None
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    # ── Optional: extract structured metadata ──
    def extract_metadata(self, file_path: Path) -> dict:
        return {"key": "value"}  # Return any serializable dict
```

## Required Methods

### `supports(extension: str) -> bool`

Return `True` if this extractor can handle the given file extension.
Extension is always lowercase with a leading dot, e.g. `".pdf"`, `".md"`.

### `extract_text(file_path: Path) -> str | None`

Extract the full text content from the file. This text is indexed by Whoosh
and becomes searchable via the Search panel.

| Return value | Meaning |
|---|---|
| `str` | Successful extraction — content is indexed |
| `None` | Extraction failed — file is skipped |

## Optional Methods

### `extract_metadata(file_path: Path) -> dict`

Return structured metadata as a flat dict. Currently used for display
in the Plugins panel. All values must be JSON-serializable.

## Class-Level Attributes

| Attribute | Type | Required | Default |
|---|---|---|---|
| `display_name` | `str` | No | Class name |
| `description` | `str` | No | Empty string |
| `version` | `str` | No | `"0.1.0"` |
| `extensions` | `list[str]` | No | `[]` |

## Plugin Discovery

Plugins are loaded from `~/.filepilot/plugins/` on startup.
Both single-file plugins (`.py`) and package plugins (`directory/__init__.py`) are supported.

```text
~/.filepilot/plugins/
├── my_csv_reader.py          # Single-file plugin
├── my_image_analyzer.py      # Another single-file plugin
└── my_package_plugin/        # Package plugin
    ├── __init__.py           # Contains extractor class
    ├── helper.py             # Supporting modules
    └── data/                 # Additional resources
```

## Integration Points

Plugins are used in these parts of FilePilot:

### Search Index (`SearchPanel`)
When building the search index, each file's content is extracted using
the matching extractor (built-in or plugin). Plugins take priority over
the built-in text-fallback for extensions they support.

### AI Summary (`SummaryPanel`)
When generating AI summaries, the same extractor pipeline is used to
feed file content to the AI engine.

## Best Practices

1. **Be explicit**: List all supported extensions in the `extensions` class attribute
2. **Handle errors**: Return `None` from `extract_text()` on failure rather than raising
3. **Limit output**: For large files, truncate content to a reasonable size (e.g. 50 KB)
4. **Use stdlib**: Prefer Python built-in modules to avoid forcing users to install extra dependencies
5. **Test your plugin**: Place it in `~/.filepilot/plugins/`, build the index, and verify the search finds the expected content

## Troubleshooting

| Symptom | Cause |
|---|---|
| Plugin not appearing in Plugins panel | File is not in `~/.filepilot/plugins/` or has syntax error |
| `extract_text()` not called for my extension | `supports()` returns `False` for that extension |
| Index builds but search finds no content | `extract_text()` returned `None` or empty string |
| Plugin loads but crashes on certain files | Add `try/except` around file I/O in `extract_text()` |

Check the application log for plugin-related warnings and errors.
