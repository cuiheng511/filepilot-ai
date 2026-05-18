"""Plugin system — base extractor interface and plugin discovery."""

import importlib.util
import inspect
import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger("filepilot.plugin_system")

PLUGINS_DIR = Path.home() / ".filepilot" / "plugins"


class BaseFileExtractor(ABC):
    """Abstract base class for file content extractor plugins.

    Subclasses must implement `supports()` and `extract_text()`.
    Optionally implement `extract_metadata()`.
    """

    @abstractmethod
    def supports(self, extension: str) -> bool:
        """Return True if this extractor can handle the given file extension."""

    @abstractmethod
    def extract_text(self, file_path: Path) -> str | None:
        """Extract text content from the file. Return None on failure."""

    def extract_metadata(self, file_path: Path) -> dict:
        """Extract metadata from the file. Return empty dict by default."""
        return {}

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def display_name(self) -> str:
        return getattr(self.__class__, "display_name", self.name)

    @property
    def version(self) -> str:
        return getattr(self.__class__, "version", "0.1.0")

    @property
    def description(self) -> str:
        return getattr(self.__class__, "description", "")


class PluginManager:
    """Discovers, loads, and manages extractor plugins."""

    def __init__(self, plugins_dir: str | Path | None = None):
        self._plugins_dir = Path(plugins_dir) if plugins_dir else PLUGINS_DIR
        self._extractors: list[BaseFileExtractor] = []
        self._loaded = False

    @property
    def plugins_dir(self) -> Path:
        return self._plugins_dir

    def discover(self) -> list[BaseFileExtractor]:
        """Scan the plugins directory and load all extractor plugins."""
        self._extractors.clear()
        self._loaded = True

        if not self._plugins_dir.exists():
            logger.debug("Plugins directory does not exist: %s", self._plugins_dir)
            return self._extractors

        for entry in sorted(self._plugins_dir.iterdir()):
            if entry.suffix == ".py" and not entry.name.startswith("_"):
                try:
                    extractors = self._load_plugin_from_file(entry)
                    self._extractors.extend(extractors)
                except Exception as e:
                    logger.warning("Failed to load plugin %s: %s", entry.name, e)

            elif entry.is_dir() and not entry.name.startswith("_"):
                init_file = entry / "__init__.py"
                if init_file.exists():
                    try:
                        extractors = self._load_plugin_from_package(entry)
                        self._extractors.extend(extractors)
                    except Exception as e:
                        logger.warning("Failed to load plugin package %s: %s", entry.name, e)

        logger.info("Discovered %d extractor plugins", len(self._extractors))
        return self._extractors

    def _load_plugin_from_file(self, file_path: Path) -> list[BaseFileExtractor]:
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if spec is None or spec.loader is None:
            return []
        module = importlib.util.module_from_spec(spec)
        sys.modules[file_path.stem] = module
        spec.loader.exec_module(module)
        return self._collect_extractors(module)

    def _load_plugin_from_package(self, package_path: Path) -> list[BaseFileExtractor]:
        spec = importlib.util.spec_from_file_location(
            package_path.name, package_path / "__init__.py"
        )
        if spec is None or spec.loader is None:
            return []
        module = importlib.util.module_from_spec(spec)
        sys.modules[package_path.name] = module
        spec.loader.exec_module(module)
        return self._collect_extractors(module)

    @staticmethod
    def _collect_extractors(module) -> list[BaseFileExtractor]:
        extractors = []
        for _, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseFileExtractor)
                and obj is not BaseFileExtractor
            ):
                try:
                    extractors.append(obj())
                except Exception as e:
                    logger.warning("Failed to instantiate extractor %s: %s", obj.__name__, e)
        return extractors

    def get_extractor_for(self, extension: str) -> BaseFileExtractor | None:
        """Find the first extractor that supports the given extension."""
        if not self._loaded:
            self.discover()
        ext = extension.lower()
        for extractor in self._extractors:
            if extractor.supports(ext):
                return extractor
        return None

    def get_all_extractors(self) -> list[BaseFileExtractor]:
        if not self._loaded:
            self.discover()
        return list(self._extractors)

    def get_supported_extensions(self) -> set[str]:
        if not self._loaded:
            self.discover()
        exts = set()
        for extractor in self._extractors:
            for ext in getattr(extractor, "extensions", []):
                exts.add(ext.lower())
        return exts

    def reload(self) -> list[BaseFileExtractor]:
        self._loaded = False
        return self.discover()

    @staticmethod
    def install_sample_plugin() -> Path:
        """Install a sample plugin to the plugins directory for demonstration."""
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        sample_file = PLUGINS_DIR / "sample_md_extractor.py"
        if not sample_file.exists():
            sample_file.write_text(
                '''"""Sample extractor plugin — extracts text from Markdown files."""
from pathlib import Path
from filepilot.core.plugin_system import BaseFileExtractor


class SampleMarkdownExtractor(BaseFileExtractor):
    display_name = "Sample Markdown Extractor"
    description = "Extracts text content from .md files"
    version = "1.0.0"
    extensions = [".md", ".markdown"]

    def supports(self, extension: str) -> bool:
        return extension.lower() in self.extensions

    def extract_text(self, file_path: Path) -> str | None:
        if not file_path.exists():
            return None
        return file_path.read_text(encoding="utf-8", errors="replace")

    def extract_metadata(self, file_path: Path) -> dict:
        return {"line_count": len(file_path.read_text().splitlines())}
''',
                encoding="utf-8",
            )
        return sample_file


# Shared plugin manager for use across the application
_shared_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """Get or create the shared PluginManager instance."""
    global _shared_plugin_manager
    if _shared_plugin_manager is None:
        _shared_plugin_manager = PluginManager()
        _shared_plugin_manager.discover()
    return _shared_plugin_manager


def reload_plugins() -> list[BaseFileExtractor]:
    """Reload all plugins and return discovered extractors."""
    pm = get_plugin_manager()
    return pm.reload()
