from __future__ import annotations

from datetime import date

from app.modules.weekly_report import find_next_week_events, next_week_range, render_weekly_report


def _member(member_id: int, **properties: str) -> dict:
    return {"id": member_id, "properties": {"Vorname": "Lea", "Name": "Muster", **properties}}


def test_next_week_starts_on_monday_after_a_sunday() -> None:
    week_start, week_end = next_week_range(date(2026, 9, 20))

    assert week_start == date(2026, 9, 21)
    assert week_end == date(2026, 9, 27)


def test_report_collects_birthdays_and_membership_anniversaries_for_next_week() -> None:
    members = [
        _member(1, Geburtstag="1990-09-22"),
        _member(2, Eintrittsdatum="2016-09-25"),
        _member(3, Geburtstag="1990-09-28", Eintrittsdatum="2019-09-28"),
    ]

    report = find_next_week_events(members, reference_date=date(2026, 9, 20))

    assert [(event.date, event.years) for event in report.birthdays] == [(date(2026, 9, 22), 36)]
    assert [(event.date, event.years) for event in report.anniversaries] == [
        (date(2026, 9, 25), 10)
    ]


def test_report_explicitly_says_when_nothing_is_upcoming() -> None:
    report = find_next_week_events([], reference_date=date(2026, 9, 20))

    text_body, html_body = render_weekly_report(report)

    assert "keine Geburtstage und Jubiläen" in text_body
    assert "keine Geburtstage und Jubiläen" in html_body


def test_report_renders_event_details() -> None:
    report = find_next_week_events(
        [_member(1, Geburtstag="1990-09-22"), _member(2, Eintrittsdatum="2016-09-25")],
        reference_date=date(2026, 9, 20),
    )

    text_body, _ = render_weekly_report(report)

    assert "22.09.2026: Lea Muster wird 36 Jahre" in text_body
    assert "25.09.2026: Lea Muster feiert 10 Jahre Mitglied" in text_body
