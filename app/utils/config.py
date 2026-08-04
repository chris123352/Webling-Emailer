"""Loading, environment expansion and validation for the application configuration."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ENV_PATTERN = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::-(?P<default>[^}]*))?\}")
REQUIRED_VALUES = (
    ("webling", "api_key"),
    ("smtp", "host"),
    ("smtp", "port"),
    ("smtp", "username"),
    ("smtp", "password"),
    ("admin", "email"),
)
ENVIRONMENT_OVERRIDES = {
    "WEBLING_API_KEY": ("webling", "api_key"),
    "SMTP_HOST": ("smtp", "host"),
    "SMTP_PORT": ("smtp", "port"),
    "SMTP_USERNAME": ("smtp", "username"),
    "SMTP_PASSWORD": ("smtp", "password"),
    "ADMIN_EMAIL": ("admin", "email"),
}


class ConfigurationError(ValueError):
    """Raised when the configuration file is missing, invalid or incomplete."""


def load_config(
    path: str | Path = "config.yml", environment: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Load YAML configuration, expand environment variables and validate required values."""
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
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    """Raise a descriptive error when required nested configuration values are empty."""
    missing = []
    for section, key in REQUIRED_VALUES:
        section_values = config.get(section)
        value = section_values.get(key) if isinstance(section_values, Mapping) else None
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(f"{section}.{key}")

    if missing:
        formatted_values = ", ".join(missing)
        raise ConfigurationError(f"Fehlende Pflichtwerte in der Konfiguration: {formatted_values}")


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
