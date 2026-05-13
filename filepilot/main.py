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

    from filepilot.app import create_app, create_services, load_settings
    from filepilot.ui.main_window import MainWindow

    app = create_app()
    settings = load_settings()
    services = create_services(settings)
    window = MainWindow(services=services)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
