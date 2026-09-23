"""Read-only birthday detection for Webling members."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.api.webling import WeblingClient


@dataclass(frozen=True)
class BirthdayMember:
    """A member whose birthday falls on the selected day."""

    member_id: int | None
    first_name: str
    last_name: str
    birthday: date
    age: int
    email: str | None

    @property
    def display_name(self) -> str:
        """Return a readable member name without exposing the full API record."""
        return " ".join(part for part in (self.first_name, self.last_name) if part) or "Unbekannt"


@dataclass(frozen=True)
class BirthdayPreview:
    """Structured result for a read-only birthday test run."""

    date: date
    birthdays: tuple[BirthdayMember, ...]


def get_todays_birthdays(client: WeblingClient, today: date | None = None) -> BirthdayPreview:
    """Load members through Webling and return only birthdays matching the selected day."""
    selected_date = today or date.today()
    return find_birthdays_today(client.get_members(), selected_date)


def find_birthdays_today(
    members: list[dict[str, Any]], today: date | None = None
) -> BirthdayPreview:
    """Identify today's birthdays in already loaded Webling member records."""
    selected_date = today or date.today()
    birthdays = []

    for member in members:
        properties = member.get("properties")
        if not isinstance(properties, dict):
            continue

        birthday = _parse_birthday(properties.get("Geburtstag"))
        if birthday is None or not is_birthday_on(birthday, selected_date):
            continue

        birthdays.append(
            BirthdayMember(
                member_id=member.get("id") if isinstance(member.get("id"), int) else None,
                first_name=str(properties.get("Vorname") or ""),
                last_name=str(properties.get("Name") or properties.get("Nachname") or ""),
                birthday=birthday,
                age=calculate_age(birthday, selected_date),
                email=_member_email(properties),
            )
        )

    return BirthdayPreview(date=selected_date, birthdays=tuple(birthdays))


def is_birthday_on(birthday: date, selected_date: date) -> bool:
    """Return whether a birthday occurs on a date, including 29 February handling."""
    anniversary = _anniversary_in_year(birthday, selected_date.year)
    return (anniversary.month, anniversary.day) == (selected_date.month, selected_date.day)


def calculate_age(birthday: date, selected_date: date) -> int:
    """Calculate the age after the birthday anniversary in the selected year."""
    anniversary = _anniversary_in_year(birthday, selected_date.year)
    return selected_date.year - birthday.year - (selected_date < anniversary)


def format_birthday_preview(preview: BirthdayPreview) -> str:
    """Render a compact, non-sending birthday preview for the console."""
    heading = f"Geburtstagsvorschau für {preview.date:%d.%m.%Y}"
    if not preview.birthdays:
        return f"{heading}\n\nKeine Geburtstage heute."

    entries = [f"- {member.display_name} ({member.age} Jahre)" for member in preview.birthdays]
    return "\n".join([heading, "", *entries])


def _parse_birthday(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _anniversary_in_year(birthday: date, year: int) -> date:
    if birthday.month == 2 and birthday.day == 29 and not _is_leap_year(year):
        return date(year, 2, 28)
    return birthday.replace(year=year)


def _member_email(properties: dict[str, Any]) -> str | None:
    for field_name in ("E-Mail", "E-Mail (geschäftlich)", "E-Mail (privat)"):
        value = properties.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
