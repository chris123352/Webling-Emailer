"""Application entry point for the Webling Automation foundation."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from app.api.webling import WeblingClient, WeblingError
from app.mail.sender import (
    AdminReportSender,
    MailConfigurationError,
    MailError,
    MailSender,
    MailTestSettings,
    SMTPSettings,
    render_birthday_templates,
)
from app.modules.birthdays import format_birthday_preview, get_todays_birthdays
from app.modules.diagnostics import format_diagnostic_result, run_diagnostics
from app.modules.weekly_report import get_next_week_report, render_weekly_report
from app.utils.config import ConfigurationError, load_config, validate_for_mode
from app.utils.logger import setup_logger


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse the currently supported, safe application modes."""
    parser = argparse.ArgumentParser(description="Webling Automation")
    parser.add_argument(
        "mode",
        nargs="?",
        default="diagnostic",
        choices=(
            "diagnostic",
            "birthday-test",
            "birthday-send-test",
            "weekly-report",
            "production",
        ),
        help="weekly-report sendet eine feste Wochenübersicht nur an die konfigurierten Admins",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Load configuration, initialize logging and report the current system status."""
    arguments = parse_args(args)
    config_path = Path(os.getenv("WEBLING_CONFIG_FILE", "config.yml"))

    try:
        config = load_config(config_path)
        validate_for_mode(config, arguments.mode)
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
    test_config = config.get("test", {})
    test_mode_status = "aktiv" if test_config.get("enabled") else "inaktiv"
    logger.info("Systemstatus: Testmodus ist %s", test_mode_status)
    logger.info(
        "Systemstatus: Aktive Module: %s",
        ", ".join(enabled_modules) if enabled_modules else "keine",
    )

    if arguments.mode in {"diagnostic", "birthday-test", "birthday-send-test", "weekly-report"}:
        webling_config = config["webling"]
        try:
            client = WeblingClient(
                base_url=webling_config["url"],
                api_key_env=webling_config["api_key_env"],
                timeout_seconds=float(webling_config.get("timeout_seconds", 15)),
            )
            if arguments.mode == "diagnostic":
                diagnostic_result = run_diagnostics(client)
            elif arguments.mode in {"birthday-test", "birthday-send-test"}:
                birthday_preview = get_todays_birthdays(client)
            else:
                weekly_report = get_next_week_report(client)
        except WeblingError as error:
            logger.error("Systemstatus: Webling-Testmodus fehlgeschlagen: %s", error)
            return 1

        if arguments.mode == "diagnostic":
            print(format_diagnostic_result(diagnostic_result))
            logger.info("Systemstatus: Diagnosemodus erfolgreich abgeschlossen.")
        elif arguments.mode == "birthday-test":
            print(format_birthday_preview(birthday_preview))
            logger.info("Systemstatus: Geburtstagsvorschau erfolgreich abgeschlossen.")
        elif arguments.mode == "birthday-send-test":
            try:
                _send_birthday_test_messages(birthday_preview, config, logger)
            except MailError as error:
                logger.error("Systemstatus: Geburtstags-Testversand fehlgeschlagen: %s", error)
                return 1
        else:
            try:
                _send_weekly_report(weekly_report, config, logger)
            except MailError as error:
                logger.error("Systemstatus: Wochenbericht fehlgeschlagen: %s", error)
                return 1
        return 0

    logger.info("Systemstatus: Produktiver Modus ist konfiguriert; keine Automation aktiviert.")
    return 0


def _send_birthday_test_messages(birthday_preview, config, logger: logging.Logger) -> None:
    """Create birthday emails and send them only through the protected test redirect."""
    try:
        smtp_settings = SMTPSettings.from_config(config["smtp"])
        test_settings = MailTestSettings.from_config(config["test"])
        sender = MailSender(smtp_settings, test_settings)
    except MailConfigurationError as error:
        raise MailError(f"Testversand nicht sicher konfiguriert: {error}") from error

    if not birthday_preview.birthdays:
        print(format_birthday_preview(birthday_preview))
        logger.info("Systemstatus: Keine Testmails erforderlich.")
        return

    for birthday in birthday_preview.birthdays:
        if not birthday.email:
            logger.warning(
                "Testmail übersprungen: Kein Originalempfänger für %s.", birthday.display_name
            )
            continue
        text_body, html_body = render_birthday_templates(
            birthday.first_name, birthday.last_name, birthday.age
        )
        delivery = sender.send(
            original_recipient=birthday.email,
            subject=f"Alles Gute zum Geburtstag, {birthday.first_name}!",
            text_body=text_body,
            html_body=html_body,
        )
        logger.info(
            "Testmail versendet. Originalempfänger: %s | Testempfänger: %s",
            delivery.original_recipient,
            ", ".join(delivery.actual_recipients),
        )


def _send_weekly_report(weekly_report, config, logger: logging.Logger) -> None:
    """Send one upcoming-week overview only to the fixed report recipients."""
    weekly_config = config["weekly_report"]
    if not weekly_config.get("enabled"):
        raise MailConfigurationError("weekly_report.enabled ist nicht aktiviert.")
    recipients = weekly_config.get("recipients", [])
    if not isinstance(recipients, list):
        raise MailConfigurationError("weekly_report.recipients muss eine Liste sein.")

    smtp_settings = SMTPSettings.from_config(config["smtp"])
    sender = AdminReportSender(smtp_settings, tuple(str(item) for item in recipients))
    text_body, html_body = render_weekly_report(weekly_report)
    subject = (
        "SSV Schmidhausen: Wichtige Termine für "
        f"{weekly_report.week_start:%d.%m.}–{weekly_report.week_end:%d.%m.%Y}"
    )
    actual_recipients = sender.send(subject=subject, text_body=text_body, html_body=html_body)
    logger.info("Wochenbericht an Admin-Empfänger versendet: %s", ", ".join(actual_recipients))


if __name__ == "__main__":
    raise SystemExit(main())
