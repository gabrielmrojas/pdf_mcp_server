from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ..config import settings


def get_logger(name: str) -> logging.Logger:
    log_path: Path = settings.log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))

    handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    # Do not propagate to root to avoid stdout/stderr pollution
    logger.propagate = False
    return logger
