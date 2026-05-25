"""Tests for filepilot.log — logging configuration"""

import logging

from filepilot.log import get_logger, setup_logging


def test_setup_logging_default():
    logger = setup_logging()
    assert logger.name == "filepilot"


def test_setup_logging_debug():
    setup_logging(level="DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_setup_logging_with_file(tmp_path):
    log_file = tmp_path / "test.log"
    logger = setup_logging(level="WARNING", log_file=str(log_file))
    root = logging.getLogger()
    assert root.level == logging.WARNING
    logger.warning("test message")
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "test message" in content


def test_third_party_loggers_suppressed():
    setup_logging()
    for name in ("urllib3", "requests", "whoosh", "PIL"):
        assert logging.getLogger(name).level == logging.WARNING


def test_get_logger():
    logger = get_logger("test_module")
    assert logger.name == "filepilot.test_module"


def test_setup_logging_invalid_level():
    setup_logging(level="INVALID")
    root = logging.getLogger()
    assert root.level == logging.INFO


def test_get_logger_different_names():
    l1 = get_logger("module_a")
    l2 = get_logger("module_b")
    assert l1.name == "filepilot.module_a"
    assert l2.name == "filepilot.module_b"
