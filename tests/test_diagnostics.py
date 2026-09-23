from __future__ import annotations

from unittest.mock import Mock

from app.modules.diagnostics import format_diagnostic_result, run_diagnostics


def test_diagnostics_reports_connection_member_count_and_required_fields() -> None:
    client = Mock()
    client.get_members.return_value = [
        {
            "id": 12,
            "properties": {
                "Vorname": "Lea",
                "Name": "Muster",
                "E-Mail": "lea@example.org",
                "Geburtstag": "1990-01-15",
                "Eintrittsdatum": "2020-02-01",
            },
        },
        {"id": 13, "properties": {}},
    ]

    result = run_diagnostics(client)

    client.test_connection.assert_called_once_with()
    client.get_members.assert_called_once_with()
    assert result.member_count == 2
    assert result.field_status == {
        "Vorname": True,
        "Nachname": True,
        "E-Mail": True,
        "Geburtstag": True,
        "Eintritt": True,
    }
    assert result.available_fields == (
        "E-Mail",
        "Eintrittsdatum",
        "Geburtstag",
        "Name",
        "Vorname",
    )


def test_diagnostics_marks_missing_fields_and_renders_report() -> None:
    client = Mock()
    client.get_members.return_value = [
        {"id": 12, "properties": {"Vorname": "Lea", "E-Mail (geschäftlich)": "lea@example.org"}}
    ]

    result = run_diagnostics(client)
    report = format_diagnostic_result(result)

    assert "Webling Verbindung: OK" in report
    assert "Mitglieder:\n1" in report
    assert "Vorname OK" in report
    assert "Nachname FEHLT" in report
    assert "E-Mail OK" in report
    assert "Verfügbare Felder des Beispielmitglieds:" in report
