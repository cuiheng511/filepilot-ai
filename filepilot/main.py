#!/usr/bin/env python3
"""FilePilot AI — Intelligent File Manager Entry Point"""

import sys
from pathlib import Path

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

    from filepilot.app import create_app, create_services, create_tray, load_settings
    from filepilot.ui.main_window import MainWindow

    app = create_app()
    settings = load_settings()
    services = create_services(settings)
    window = MainWindow(services=services)

    # Setup system tray (must be created after MainWindow)
    tray = create_tray(window, services)
    tray.show()

    # Center window on screen
    window.show()
    from PySide6.QtGui import QScreen
    screen = QApplication.primaryScreen()
    if screen:
        screen_geo = screen.availableGeometry()
        window.move(
            screen_geo.x() + (screen_geo.width() - window.width()) // 2,
            screen_geo.y() + (screen_geo.height() - window.height()) // 2
        )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
