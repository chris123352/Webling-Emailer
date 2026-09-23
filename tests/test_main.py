from __future__ import annotations

from unittest.mock import Mock

from app import main as main_module


def test_diagnostic_mode_is_available() -> None:
    assert main_module.parse_args(["diagnostic"]).mode == "diagnostic"


def test_production_mode_is_available() -> None:
    assert main_module.parse_args(["production"]).mode == "production"


def test_birthday_test_mode_is_available() -> None:
    assert main_module.parse_args(["birthday-test"]).mode == "birthday-test"


def test_birthday_send_test_mode_is_available() -> None:
    assert main_module.parse_args(["birthday-send-test"]).mode == "birthday-send-test"


def test_weekly_report_mode_is_available() -> None:
    assert main_module.parse_args(["weekly-report"]).mode == "weekly-report"


def test_diagnostic_mode_starts_without_smtp_configuration(monkeypatch, tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
webling:
  url: "https://verein.webling.ch"
  api_key_env: "WEBLING_API_KEY"
testmodus: true
logging: {}
module: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBLING_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("WEBLING_API_KEY", "test-key")
    monkeypatch.setattr(main_module, "setup_logger", Mock(return_value=Mock()))
    monkeypatch.setattr(main_module, "WeblingClient", Mock(return_value=Mock()))
    monkeypatch.setattr(main_module, "run_diagnostics", Mock(return_value=Mock()))
    monkeypatch.setattr(main_module, "format_diagnostic_result", Mock(return_value="Diagnose"))

    assert main_module.main(["diagnostic"]) == 0
