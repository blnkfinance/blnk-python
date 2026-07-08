"""The ApiKeys service — API key management. Blnk Core requires the master
key or the `api-keys:write` scope for these endpoints.

Endpoint strings have NO leading slash (the client concatenates onto base_url,
which is guaranteed to end with "/"). No header_options are ever passed
(3-arg request calls). Every method is wrapped in try/except -> handle_error
with its own method name.

ApiKeys URL-encodes BOTH the id path segment and the owner query value
(contrast Hooks, which never encodes). Query strings are appended manually —
exactly one `?owner=` pair, never `&`.
"""

from __future__ import annotations

from typing import Any, Callable

from ..logger import handle_error
from ..uri_utils import percent_encode
from ..validators.api_key_validators import (
    validate_create_api_key_data,
    validate_delete_api_key_options,
    validate_list_api_keys_options,
)


def _serialize(data: Any) -> Any:
    """DTOs are serialized to wire dicts before the request; raw dicts are
    forwarded by reference — the caller's object passes through unmodified."""
    if not isinstance(data, dict):
        to_dict = getattr(data, "to_dict", None)
        if callable(to_dict):
            return to_dict()
    return data


def _option(options: Any, name: str) -> Any:
    """Read an optional field from dict or DTO options (None when absent)."""
    if isinstance(options, dict):
        return options.get(name)
    return getattr(options, name, None)


class ApiKeys:
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
        """POST api-keys — validates, then forwards `data` unmodified.
        `expires_at` is sent exactly as provided, even though validation
        trims whitespace when checking it."""
        try:
            payload = _serialize(data)
            validator_response = validate_create_api_key_data(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request("api-keys", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "create")

    def list(self, options: Any = None) -> Any:
        """GET api-keys, or api-keys?owner={owner} with the owner
        URL-encoded. An owner key explicitly set to None fails validation
        before the endpoint is built, so the `is not None` check only ever
        distinguishes absent from present."""
        try:
            validator_response = validate_list_api_keys_options(options)
            if validator_response:
                return self._format_response(400, validator_response, None)

            owner = _option(options, "owner")
            endpoint = (
                f"api-keys?owner={percent_encode(owner)}"
                if owner is not None
                else "api-keys"
            )
            return self._request(endpoint, None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "list")

    def delete(self, id: str, options: Any = None) -> Any:
        """DELETE api-keys/{id}[?owner=...] with both id and owner
        URL-encoded. The id truthiness check runs FIRST (before options
        validation). Success data is always None — the server responds with
        204 or an empty 200 body."""
        try:
            if not id:
                return self._format_response(400, "api key id is required", None)

            validator_response = validate_delete_api_key_options(options)
            if validator_response:
                return self._format_response(400, validator_response, None)

            endpoint = f"api-keys/{percent_encode(id)}"
            owner = _option(options, "owner")
            if owner is not None:
                endpoint += f"?owner={percent_encode(owner)}"
            return self._request(endpoint, None, "DELETE")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "delete")
