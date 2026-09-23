from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.api.webling import (
    WeblingAuthenticationError,
    WeblingClient,
    WeblingConfigurationError,
)


def _response(payload: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_connection_uses_api_key_header_without_real_http_call(monkeypatch) -> None:
    monkeypatch.setenv("WEBLING_API_KEY", "test-key")
    session = Mock()
    session.request.return_value = _response({"objects": [123]})
    client = WeblingClient("https://verein.webling.ch", session=session)

    assert client.test_connection() is True
    session.request.assert_called_once_with(
        "GET",
        "https://verein.webling.ch/api/1/member",
        headers={"apikey": "test-key"},
        params={"per_page": 1},
        timeout=15,
    )


def test_get_members_and_one_member_field_use_mocked_api_data(monkeypatch) -> None:
    monkeypatch.setenv("WEBLING_API_KEY", "test-key")
    session = Mock()
    session.request.side_effect = [
        _response([{"id": 7, "properties": {"Vorname": "Lea"}}]),
        _response({"id": 7, "properties": {"Vorname": "Lea", "Name": "Muster"}}),
    ]
    client = WeblingClient("https://verein.webling.ch/api/1", session=session)

    assert client.get_members() == [{"id": 7, "properties": {"Vorname": "Lea"}}]
    assert client.get_member_field(7, "Vorname") == "Lea"


def test_client_requires_api_key_environment_variable(monkeypatch) -> None:
    monkeypatch.delenv("WEBLING_API_KEY", raising=False)

    with pytest.raises(WeblingConfigurationError, match="WEBLING_API_KEY"):
        WeblingClient("https://verein.webling.ch")


def test_client_reports_invalid_api_key(monkeypatch) -> None:
    monkeypatch.setenv("WEBLING_API_KEY", "invalid-key")
    session = Mock()
    session.request.return_value = _response({}, status_code=401)
    client = WeblingClient("https://verein.webling.ch", session=session)

    with pytest.raises(WeblingAuthenticationError, match="abgelehnt"):
        client.test_connection()
