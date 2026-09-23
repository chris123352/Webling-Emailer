from __future__ import annotations

import pytest

from app.utils.config import ConfigurationError, load_config, validate_for_mode


def test_load_config_expands_environment_variables_and_overrides_values(tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
webling:
  url: "https://verein.webling.ch"
  api_key_env: "WEBLING_API_KEY"
smtp:
  host: "mail.example.org"
  port: 587
  username: "mailer"
  password: "secret"
admin:
  email: "admin@example.org"
""",
        encoding="utf-8",
    )

    config = load_config(
        config_file,
        environment={"SMTP_HOST": "smtp.example.org"},
    )

    assert config["webling"]["api_key_env"] == "WEBLING_API_KEY"
    assert config["smtp"]["host"] == "smtp.example.org"


def test_diagnostic_validation_allows_missing_smtp_configuration(tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
webling:
  url: "https://verein.webling.ch"
  api_key_env: "WEBLING_API_KEY"
""",
        encoding="utf-8",
    )

    config = load_config(config_file, environment={"WEBLING_API_KEY": "test-key"})

    validate_for_mode(config, "diagnostic", environment={"WEBLING_API_KEY": "test-key"})


def test_production_validation_reports_missing_smtp_configuration(tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
webling:
  url: "https://verein.webling.ch"
  api_key_env: "WEBLING_API_KEY"
""",
        encoding="utf-8",
    )
    config = load_config(config_file, environment={"WEBLING_API_KEY": "test-key"})

    with pytest.raises(ConfigurationError, match="smtp.host"):
        validate_for_mode(config, "production", environment={"WEBLING_API_KEY": "test-key"})


def test_birthday_test_validation_allows_missing_smtp_configuration(tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
webling:
  url: "https://verein.webling.ch"
  api_key_env: "WEBLING_API_KEY"
""",
        encoding="utf-8",
    )
    config = load_config(config_file, environment={"WEBLING_API_KEY": "test-key"})

    validate_for_mode(config, "birthday-test", environment={"WEBLING_API_KEY": "test-key"})


def test_weekly_report_validation_accepts_smtp_environment_variables(tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
webling:
  url: "https://verein.webling.ch"
  api_key_env: "WEBLING_API_KEY"
smtp:
  host: "smtp.example.org"
  port: 587
  username_env: "SMTP_USERNAME"
  password_env: "SMTP_PASSWORD"
weekly_report:
  enabled: true
  recipients:
    - "admin@example.org"
""",
        encoding="utf-8",
    )
    environment = {
        "WEBLING_API_KEY": "test-key",
        "SMTP_USERNAME": "mailer",
        "SMTP_PASSWORD": "secret",
    }
    config = load_config(config_file, environment=environment)

    validate_for_mode(config, "weekly-report", environment=environment)
