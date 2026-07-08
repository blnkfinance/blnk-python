"""The Ledgers service — ledger management.

Endpoint strings have NO leading slash (the client concatenates onto base_url,
which is guaranteed to end with "/"). No header_options are ever passed
(3-arg request calls). The path interpolation `ledgers/{id}` performs NO
URL-encoding of the id.
"""

from __future__ import annotations

from typing import Any, Callable

from ..logger import handle_error
from ..validators.ledger_validators import (
    validate_create_ledger,
    validate_update_ledger,
)


def _serialize(data: Any) -> Any:
    """DTOs are serialized to wire dicts before the request; raw dicts are
    forwarded by reference — the caller's object passes through unmodified."""
    if not isinstance(data, dict):
        to_dict = getattr(data, "to_dict", None)
        if callable(to_dict):
            return to_dict()
    return data


class Ledgers:
    def __init__(
        self,
        request: Callable[..., Any],
        logger: Any,
        format_response: Callable[..., Any],
    ) -> None:
        self._request = request
        self._logger = logger
        self._format_response = format_response

    def create(self, data: Any) -> Any:
        """POST ledgers — validates, then forwards `data` unmodified."""
        try:
            payload = _serialize(data)
            error = validate_create_ledger(payload)
            if error:
                return self._format_response(400, error, None)
            return self._request("ledgers", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "create")

    def get(self, id: str) -> Any:
        """GET ledgers/{id}.

        No id validation (get("") issues `GET ledgers/`) and NO try/except —
        if the request function raises, the exception PROPAGATES to the
        caller. Do not add a guard."""
        return self._request(f"ledgers/{id}", None, "GET")

    def update(self, id: str, data: Any) -> Any:
        """PUT ledgers/{id} — inline truthiness id check, then validation."""
        try:
            if not id:
                return self._format_response(400, "ledger id is required", None)

            payload = _serialize(data)
            error = validate_update_ledger(payload)
            if error:
                return self._format_response(400, error, None)

            return self._request(f"ledgers/{id}", payload, "PUT")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "update")
