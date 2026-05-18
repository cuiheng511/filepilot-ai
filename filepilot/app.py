"""FilePilot AI Application Configuration"""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from filepilot import __version__
from filepilot.core.service_container import ServiceContainer
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
    """Create service module instances (legacy — returns raw dict)."""
    svc = create_service_container(settings)
    return vars(svc)


def create_service_container(settings: dict) -> ServiceContainer:
    """Create a typed ServiceContainer from settings."""
    return ServiceContainer.from_settings(settings)


def create_tray(main_window, services: dict) -> SystemTrayManager:
    """Create the system tray manager after main window is ready."""
    services_with_toast = dict(services)
    services_with_toast["toast"] = main_window._notify
    tray = SystemTrayManager(main_window=main_window, services=services_with_toast)
    return tray


def create_tray_from_container(main_window, svc: ServiceContainer, notify_fn) -> SystemTrayManager:
    """Create tray from typed ServiceContainer."""
    extra = {
        "toast": notify_fn,
        "scanner": svc.scanner,
        "search_cache_get": svc.search_cache_get,
        "search_cache_set": svc.search_cache_set,
        "search_cache_clear": svc.search_cache_clear,
        "search_cache_stats": svc.search_cache_stats,
    }
    return SystemTrayManager(main_window=main_window, services=extra)
