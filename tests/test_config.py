from __future__ import annotations

import pytest

from app.utils.config import ConfigurationError, load_config


def test_load_config_expands_environment_variables_and_overrides_values(tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text(
        """
webling:
  api_key: "${WEBLING_API_KEY}"
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
        environment={"WEBLING_API_KEY": "api-from-environment", "SMTP_HOST": "smtp.example.org"},
    )

    assert config["webling"]["api_key"] == "api-from-environment"
    assert config["smtp"]["host"] == "smtp.example.org"


def test_load_config_reports_missing_required_values(tmp_path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text("webling:\n  api_key: ''\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="smtp.host"):
        load_config(config_file, environment={})
