"""Application entry point for the Webling Automation foundation."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from app.utils.config import ConfigurationError, load_config
from app.utils.logger import setup_logger


def main() -> int:
    """Load configuration, initialize logging and report the current system status."""
    config_path = Path(os.getenv("WEBLING_CONFIG_FILE", "config.yml"))

    try:
        config = load_config(config_path)
    except ConfigurationError as error:
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s | %(message)s")
        logging.getLogger("webling_automation").error(
            "Systemstatus: Konfiguration fehlerhaft: %s", error
        )
        return 1

    logger = setup_logger(config.get("logging", {}))
    enabled_modules = [name for name, enabled in config.get("module", {}).items() if enabled]

    logger.info("Webling Automation wurde gestartet.")
    logger.info("Systemstatus: Konfiguration geladen aus %s", config_path)
    logger.info("Systemstatus: Testmodus ist %s", "aktiv" if config.get("testmodus") else "inaktiv")
    logger.info(
        "Systemstatus: Aktive Module: %s",
        ", ".join(enabled_modules) if enabled_modules else "keine",
    )
    logger.info("Systemstatus: Grundsystem bereit; Webling-API ist noch nicht aktiviert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
