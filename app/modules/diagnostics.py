"""Read-only diagnostics for a Webling connection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.api.webling import WeblingClient

REQUIRED_FIELDS = {
    "Vorname": ("Vorname",),
    "Nachname": ("Nachname", "Name"),
    "E-Mail": ("E-Mail", "E-Mail-Adresse", "Email", "E-Mail (geschäftlich)", "E-Mail (privat)"),
    "Geburtstag": ("Geburtstag",),
    "Eintritt": ("Eintrittsdatum", "Eintritt"),
}


@dataclass(frozen=True)
class DiagnosticResult:
    """The read-only results from one Webling diagnostic run."""

    member_count: int
    available_fields: tuple[str, ...]
    field_status: dict[str, bool]


def run_diagnostics(client: WeblingClient) -> DiagnosticResult:
    """Check API access and inspect the properties of one available member."""
    client.test_connection()
    members = client.get_members()
    properties = _example_member_properties(members)

    return DiagnosticResult(
        member_count=len(members),
        available_fields=tuple(sorted(str(field) for field in properties)),
        field_status={
            display_name: any(field_name in properties for field_name in accepted_names)
            for display_name, accepted_names in REQUIRED_FIELDS.items()
        },
    )


def format_diagnostic_result(result: DiagnosticResult) -> str:
    """Render a concise, human-readable diagnostic report for the console."""
    field_lines = [
        f"{field_name} {'OK' if is_available else 'FEHLT'}"
        for field_name, is_available in result.field_status.items()
    ]
    available_fields = ", ".join(result.available_fields) or "keine (keine Mitglieder gefunden)"

    return "\n".join(
        [
            "Webling Verbindung: OK",
            "",
            "Mitglieder:",
            str(result.member_count),
            "",
            "Felder:",
            *field_lines,
            "",
            "Verfügbare Felder des Beispielmitglieds:",
            available_fields,
        ]
    )


def _example_member_properties(members: list[dict[str, Any]]) -> Mapping[str, Any]:
    if not members:
        return {}

    properties = members[0].get("properties")
    return properties if isinstance(properties, Mapping) else {}
