"""Loading, environment expansion and validation for the application configuration."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ENV_PATTERN = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-(?P<default>[^}]*))?\}")
WEBLING_REQUIRED_VALUES = (
    ("webling", "url"),
    ("webling", "api_key_env"),
)
PRODUCTION_REQUIRED_VALUES = (
    ("smtp", "host"),
    ("smtp", "port"),
    ("smtp", "username_env"),
    ("smtp", "password_env"),
    ("admin", "email"),
)
TEST_SEND_REQUIRED_VALUES = (
    ("smtp", "host"),
    ("smtp", "port"),
    ("smtp", "username_env"),
    ("smtp", "password_env"),
    ("test", "enabled"),
    ("test", "redirect_all_mail"),
    ("test", "recipients"),
)
WEEKLY_REPORT_REQUIRED_VALUES = (
    ("smtp", "host"),
    ("smtp", "port"),
    ("smtp", "username_env"),
    ("smtp", "password_env"),
    ("weekly_report", "enabled"),
    ("weekly_report", "recipients"),
)
ENVIRONMENT_OVERRIDES = {
    "SMTP_HOST": ("smtp", "host"),
    "SMTP_PORT": ("smtp", "port"),
    "ADMIN_EMAIL": ("admin", "email"),
}


class ConfigurationError(ValueError):
    """Raised when the configuration file is missing, invalid or incomplete."""


def load_config(
    path: str | Path = "config.yml", environment: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Load YAML configuration and expand environment variables."""
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigurationError(f"Konfigurationsdatei nicht gefunden: {config_path}")

    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        message = f"Ungültige YAML-Konfiguration in {config_path}: {error}"
        raise ConfigurationError(message) from error

    if not isinstance(raw_config, dict):
        raise ConfigurationError(
            "Die Konfiguration muss ein YAML-Objekt auf oberster Ebene enthalten."
        )

    active_environment = dict(os.environ if environment is None else environment)
    config = _expand_environment_values(raw_config, active_environment)
    _apply_environment_overrides(config, active_environment)
    return config


def validate_for_mode(
    config: Mapping[str, Any], mode: str, environment: Mapping[str, str] | None = None
) -> None:
    """Validate only the configuration and secrets required by the selected mode."""
    supported_modes = {
        "diagnostic",
        "birthday-test",
        "birthday-send-test",
        "weekly-report",
        "production",
    }
    if mode not in supported_modes:
        raise ConfigurationError(f"Unbekannter Ausführungsmodus: {mode}")

    required_values = WEBLING_REQUIRED_VALUES
    if mode == "production":
        required_values += PRODUCTION_REQUIRED_VALUES
    if mode == "birthday-send-test":
        required_values += TEST_SEND_REQUIRED_VALUES
    if mode == "weekly-report":
        required_values += WEEKLY_REPORT_REQUIRED_VALUES

    missing = []
    for section, key in required_values:
        section_values = config.get(section)
        value = section_values.get(key) if isinstance(section_values, Mapping) else None
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(f"{section}.{key}")

    active_environment = os.environ if environment is None else environment
    environment_keys = [("webling", "api_key_env")]
    if mode in {"birthday-send-test", "weekly-report", "production"}:
        environment_keys.extend(
            [("smtp", "username_env"), ("smtp", "password_env")]
        )
    for section, key in environment_keys:
        environment_name = _get_value(config, section, key)
        if isinstance(environment_name, str) and environment_name.strip():
            if not active_environment.get(environment_name):
                missing.append(f"Umgebungsvariable {environment_name}")

    if missing:
        formatted_values = ", ".join(missing)
        raise ConfigurationError(f"Fehlende Pflichtwerte in der Konfiguration: {formatted_values}")


def _get_value(config: Mapping[str, Any], section: str, key: str) -> Any:
    section_values = config.get(section)
    return section_values.get(key) if isinstance(section_values, Mapping) else None


def _expand_environment_values(value: Any, environment: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _expand_environment_values(item, environment) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_environment_values(item, environment) for item in value]
    if not isinstance(value, str):
        return value

    full_match = ENV_PATTERN.fullmatch(value)
    if full_match:
        return _environment_value(full_match, environment)

    return ENV_PATTERN.sub(
        lambda match: str(_environment_value(match, environment) or ""),
        value,
    )


def _environment_value(match: re.Match[str], environment: Mapping[str, str]) -> str | None:
    name = match.group("name")
    return environment.get(name, match.group("default"))


def _apply_environment_overrides(config: dict[str, Any], environment: Mapping[str, str]) -> None:
    for environment_name, (section, key) in ENVIRONMENT_OVERRIDES.items():
        value = environment.get(environment_name)
        if value is not None:
            config.setdefault(section, {})[key] = value
