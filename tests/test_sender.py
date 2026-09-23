from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.mail.sender import (
    AdminReportSender,
    MailConfigurationError,
    MailSender,
    MailTestSettings,
    SMTPSettings,
    render_birthday_templates,
)


def _smtp_settings() -> SMTPSettings:
    return SMTPSettings(
        host="smtp.example.org",
        port=587,
        username="mailer",
        password="test-password",
        from_address="mailer@example.org",
        use_tls=False,
    )


def test_test_mode_redirects_all_mail_to_test_recipients() -> None:
    smtp = MagicMock()
    smtp_factory = MagicMock()
    smtp_factory.return_value.__enter__.return_value = smtp
    test_settings = MailTestSettings(True, True, ("test@example.org",))
    sender = MailSender(_smtp_settings(), test_settings, smtp_factory=smtp_factory)

    delivery = sender.send(
        original_recipient="member@example.org",
        subject="Test",
        text_body="Text",
        html_body="<p>HTML</p>",
    )

    assert delivery.original_recipient == "member@example.org"
    assert delivery.actual_recipients == ("test@example.org",)
    smtp.send_message.assert_called_once()
    assert smtp.send_message.call_args.kwargs["to_addrs"] == ["test@example.org"]


def test_sender_rejects_missing_smtp_configuration() -> None:
    with pytest.raises(MailConfigurationError, match="smtp.host"):
        SMTPSettings.from_config(
            {"port": 587, "username_env": "SMTP_USERNAME", "password_env": "SMTP_PASSWORD"},
            environment={"SMTP_USERNAME": "mailer", "SMTP_PASSWORD": "secret"},
        )


def test_birthday_templates_render_text_and_escaped_html() -> None:
    text_body, html_body = render_birthday_templates("Lea", "<Muster>", 36)

    assert "Lea <Muster>" in text_body
    assert "Lea &lt;Muster&gt;" in html_body
    assert "36." in html_body


def test_admin_report_sender_sends_only_to_configured_recipients() -> None:
    smtp = MagicMock()
    smtp_factory = MagicMock()
    smtp_factory.return_value.__enter__.return_value = smtp
    sender = AdminReportSender(_smtp_settings(), ("admin@example.org",), smtp_factory=smtp_factory)

    recipients = sender.send(subject="Wochenbericht", text_body="Text", html_body="<p>HTML</p>")

    assert recipients == ("admin@example.org",)
    assert smtp.send_message.call_args.kwargs["to_addrs"] == ["admin@example.org"]
