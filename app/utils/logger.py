"""Central logging configuration for Webling Automation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    logging_config: Mapping[str, Any], name: str = "webling_automation"
) -> logging.Logger:
    """Create a console and rotating-file logger from the configured logging section."""
    level_name = str(logging_config.get("level", "INFO")).upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        raise ValueError(f"Ungültiges Logging-Level: {level_name}")

    log_file = Path(str(logging_config.get("file", "data/logs/webling-automation.log")))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(logging_config.get("max_bytes", 1_048_576)),
        backupCount=int(logging_config.get("backup_count", 5)),
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
