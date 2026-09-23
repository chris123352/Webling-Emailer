"""Read-only collection and rendering of next week's member events."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.api.webling import WeblingClient
from app.modules.birthdays import calculate_age


@dataclass(frozen=True)
class UpcomingEvent:
    """One birthday or membership anniversary in the following week."""

    date: date
    member_id: int | None
    name: str
    years: int


@dataclass(frozen=True)
class WeeklyReport:
    """Structured overview for the next complete calendar week."""

    week_start: date
    week_end: date
    birthdays: tuple[UpcomingEvent, ...]
    anniversaries: tuple[UpcomingEvent, ...]

    @property
    def has_events(self) -> bool:
        """Return whether the upcoming week contains any relevant events."""
        return bool(self.birthdays or self.anniversaries)


def get_next_week_report(client: WeblingClient, reference_date: date | None = None) -> WeeklyReport:
    """Load members through Webling and collect events for the next complete week."""
    return find_next_week_events(client.get_members(), reference_date)


def find_next_week_events(
    members: list[dict[str, Any]], reference_date: date | None = None
) -> WeeklyReport:
    """Collect next week's birthdays and membership anniversaries from member data."""
    week_start, week_end = next_week_range(reference_date or date.today())
    birthdays: list[UpcomingEvent] = []
    anniversaries: list[UpcomingEvent] = []

    for member in members:
        properties = member.get("properties")
        if not isinstance(properties, dict):
            continue

        member_id = member.get("id") if isinstance(member.get("id"), int) else None
        name = _member_name(properties)
        birthday = _parse_date(properties.get("Geburtstag"))
        entry_date = _parse_date(properties.get("Eintrittsdatum") or properties.get("Eintritt"))

        if birthday:
            event_date = _anniversary_in_week(birthday, week_start, week_end)
            if event_date:
                birthdays.append(
                    UpcomingEvent(
                        date=event_date,
                        member_id=member_id,
                        name=name,
                        years=calculate_age(birthday, event_date),
                    )
                )

        if entry_date:
            event_date = _anniversary_in_week(entry_date, week_start, week_end)
            if event_date:
                membership_years = event_date.year - entry_date.year
                if membership_years > 0:
                    anniversaries.append(
                        UpcomingEvent(
                            date=event_date,
                            member_id=member_id,
                            name=name,
                            years=membership_years,
                        )
                    )

    return WeeklyReport(
        week_start=week_start,
        week_end=week_end,
        birthdays=tuple(sorted(birthdays, key=_event_sort_key)),
        anniversaries=tuple(sorted(anniversaries, key=_event_sort_key)),
    )


def next_week_range(reference_date: date) -> tuple[date, date]:
    """Return the Monday-to-Sunday interval following the current calendar week."""
    days_until_next_monday = 7 - reference_date.weekday()
    week_start = reference_date + timedelta(days=days_until_next_monday)
    return week_start, week_start + timedelta(days=6)


def render_weekly_report(report: WeeklyReport) -> tuple[str, str]:
    """Render the admin summary as plain text and safe HTML."""
    period = f"{report.week_start:%d.%m.%Y} bis {report.week_end:%d.%m.%Y}"
    intro = f"Hier sind die wichtigen Informationen für die kommende Woche ({period})."

    if not report.has_events:
        text = f"{intro}\n\nIn der kommenden Woche fallen keine Geburtstage und Jubiläen an."
        html_body = (
            "<p>"
            f"{html.escape(intro)}"
            "</p><p>In der kommenden Woche fallen keine Geburtstage und Jubiläen an.</p>"
        )
        return text, html_body

    text_sections = [intro, _text_section("Geburtstage", report.birthdays, "wird", "Jahre")]
    text_sections.append(
        _text_section("Jubiläen", report.anniversaries, "feiert", "Jahre Mitglied")
    )
    html_sections = [f"<p>{html.escape(intro)}</p>"]
    html_sections.append(_html_section("Geburtstage", report.birthdays, "wird", "Jahre"))
    html_sections.append(
        _html_section("Jubiläen", report.anniversaries, "feiert", "Jahre Mitglied")
    )
    return "\n\n".join(text_sections), "\n".join(html_sections)


def _text_section(
    heading: str, events: tuple[UpcomingEvent, ...], verb: str, unit: str
) -> str:
    if not events:
        return f"{heading}:\n- Keine"
    lines = [
        f"- {event.date:%d.%m.%Y}: {event.name} {verb} {event.years} {unit}"
        for event in events
    ]
    return "\n".join([f"{heading}:", *lines])


def _html_section(
    heading: str, events: tuple[UpcomingEvent, ...], verb: str, unit: str
) -> str:
    if not events:
        return f"<h2>{html.escape(heading)}</h2><p>Keine</p>"
    items = "".join(
        "<li>"
        f"{event.date:%d.%m.%Y}: {html.escape(event.name)} {html.escape(verb)} "
        f"{event.years} {html.escape(unit)}"
        "</li>"
        for event in events
    )
    return f"<h2>{html.escape(heading)}</h2><ul>{items}</ul>"


def _anniversary_in_week(original_date: date, week_start: date, week_end: date) -> date | None:
    candidates = []
    for year in {week_start.year, week_end.year}:
        candidate = _anniversary_in_year(original_date, year)
        if week_start <= candidate <= week_end:
            candidates.append(candidate)
    return min(candidates) if candidates else None


def _anniversary_in_year(original_date: date, year: int) -> date:
    if original_date.month == 2 and original_date.day == 29 and not _is_leap_year(year):
        return date(year, 2, 28)
    return original_date.replace(year=year)


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _member_name(properties: dict[str, Any]) -> str:
    first_name = str(properties.get("Vorname") or "")
    last_name = str(properties.get("Name") or properties.get("Nachname") or "")
    return " ".join(part for part in (first_name, last_name) if part) or "Unbekannt"


def _event_sort_key(event: UpcomingEvent) -> tuple[date, str]:
    return event.date, event.name.casefold()


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
