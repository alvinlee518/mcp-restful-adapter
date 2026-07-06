"""Logging configuration for mcp-restful-adapter."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOGGER_NAME = "mcp_restful_adapter"


def setup_logging() -> logging.Logger:
    """Configure logging based on LOG_LEVEL environment variable.

    Sets up two handlers:
    - RotatingFileHandler: writes to mcp_requests.log (10MB × 5 backups)
    - StreamHandler: writes to stderr

    Returns:
        Configured logger instance.
    """
    log_dir = os.path.join(os.path.expanduser("~"), ".mcp_restful_adapter")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "mcp_requests.log")

    log_level = os.environ.get("LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, log_level, logging.WARNING)
    log_format = "%(asctime)s %(levelname)s %(message)s"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # Guard against duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # File handler: rotating log file for request/response records
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    # Stderr handler: console output
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(stderr_handler)

    return logger
