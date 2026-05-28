"""Plugin Registry — browse and install community plugins from GitHub.

Provides a simple registry of community-contributed extractor plugins
that can be installed with one click from the Plugin Manager panel.

The registry is a JSON file hosted on GitHub (or bundled locally as fallback).
"""

import hashlib
import json
import logging
import re
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
PLUGIN_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
REQUIRE_REMOTE_PLUGIN_HASH = True


@dataclass
class PluginEntry:
    """A plugin available in the registry."""

    name: str
    display_name: str
    description: str
    version: str
    author: str
    url: str  # Raw URL to the .py file
    sha256: str = ""
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
            sha256=data.get("sha256", ""),
            extensions=data.get("extensions", []),
        )


def is_safe_plugin_name(name: str) -> bool:
    """Return True when a registry plugin name is safe for a local filename."""
    return bool(PLUGIN_NAME_RE.fullmatch(name))


def get_plugin_path(name: str) -> Path:
    """Resolve a plugin filename inside the plugin directory."""
    if not is_safe_plugin_name(name):
        raise ValueError(f"Invalid plugin name: {name!r}")
    plugins_root = PLUGINS_DIR.resolve()
    dest = (PLUGINS_DIR / f"{name}.py").resolve()
    if not dest.is_relative_to(plugins_root):
        raise ValueError(f"Plugin path escapes plugin directory: {name!r}")
    return dest


def verify_plugin_sha256(content: str | bytes, expected_sha256: str) -> bool:
    """Return True when plugin content matches the expected SHA256."""
    if not expected_sha256:
        return True
    raw_content = content if isinstance(content, bytes) else content.encode("utf-8")
    actual = hashlib.sha256(raw_content).hexdigest()
    return actual.lower() == expected_sha256.lower()


def is_hash_pinned(entry: "PluginEntry") -> bool:
    """Return True when a remote registry plugin includes a SHA256 pin."""
    return bool(entry.sha256)


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
            dest = get_plugin_path(entry.name)

            # Download to temp file first
            resp = requests.get(entry.url, timeout=15)
            resp.raise_for_status()

            # Validate it's Python code (basic check)
            raw_content = resp.content
            content = raw_content.decode("utf-8", errors="replace")
            if not content.strip():
                logger.warning("Plugin %s: empty content", entry.name)
                return False
            if REQUIRE_REMOTE_PLUGIN_HASH and not is_hash_pinned(entry):
                logger.warning("Plugin %s: missing required SHA256 pin", entry.name)
                return False
            if not verify_plugin_sha256(raw_content, entry.sha256):
                logger.warning("Plugin %s: SHA256 mismatch", entry.name)
                return False

            # Write to plugins directory
            dest.write_bytes(raw_content)
            entry.installed = True
            logger.info("Installed plugin: %s -> %s", entry.name, dest)
            return True

        except (requests.RequestException, OSError) as e:
            logger.warning("Failed to install plugin %s: %s", entry.name, e)
            return False
        except ValueError as e:
            logger.warning("Rejected plugin %s: %s", entry.name, e)
            return False

    def uninstall_plugin(self, entry: PluginEntry) -> bool:
        """Remove an installed plugin.

        Args:
            entry: The plugin entry to uninstall.

        Returns:
            True if removal succeeded.
        """
        try:
            dest = get_plugin_path(entry.name)
        except ValueError as e:
            logger.warning("Rejected plugin uninstall %s: %s", entry.name, e)
            return False
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
            try:
                plugin_file = get_plugin_path(entry.name)
                entry.installed = plugin_file.exists()
            except ValueError:
                entry.installed = False

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
