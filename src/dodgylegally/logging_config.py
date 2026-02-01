"""Structured logging configuration for dodgylegally."""

from __future__ import annotations

import logging


_FORMAT = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    verbose: bool = False,
    quiet: bool = False,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure and return the dodgylegally logger.

    verbose: set DEBUG level (all messages)
    quiet: set WARNING level (errors and warnings only)
    log_file: write structured log entries to this path
    """
    logger = logging.getLogger("dodgylegally")

    # Clear existing handlers to avoid duplication on repeated calls
    logger.handlers.clear()

    if verbose:
        logger.setLevel(logging.DEBUG)
    elif quiet:
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
