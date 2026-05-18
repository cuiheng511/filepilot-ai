"""Type-safe service locator for FilePilot AI

Eliminates the ad-hoc services dict pattern.
All services are optional — None means the service is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from filepilot.ai.summarizer import Summarizer
from filepilot.core.duplicate_finder import DuplicateFinder
from filepilot.core.file_organizer import FileOrganizer
from filepilot.core.file_scanner import FileScanner
from filepilot.core.file_watcher import FileWatcher
from filepilot.core.indexer import FileIndexer


@dataclass
class ServiceContainer:
    """Typed container for all application services.

    Every field is optional (default None). Panels that need a service
    should check for None and degrade gracefully.
    """

    scanner: FileScanner | None = None
    indexer: FileIndexer | None = None
    organizer: FileOrganizer | None = None
    duplicate_finder: DuplicateFinder | None = None
    summarizer: Summarizer | None = None
    local_ai: Any | None = None
    cloud_ai: Any | None = None
    watcher: FileWatcher | None = None
    tray: Any | None = None

    _search_cache_get: Any = field(default=None, repr=False)
    _search_cache_set: Any = field(default=None, repr=False)
    _search_cache_clear: Any = field(default=None, repr=False)
    _search_cache_stats: Any = field(default=None, repr=False)

    @classmethod
    def from_settings(cls, settings: dict) -> ServiceContainer:
        """Create services from a settings dict (backward compat)."""
        from filepilot.ai.cloud_ai import AnthropicProvider, OpenAIProvider
        from filepilot.ai.local_ai import LlamaCppProvider, OllamaProvider

        provider = settings.get("ai_provider", "ollama")
        model = settings.get("ai_model", "qwen2.5:7b")
        api_base = settings.get("ai_api_base", "http://localhost:11434")
        api_key = settings.get("ai_api_key", "")

        provider_map: dict[str, Any] = {
            "ollama": lambda: OllamaProvider(model=model, api_base=api_base),
            "llamacpp": lambda: LlamaCppProvider(model=model, api_base=api_base),
            "openai": lambda: OpenAIProvider(api_key=api_key, model=model, api_base=api_base),
            "anthropic": lambda: AnthropicProvider(api_key=api_key, model=model, api_base=api_base),
            "custom": lambda: OpenAIProvider(api_key=api_key, model=model, api_base=api_base),
        }
        primary_ai = provider_map.get(provider, provider_map["ollama"])()

        local_ai = primary_ai if provider in ("ollama", "llamacpp") else OllamaProvider()
        cloud_ai = (
            primary_ai
            if provider in ("openai", "anthropic", "custom")
            else OpenAIProvider(api_key=api_key)
        )

        summarizer = Summarizer(
            local_ai=local_ai,
            cloud_ai=cloud_ai,
            prefer_local=(settings.get("ai_mode", "local") in ("local", "hybrid")),
        )

        from filepilot.core.search_cache import (
            cache_results,
            clear_search_cache,
            get_cache_stats,
            get_cached_results,
        )

        return cls(
            scanner=FileScanner(),
            organizer=FileOrganizer(),
            duplicate_finder=DuplicateFinder(),
            watcher=FileWatcher(),
            indexer=FileIndexer(
                index_dir=settings.get("index_dir", "~/.filepilot/index"),
            ),
            local_ai=local_ai,
            cloud_ai=cloud_ai,
            summarizer=summarizer,
            _search_cache_get=get_cached_results,
            _search_cache_set=cache_results,
            _search_cache_clear=clear_search_cache,
            _search_cache_stats=get_cache_stats,
        )

    def get_scanner(self) -> FileScanner:
        """Return scanner, creating a default if needed."""
        if self.scanner is None:
            self.scanner = FileScanner()
        return self.scanner

    def get_indexer(self) -> FileIndexer:
        if self.indexer is None:
            self.indexer = FileIndexer()
        return self.indexer

    def get_organizer(self) -> FileOrganizer:
        if self.organizer is None:
            self.organizer = FileOrganizer()
        return self.organizer

    def get_duplicate_finder(self) -> DuplicateFinder:
        if self.duplicate_finder is None:
            self.duplicate_finder = DuplicateFinder()
        return self.duplicate_finder

    def get_watcher(self) -> FileWatcher:
        if self.watcher is None:
            self.watcher = FileWatcher()
        return self.watcher

    def search_cache_get(self, key: str) -> Any:
        if self._search_cache_get:
            return self._search_cache_get(key)
        return None

    def search_cache_set(self, key: str, results: Any) -> None:
        if self._search_cache_set:
            self._search_cache_set(key, results)

    def search_cache_clear(self) -> None:
        if self._search_cache_clear:
            self._search_cache_clear()

    def search_cache_stats(self) -> dict:
        if self._search_cache_stats:
            return dict(self._search_cache_stats() or {})
        return {}
