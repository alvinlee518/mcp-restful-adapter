"""Logging configuration for mcp-restful-adapter."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOGGER_NAME = "mcp_restful_adapter"
LOG_DIR = os.path.join(os.path.expanduser("~"), ".mcp_restful_adapter")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "mcp_requests.log")


def setup_logging() -> logging.Logger:
    """Configure logging based on LOG_LEVEL environment variable.

    Sets up two handlers:
    - RotatingFileHandler: writes to mcp_requests.log (10MB × 5 backups)
    - StreamHandler: writes to stderr

    Returns:
        Configured logger instance.
    """
    log_level = os.environ.get("LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, log_level, logging.WARNING)
    log_format = "%(asctime)s %(levelname)s %(message)s"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # File handler: rotating log file for request/response records
    file_handler = RotatingFileHandler(
        LOG_FILE,
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
