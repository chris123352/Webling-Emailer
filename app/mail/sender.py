"""Safe SMTP email sending for explicit test recipients only."""

from __future__ import annotations

import html
import os
import smtplib
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any

TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"


class MailError(RuntimeError):
    """Base class for mail configuration and delivery errors."""


class MailConfigurationError(MailError):
    """Raised when SMTP or test-recipient configuration is incomplete or unsafe."""


class MailSendError(MailError):
    """Raised when SMTP delivery fails."""


@dataclass(frozen=True)
class SMTPSettings:
    """Resolved SMTP settings with credentials loaded only from the environment."""

    host: str
    port: int
    username: str
    password: str
    from_address: str
    use_tls: bool

    @classmethod
    def from_config(
        cls, smtp_config: Mapping[str, Any], environment: Mapping[str, str] | None = None
    ) -> SMTPSettings:
        """Build SMTP settings without ever accepting a password in the config file."""
        active_environment = os.environ if environment is None else environment
        host = _required_config_value(smtp_config, "host")
        username_env = _required_config_value(smtp_config, "username_env")
        password_env = _required_config_value(smtp_config, "password_env")
        username = _required_environment_value(username_env, active_environment)
        password = _required_environment_value(password_env, active_environment)

        try:
            port = int(_required_config_value(smtp_config, "port"))
        except ValueError as error:
            raise MailConfigurationError("SMTP-Port muss eine Zahl sein.") from error

        from_address = str(smtp_config.get("from_address") or username)
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            from_address=from_address,
            use_tls=bool(smtp_config.get("use_tls", True)),
        )


@dataclass(frozen=True)
class MailTestSettings:
    """Recipients and switches protecting the test-only delivery path."""

    enabled: bool
    redirect_all_mail: bool
    recipients: tuple[str, ...]

    @classmethod
    def from_config(cls, test_config: Mapping[str, Any]) -> MailTestSettings:
        recipients = test_config.get("recipients", [])
        if not isinstance(recipients, list):
            raise MailConfigurationError(
                "test.recipients muss eine Liste von E-Mail-Adressen sein."
            )
        return cls(
            enabled=bool(test_config.get("enabled", False)),
            redirect_all_mail=bool(test_config.get("redirect_all_mail", False)),
            recipients=tuple(str(recipient) for recipient in recipients if str(recipient).strip()),
        )

    def require_safe_redirect(self) -> None:
        """Reject every configuration that could send a message to a real recipient."""
        if not self.enabled or not self.redirect_all_mail or not self.recipients:
            raise MailConfigurationError(
                "birthday-send-test benötigt test.enabled, test.redirect_all_mail "
                "und Testempfänger."
            )


@dataclass(frozen=True)
class MailDelivery:
    """Audit-friendly record of a redirected test delivery."""

    original_recipient: str
    actual_recipients: tuple[str, ...]


class AdminReportSender:
    """SMTP sender for the fixed, configured admin-report recipients."""

    def __init__(
        self,
        settings: SMTPSettings,
        recipients: tuple[str, ...],
        smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        if not recipients:
            raise MailConfigurationError("Keine Empfänger für den Wochenbericht konfiguriert.")
        self._settings = settings
        self._recipients = recipients
        self._smtp_factory = smtp_factory

    def send(self, *, subject: str, text_body: str, html_body: str) -> tuple[str, ...]:
        """Send one admin report only to its preconfigured recipients."""
        _send_message(
            settings=self._settings,
            recipients=self._recipients,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            smtp_factory=self._smtp_factory,
        )
        return self._recipients


class MailSender:
    """SMTP sender that only sends through the explicit test-recipient redirect."""

    def __init__(
        self,
        settings: SMTPSettings,
        test_settings: MailTestSettings,
        smtp_factory: Callable[..., smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        test_settings.require_safe_redirect()
        self._settings = settings
        self._test_settings = test_settings
        self._smtp_factory = smtp_factory

    def send(
        self, *, original_recipient: str, subject: str, text_body: str, html_body: str
    ) -> MailDelivery:
        """Send a multipart message solely to configured test recipients."""
        _send_message(
            settings=self._settings,
            recipients=self._test_settings.recipients,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            smtp_factory=self._smtp_factory,
        )

        return MailDelivery(
            original_recipient=original_recipient,
            actual_recipients=self._test_settings.recipients,
        )


def _send_message(
    *,
    settings: SMTPSettings,
    recipients: tuple[str, ...],
    subject: str,
    text_body: str,
    html_body: str,
    smtp_factory: Callable[..., smtplib.SMTP],
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.from_address
    message["To"] = ", ".join(recipients)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        with smtp_factory(settings.host, settings.port, timeout=15) as smtp:
            if settings.use_tls:
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(settings.username, settings.password)
            smtp.send_message(
                message,
                from_addr=settings.from_address,
                to_addrs=list(recipients),
            )
    except (OSError, smtplib.SMTPException) as error:
        raise MailSendError("SMTP-Versand ist fehlgeschlagen.") from error


def render_birthday_templates(first_name: str, last_name: str, age: int) -> tuple[str, str]:
    """Render plain-text and HTML birthday templates from the packaged template files."""
    text_context = {"first_name": first_name, "last_name": last_name, "age": str(age)}
    html_context = {
        key: html.escape(value) for key, value in text_context.items()
    }
    text_body = _read_template("birthday.txt").format(**text_context)
    html_body = _read_template("birthday.html").format(**html_context)
    return text_body, html_body


def _read_template(filename: str) -> str:
    try:
        return (TEMPLATE_DIRECTORY / filename).read_text(encoding="utf-8")
    except OSError as error:
        message = f"E-Mail-Template fehlt oder ist nicht lesbar: {filename}"
        raise MailConfigurationError(message) from error


def _required_config_value(config: Mapping[str, Any], key: str) -> str:
    value = config.get(key)
    if value is None or not str(value).strip():
        raise MailConfigurationError(f"Fehlende SMTP-Konfiguration: smtp.{key}")
    return str(value)


def _required_environment_value(name: str, environment: Mapping[str, str]) -> str:
    value = environment.get(name)
    if not value:
        raise MailConfigurationError(f"Fehlende SMTP-Umgebungsvariable: {name}")
    return value
