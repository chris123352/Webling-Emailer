from __future__ import annotations

from datetime import date
from unittest.mock import Mock

from app.modules.birthdays import find_birthdays_today, get_todays_birthdays


def _member(birthday: str) -> dict:
    return {
        "id": 42,
        "properties": {"Vorname": "Lea", "Name": "Muster", "Geburtstag": birthday},
    }


def test_birthday_today_is_detected_and_age_is_calculated() -> None:
    result = find_birthdays_today([_member("1990-08-04")], today=date(2026, 8, 4))

    assert len(result.birthdays) == 1
    assert result.birthdays[0].display_name == "Lea Muster"
    assert result.birthdays[0].age == 36


def test_birthday_tomorrow_is_not_detected() -> None:
    result = find_birthdays_today([_member("1990-08-05")], today=date(2026, 8, 4))

    assert result.birthdays == ()


def test_leap_day_birthday_is_recognized_on_28_february_in_non_leap_year() -> None:
    result = find_birthdays_today([_member("2000-02-29")], today=date(2025, 2, 28))

    assert len(result.birthdays) == 1
    assert result.birthdays[0].age == 25


def test_birthday_preview_loads_members_from_client() -> None:
    client = Mock()
    client.get_members.return_value = [_member("1990-08-04")]

    result = get_todays_birthdays(client, today=date(2026, 8, 4))

    client.get_members.assert_called_once_with()
    assert result.birthdays[0].member_id == 42
