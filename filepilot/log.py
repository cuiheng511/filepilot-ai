"""FilePilot AI — Logging Configuration"""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """Configure global logging

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path

    Returns:
        root logger

    """
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,
    )

    # Lower log level for third-party libraries
    for name in ("urllib3", "requests", "whoosh", "PIL"):
        logging.getLogger(name).setLevel(logging.WARNING)

    return logging.getLogger("filepilot")


def get_logger(name: str) -> logging.Logger:
    """Get a module logger"""
    return logging.getLogger(f"filepilot.{name}")
