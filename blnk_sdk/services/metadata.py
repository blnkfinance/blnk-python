"""The Metadata service.

Metadata operations for ledgers, transactions, balances, and identities.
`update` uses HTTP POST (not PUT/PATCH) to `{id}/metadata`, where the
caller-supplied entity id forms the leading path segment(s). The id is
validated but NOT URL-encoded — an id containing "/" changes the path shape.
"""

from __future__ import annotations

from typing import Any, Callable

from ..logger import handle_error
from ..validators.metadata_validators import validate_update_metadata_data


def _serialize(data: Any) -> Any:
    """DTOs are serialized to wire dicts before the request; raw dicts are
    forwarded by reference, untouched."""
    if not isinstance(data, dict):
        to_dict = getattr(data, "to_dict", None)
        if callable(to_dict):
            return to_dict()
    return data


class Metadata:
    def __init__(
        self,
        request: Callable[..., Any],
        logger: Any,
        format_response: Callable[..., Any],
    ) -> None:
        self._request = request
        self._logger = logger
        self._format_response = format_response

    def update(self, id: str, data: Any) -> Any:
        """POST {id}/metadata — validates id + body, forwards `data` unmodified."""
        try:
            payload = _serialize(data)
            validator_response = validate_update_metadata_data(id, payload)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request(f"{id}/metadata", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "update")
