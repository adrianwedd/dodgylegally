"""Tests for structured logging configuration."""

import logging

import pytest


def test_setup_logging_returns_logger():
    """setup_logging returns a configured Logger instance."""
    from dodgylegally.logging_config import setup_logging

    logger = setup_logging()
    assert isinstance(logger, logging.Logger)
    assert logger.name == "dodgylegally"


def test_setup_logging_default_level_is_info():
    """Default logging level is INFO."""
    from dodgylegally.logging_config import setup_logging

    logger = setup_logging()
    assert logger.level == logging.INFO


def test_setup_logging_verbose_sets_debug():
    """verbose=True sets level to DEBUG."""
    from dodgylegally.logging_config import setup_logging

    logger = setup_logging(verbose=True)
    assert logger.level == logging.DEBUG


def test_setup_logging_quiet_sets_warning():
    """quiet=True sets level to WARNING."""
    from dodgylegally.logging_config import setup_logging

    logger = setup_logging(quiet=True)
    assert logger.level == logging.WARNING


def test_setup_logging_writes_to_file(tmp_path):
    """log_file parameter creates a file handler."""
    from dodgylegally.logging_config import setup_logging

    log_path = tmp_path / "test.log"
    logger = setup_logging(log_file=str(log_path))
    logger.info("test message")
    # Flush handlers
    for handler in logger.handlers:
        handler.flush()
    content = log_path.read_text()
    assert "test message" in content


def test_log_format_includes_timestamp(tmp_path):
    """Log entries include a timestamp."""
    from dodgylegally.logging_config import setup_logging

    log_path = tmp_path / "test.log"
    logger = setup_logging(log_file=str(log_path))
    logger.info("timestamp check")
    for handler in logger.handlers:
        handler.flush()
    content = log_path.read_text()
    # Timestamp format: YYYY-MM-DD HH:MM:SS
    import re
    assert re.search(r"\d{4}-\d{2}-\d{2}", content)


def test_log_format_includes_level(tmp_path):
    """Log entries include the log level."""
    from dodgylegally.logging_config import setup_logging

    log_path = tmp_path / "test.log"
    logger = setup_logging(log_file=str(log_path))
    logger.warning("level check")
    for handler in logger.handlers:
        handler.flush()
    content = log_path.read_text()
    assert "WARNING" in content


def test_cli_has_log_file_flag():
    """CLI group accepts --log-file flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--log-file", "/dev/null", "search", "--count", "1"])
    assert result.exit_code == 0
