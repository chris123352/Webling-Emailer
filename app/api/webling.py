"""Client for the Webling REST API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import requests


class WeblingError(RuntimeError):
    """Base class for understandable Webling API errors."""


class WeblingConfigurationError(WeblingError):
    """Raised when the client cannot be configured safely."""


class WeblingAuthenticationError(WeblingError):
    """Raised when Webling rejects the configured API key."""


class WeblingRequestError(WeblingError):
    """Raised when Webling cannot be reached or returns invalid data."""


class WeblingClient:
    """Read-only client for Webling's REST API version 1."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key_env: str = "WEBLING_API_KEY",
        timeout_seconds: float = 15,
        session: requests.Session | None = None,
    ) -> None:
        if not base_url.strip():
            raise WeblingConfigurationError("Die Webling-URL ist nicht konfiguriert.")

        self.api_url = self._build_api_url(base_url)
        self.timeout_seconds = timeout_seconds
        self._session = session or requests.Session()
        self._api_key = self._load_api_key(api_key_env)

    def test_connection(self) -> bool:
        """Test API access with a minimal request to the member endpoint."""
        self._get("member", params={"per_page": 1})
        return True

    def get_members(self) -> list[dict[str, Any]]:
        """Return all members visible to the API key, including their properties."""
        response = self._get("member", params={"format": "full"})
        members = response.get("objects") if isinstance(response, Mapping) else response
        if not isinstance(members, list):
            raise WeblingRequestError("Die Webling-Antwort enthält keine gültige Mitgliederliste.")
        if not all(isinstance(member, Mapping) for member in members):
            raise WeblingRequestError("Die Webling-Antwort enthält unvollständige Mitgliedsdaten.")
        return [dict(member) for member in members]

    def get_member(self, member_id: int) -> dict[str, Any]:
        """Return one member record by its Webling ID."""
        response = self._get(f"member/{member_id}")
        if not isinstance(response, Mapping):
            raise WeblingRequestError("Webling lieferte kein gültiges Mitgliedsobjekt.")
        return dict(response)

    def get_member_field(self, member_id: int, field_name: str) -> Any | None:
        """Return one field from a member's Webling properties, if it exists."""
        member = self.get_member(member_id)
        properties = member.get("properties")
        if not isinstance(properties, Mapping):
            raise WeblingRequestError(
                f"Mitglied {member_id} enthält keine gültigen Eigenschaften in der API-Antwort."
            )
        return properties.get(field_name)

    def _get(
        self, path: str, *, params: Mapping[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.api_url}/{path.lstrip('/')}"
        try:
            response = self._session.request(
                "GET",
                url,
                headers={"apikey": self._api_key},
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as error:
            raise WeblingRequestError("Zeitüberschreitung beim Aufruf der Webling-API.") from error
        except requests.RequestException as error:
            raise WeblingRequestError("Webling-API konnte nicht erreicht werden.") from error

        if response.status_code in {401, 403}:
            raise WeblingAuthenticationError("Webling hat den API-Key abgelehnt.")

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise WeblingRequestError(
                f"Webling-API antwortete mit HTTP-Status {response.status_code}."
            ) from error

        try:
            payload = response.json()
        except ValueError as error:
            raise WeblingRequestError("Webling-API lieferte keine gültige JSON-Antwort.") from error

        if isinstance(payload, Mapping):
            return dict(payload)
        if isinstance(payload, list):
            return list(payload)
        raise WeblingRequestError("Webling-API lieferte ein unerwartetes Antwortformat.")

    @staticmethod
    def _build_api_url(base_url: str) -> str:
        normalized_url = base_url.strip().rstrip("/")
        if normalized_url.endswith("/api/1"):
            return normalized_url
        return f"{normalized_url}/api/1"

    @staticmethod
    def _load_api_key(api_key_env: str) -> str:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise WeblingConfigurationError(
                f"Die Umgebungsvariable {api_key_env} für den Webling-API-Key ist nicht gesetzt."
            )
        return api_key
