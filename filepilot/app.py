"""FilePilot AI Application Configuration"""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from filepilot import __version__
from filepilot.ai.summarizer import Summarizer
from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.file_organizer import FileOrganizer
from filepilot.core.file_scanner import FileScanner
from filepilot.core.file_watcher import FileWatcher
from filepilot.core.indexer import FileIndexer
from filepilot.core.search_cache import (
    cache_results,
    clear_search_cache,
    get_cache_stats,
    get_cached_results,
)
from filepilot.ui.tray import SystemTrayManager


def create_app() -> QApplication:
    """Create a QApplication instance"""
    app = QApplication(sys.argv)
    app.setApplicationName("FilePilot AI")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("FilePilot")

    # Set global font with Windows-friendly emoji fallback for icon labels.
    font = QFont()
    font.setFamilies(["Segoe UI", "Microsoft YaHei UI", "Segoe UI Emoji"])
    font.setPointSize(10)
    app.setFont(font)

    # Global style
    app.setStyle("Fusion")

    return app


def load_settings() -> dict:
    """Load user settings — delegates to config.load() for unified settings."""
    from filepilot.core import config

    return config.load()


def create_services(settings: dict) -> dict:
    """Create service module instances"""
    from filepilot.ai.cloud_ai import AnthropicProvider, OpenAIProvider
    from filepilot.ai.local_ai import LlamaCppProvider, OllamaProvider

    provider = settings.get("ai_provider", "ollama")
    model = settings.get("ai_model", "qwen2.5:7b")
    api_base = settings.get("ai_api_base", "http://localhost:11434")
    api_key = settings.get("ai_api_key", "")

    # Create the appropriate AI engine based on provider
    provider_map = {
        "ollama": lambda: OllamaProvider(model=model, api_base=api_base),
        "llamacpp": lambda: LlamaCppProvider(model=model, api_base=api_base),
        "openai": lambda: OpenAIProvider(api_key=api_key, model=model, api_base=api_base),
        "anthropic": lambda: AnthropicProvider(api_key=api_key, model=model, api_base=api_base),
        "custom": lambda: OpenAIProvider(api_key=api_key, model=model, api_base=api_base),
    }
    primary_ai = provider_map.get(provider, provider_map["ollama"])()

    # Keep both local and cloud AI (backward compatibility + hybrid mode)
    local_ai = primary_ai if provider in ("ollama", "llamacpp") else OllamaProvider()
    cloud_ai = (
        primary_ai
        if provider in ("openai", "anthropic", "custom")
        else OpenAIProvider(api_key=api_key)
    )

    # Summarizer
    summarizer = Summarizer(
        local_ai=local_ai,  # type: ignore[arg-type]
        cloud_ai=cloud_ai,  # type: ignore[arg-type]
        prefer_local=(settings.get("ai_mode", "local") in ("local", "hybrid")),
    )

    return {
        "scanner": FileScanner(),
        "organizer": FileOrganizer(),
        "duplicate_finder": DuplicateFinder(),
        "watcher": FileWatcher(),
        "indexer": FileIndexer(
            index_dir=settings.get("index_dir", "~/.filepilot/index"),
        ),
        "local_ai": local_ai,
        "cloud_ai": cloud_ai,
        "summarizer": summarizer,
        "search_cache_get": get_cached_results,
        "search_cache_set": cache_results,
        "search_cache_clear": clear_search_cache,
        "search_cache_stats": get_cache_stats,
    }


def create_tray(main_window, services: dict) -> SystemTrayManager:
    """Create the system tray manager after main window is ready."""
    services_with_toast = dict(services)
    services_with_toast["toast"] = main_window._notify
    tray = SystemTrayManager(main_window=main_window, services=services_with_toast)
    return tray
