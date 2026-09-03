"""The Hooks service — webhook management. Blnk Core requires the master key
for these endpoints.

Endpoint strings have NO leading slash (the client concatenates onto base_url,
which is guaranteed to end with "/"). No header_options are ever passed
(3-arg request calls). Every method is wrapped in try/except -> handle_error
with its own method name.

Hooks NEVER URL-encodes anything — the id is interpolated raw into
`hooks/{id}` and the (already-validated) type enum is interpolated raw into
`hooks?type={type}`. Contrast ApiKeys, which encodes both.
"""

from __future__ import annotations

from typing import Any, Callable

from ..logger import handle_error
from ..validators.hook_validators import (
    validate_create_hook_data,
    validate_list_hooks_options,
    validate_update_hook_data,
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


class Hooks:
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
        """POST hooks — validates, then forwards `data` unmodified."""
        try:
            payload = _serialize(data)
            validator_response = validate_create_hook_data(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request("hooks", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "create")

    def list(self, options: Any = None) -> Any:
        """GET hooks, or hooks?type={type} when a type is provided.

        Omitting ``type`` (``hooks.list()``) lists PRE and POST hooks.
        A type key explicitly set to None fails validation before the
        endpoint is built, so the `is not None` check only ever
        distinguishes absent from present; the enum value is interpolated
        RAW (no encoding).
        """
        try:
            validator_response = validate_list_hooks_options(options)
            if validator_response:
                return self._format_response(400, validator_response, None)

            hook_type = _option(options, "type")
            endpoint = (
                f"hooks?type={hook_type}" if hook_type is not None else "hooks"
            )
            return self._request(endpoint, None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "list")

    def get(self, id: str) -> Any:
        """GET hooks/{id} — raw id, no URL-encoding."""
        try:
            if not id:
                return self._format_response(400, "hook id is required", None)
            return self._request(f"hooks/{id}", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "get")

    def update(self, id: str, data: Any) -> Any:
        """PUT hooks/{id} — id truthiness check runs BEFORE payload
        validation; raw (un-encoded) id; `data` forwarded unmodified.
        Note: an invalid payload yields the message that names
        CreateHookData; callers depend on this exact string."""
        try:
            if not id:
                return self._format_response(400, "hook id is required", None)

            payload = _serialize(data)
            validator_response = validate_update_hook_data(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request(f"hooks/{id}", payload, "PUT")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "update")

    def delete(self, id: str) -> Any:
        """DELETE hooks/{id} — raw id, no URL-encoding."""
        try:
            if not id:
                return self._format_response(400, "hook id is required", None)
            return self._request(f"hooks/{id}", None, "DELETE")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "delete")
