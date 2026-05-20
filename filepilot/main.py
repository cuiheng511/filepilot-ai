#!/usr/bin/env python3
"""FilePilot AI — Intelligent File Manager Entry Point"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from filepilot.log import setup_logging


def main():
    """Main function"""
    # Setup logging
    log_dir = Path.home() / ".filepilot" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(log_file=str(log_dir / "filepilot.log"))

    # Load language settings
    from filepilot.i18n import load_language_from_settings

    load_language_from_settings()

    from filepilot.app import (
        create_app,
        create_service_container,
        create_tray_from_container,
        load_settings,
    )
    from filepilot.ui.main_window import MainWindow

    app = create_app()
    settings = load_settings()
    svc = create_service_container(settings)
    window = MainWindow(services=svc)

    # Setup system tray (must be created after MainWindow)
    tray = create_tray_from_container(window, svc, window._notify)
    window.tray_manager = tray
    tray.show()

    # Center window on screen
    if not settings.get("start_minimized", False):
        window.show()
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            window.move(
                screen_geo.x() + (screen_geo.width() - window.width()) // 2,
                screen_geo.y() + (screen_geo.height() - window.height()) // 2,
            )
    else:
        # Start minimized to tray (window hidden, tray visible)
        window.hide()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
