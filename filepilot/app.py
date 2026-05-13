"""FilePilot AI Application Configuration"""

import json
import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from filepilot.ai.summarizer import Summarizer
from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.file_organizer import FileOrganizer
from filepilot.core.file_scanner import FileScanner
from filepilot.core.indexer import FileIndexer


def create_app() -> QApplication:
    """Create a QApplication instance"""
    app = QApplication(sys.argv)
    app.setApplicationName("FilePilot AI")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("FilePilot")

    # Set global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Global style
    app.setStyle("Fusion")

    return app


def load_settings() -> dict:
    """Load user settings"""
    settings_path = Path.home() / ".filepilot" / "settings.json"
    defaults = {
        "ai_mode": "local",
        "ai_provider": "ollama",
        "ai_model": "qwen2.5:7b",
        "ai_api_base": "http://localhost:11434",
        "ai_api_key": "",
        "index_dir": "~/.filepilot/index",
        "max_file_size_mb": 500,
    }
    if settings_path.exists():
        try:
            user = json.loads(settings_path.read_text(encoding="utf-8"))
            defaults.update(user)
        except Exception:
            pass
    return defaults


def create_services(settings: dict) -> dict:
    """Create service module instances"""
    from filepilot.ai.local_ai import OllamaProvider, LlamaCppProvider
    from filepilot.ai.cloud_ai import OpenAIProvider, AnthropicProvider

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
    cloud_ai = primary_ai if provider in ("openai", "anthropic", "custom") else OpenAIProvider(api_key=api_key)

    # Summarizer
    summarizer = Summarizer(
        local_ai=local_ai,
        cloud_ai=cloud_ai,
        prefer_local=(settings.get("ai_mode", "local") in ("local", "hybrid")),
    )

    return {
        "scanner": FileScanner(),
        "organizer": FileOrganizer(),
        "duplicate_finder": DuplicateFinder(),
        "indexer": FileIndexer(
            index_dir=settings.get("index_dir", "~/.filepilot/index")
        ),
        "local_ai": local_ai,
        "cloud_ai": cloud_ai,
        "summarizer": summarizer,
    }
