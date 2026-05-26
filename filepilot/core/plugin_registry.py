"""Plugin Registry — browse and install community plugins from GitHub.

Provides a simple registry of community-contributed extractor plugins
that can be installed with one click from the Plugin Manager panel.

The registry is a JSON file hosted on GitHub (or bundled locally as fallback).
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread

import requests

from filepilot.core.plugin_system import PLUGINS_DIR

logger = logging.getLogger("filepilot.plugin_registry")

# Registry URL — points to a JSON file listing available plugins
REGISTRY_URL = (
    "https://raw.githubusercontent.com/cuiheng511/filepilot-ai/main/plugins/registry.json"
)
REGISTRY_CACHE = Path.home() / ".filepilot" / "plugin_registry_cache.json"
REGISTRY_CACHE_HOURS = 24


@dataclass
class PluginEntry:
    """A plugin available in the registry."""

    name: str
    display_name: str
    description: str
    version: str
    author: str
    url: str  # Raw URL to the .py file
    extensions: list[str] = field(default_factory=list)
    installed: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "PluginEntry":
        return cls(
            name=data.get("name", ""),
            display_name=data.get("display_name", data.get("name", "")),
            description=data.get("description", ""),
            version=data.get("version", "0.1.0"),
            author=data.get("author", "unknown"),
            url=data.get("url", ""),
            extensions=data.get("extensions", []),
        )


# Built-in registry (fallback when network is unavailable)
_BUILTIN_REGISTRY: list[dict] = [
    {
        "name": "csv_analyzer",
        "display_name": "CSV Analyzer",
        "description": "Reads and analyzes CSV files - extracts headers, row count, and sample data",
        "version": "1.0.0",
        "author": "FilePilot Team",
        "url": "",
        "extensions": [".csv"],
    },
    {
        "name": "log_parser",
        "display_name": "Log File Parser",
        "description": "Parses .log files, extracts timestamps, log levels, and error summaries",
        "version": "1.0.0",
        "author": "FilePilot Team",
        "url": "",
        "extensions": [".log"],
    },
    {
        "name": "yaml_extractor",
        "display_name": "YAML/TOML Extractor",
        "description": "Extracts structured data from YAML and TOML configuration files",
        "version": "1.0.0",
        "author": "Community",
        "url": "https://raw.githubusercontent.com/cuiheng511/filepilot-ai/main/plugins/yaml_extractor.py",
        "extensions": [".yaml", ".yml", ".toml"],
    },
    {
        "name": "epub_extractor",
        "display_name": "EPUB Book Extractor",
        "description": "Extracts text content and metadata from EPUB ebook files",
        "version": "1.0.0",
        "author": "Community",
        "url": "https://raw.githubusercontent.com/cuiheng511/filepilot-ai/main/plugins/epub_extractor.py",
        "extensions": [".epub"],
    },
]


class PluginRegistry:
    """Manages the plugin registry — fetching, caching, and installing plugins."""

    def __init__(self):
        self._entries: list[PluginEntry] = []
        self._loaded = False

    def fetch(self, force: bool = False) -> list[PluginEntry]:
        """Fetch the plugin registry (from cache or network).

        Args:
            force: If True, bypass cache and fetch from network.

        Returns:
            List of available plugins.
        """
        if not force and self._try_load_cache():
            self._mark_installed()
            return self._entries

        # Try network fetch
        try:
            resp = requests.get(REGISTRY_URL, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self._entries = [PluginEntry.from_dict(d) for d in data]
                self._save_cache(data)
                self._mark_installed()
                self._loaded = True
                return self._entries
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.debug("Failed to fetch plugin registry: %s", e)

        # Fallback to built-in registry
        self._entries = [PluginEntry.from_dict(d) for d in _BUILTIN_REGISTRY]
        self._mark_installed()
        self._loaded = True
        return self._entries

    def fetch_async(self, callback=None, force: bool = False) -> Thread:
        """Fetch registry in background thread.

        Args:
            callback: Called with list[PluginEntry] when done.
            force: Bypass cache.

        Returns:
            The background thread.
        """

        def worker():
            entries = self.fetch(force=force)
            if callback:
                callback(entries)

        thread = Thread(target=worker, daemon=True)
        thread.start()
        return thread

    def install_plugin(self, entry: PluginEntry) -> bool:
        """Download and install a plugin from its URL.

        Args:
            entry: The plugin entry to install.

        Returns:
            True if installation succeeded.
        """
        if not entry.url:
            logger.warning("Plugin %s has no download URL", entry.name)
            return False

        try:
            PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
            dest = PLUGINS_DIR / f"{entry.name}.py"

            # Download to temp file first
            resp = requests.get(entry.url, timeout=15)
            resp.raise_for_status()

            # Validate it's Python code (basic check)
            content = resp.text
            if not content.strip():
                logger.warning("Plugin %s: empty content", entry.name)
                return False

            # Write to plugins directory
            dest.write_text(content, encoding="utf-8")
            entry.installed = True
            logger.info("Installed plugin: %s -> %s", entry.name, dest)
            return True

        except (requests.RequestException, OSError) as e:
            logger.warning("Failed to install plugin %s: %s", entry.name, e)
            return False

    def uninstall_plugin(self, entry: PluginEntry) -> bool:
        """Remove an installed plugin.

        Args:
            entry: The plugin entry to uninstall.

        Returns:
            True if removal succeeded.
        """
        dest = PLUGINS_DIR / f"{entry.name}.py"
        if dest.exists():
            try:
                dest.unlink()
                entry.installed = False
                logger.info("Uninstalled plugin: %s", entry.name)
                return True
            except OSError as e:
                logger.warning("Failed to uninstall plugin %s: %s", entry.name, e)
        return False

    def get_installed(self) -> list[PluginEntry]:
        """Return only installed plugins."""
        return [e for e in self._entries if e.installed]

    def get_available(self) -> list[PluginEntry]:
        """Return plugins not yet installed."""
        return [e for e in self._entries if not e.installed]

    @property
    def entries(self) -> list[PluginEntry]:
        """All registry entries."""
        if not self._loaded:
            self.fetch()
        return self._entries

    def _mark_installed(self):
        """Check which plugins are already installed locally."""
        for entry in self._entries:
            plugin_file = PLUGINS_DIR / f"{entry.name}.py"
            entry.installed = plugin_file.exists()

    def _try_load_cache(self) -> bool:
        """Try to load from cache file."""
        if not REGISTRY_CACHE.exists():
            return False
        try:
            import time

            age_hours = (time.time() - REGISTRY_CACHE.stat().st_mtime) / 3600
            if age_hours > REGISTRY_CACHE_HOURS:
                return False
            data = json.loads(REGISTRY_CACHE.read_text(encoding="utf-8"))
            self._entries = [PluginEntry.from_dict(d) for d in data]
            self._loaded = True
            return True
        except (OSError, json.JSONDecodeError):
            return False

    def _save_cache(self, data: list[dict]) -> None:
        """Save registry data to cache."""
        try:
            REGISTRY_CACHE.parent.mkdir(parents=True, exist_ok=True)
            REGISTRY_CACHE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass
