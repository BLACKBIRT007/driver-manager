"""
logger.py - Centralised logging for Driver Update Manager
Writes to a rotating log file and optionally to the console.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_FILE


def setup_logger(name: str = "DriverManager", level: int = logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger          # already set up (e.g. imported twice)

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(module)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file: max 2 MB, keep 3 backups
    fh = RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console output (visible when running from VS Code / terminal)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


log = setup_logger()
