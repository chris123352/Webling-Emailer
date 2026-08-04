from __future__ import annotations

import logging

from app.utils.logger import setup_logger


def test_setup_logger_writes_errors_to_rotating_log_file(tmp_path) -> None:
    log_file = tmp_path / "logs" / "automation.log"
    logger = setup_logger({"level": "ERROR", "file": str(log_file)}, name="test_webling_logger")

    logger.error("Ein erwarteter Testfehler")

    assert log_file.exists()
    assert "ERROR" in log_file.read_text(encoding="utf-8")
    assert "Ein erwarteter Testfehler" in log_file.read_text(encoding="utf-8")
    assert logger.level == logging.ERROR
