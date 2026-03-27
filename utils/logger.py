"""Logging configuration for InstaRec."""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.environ.get("APPDATA", ""), "InstaRec")
LOG_FILE = os.path.join(LOG_DIR, "instarec.log")


def setup_logging(level: int = logging.INFO):
    """Configure logging with file rotation and console output."""
    os.makedirs(LOG_DIR, exist_ok=True)

    root_logger = logging.getLogger("instarec")
    root_logger.setLevel(level)

    # Avoid adding handlers multiple times
    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation (5MB, keep 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
