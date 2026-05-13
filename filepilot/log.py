"""FilePilot AI — 日志配置"""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """配置全局日志

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 可选的日志文件路径

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

    # 降低第三方库的日志级别
    for name in ("urllib3", "requests", "whoosh", "PIL"):
        logging.getLogger(name).setLevel(logging.WARNING)

    return logging.getLogger("filepilot")


def get_logger(name: str) -> logging.Logger:
    """获取模块日志器"""
    return logging.getLogger(f"filepilot.{name}")
