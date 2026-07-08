"""The Identity service — identity records and field tokenization.

Every method returns an ApiResponse value and NEVER raises: validation failure
-> format_response(400, <msg>, None) with the request fn NOT called; raised
errors -> handle_error -> 500. No identity method ever passes header_options.

Path behavior notes:
- ONLY `delete` URL-encodes the path id; every other method interpolates the
  raw id (and raw field name) into the path.
- `get` and `update` perform NO id validation at all (`get("")` issues
  `GET identities/` — the list endpoint).
- `tokenize`/`detokenize` send their data argument AS-IS (no copy/transform);
  `create`/`update` serialize via serialize_identity_data first.
- Verb asymmetry: `tokenize_field` is POST, `detokenize_field` is GET (so only
  detokenize_field participates in the core GET-retry policy).
"""

from __future__ import annotations

from typing import Any, Callable

from ..identity_serialization import serialize_identity_data
from ..logger import handle_error
from ..uri_utils import percent_encode
from ..validators.identity_validators import (
    validate_detokenize_identity_data,
    validate_identity,
    validate_identity_id,
    validate_tokenize_identity_data,
    validate_tokenize_identity_field,
)


class Identity:
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
        """POST identities — validates the identity, then serializes it via
        serialize_identity_data."""
        try:
            message = validate_identity(data)
            if message:
                return self._format_response(400, message, None)
            payload = serialize_identity_data(data)
            return self._request("identities", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "create")

    def get(self, id: Any) -> Any:
        """GET identities/{id} — no validation, raw (un-encoded) id."""
        try:
            return self._request(f"identities/{id}", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "get")

    def list(self) -> Any:
        """GET identities."""
        try:
            return self._request("identities", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "list")

    def update(self, id: Any, data: Any) -> Any:
        """PUT identities/{id} — body validated, id NOT."""
        try:
            message = validate_identity(data)
            if message:
                return self._format_response(400, message, None)
            payload = serialize_identity_data(data)
            return self._request(f"identities/{id}", payload, "PUT")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "update")

    def delete(self, id: Any) -> Any:
        """DELETE identities/{id} with the id URL-encoded — the ONLY method
        that URL-encodes the id. No request body."""
        try:
            message = validate_identity_id(id)
            if message:
                return self._format_response(400, message, None)
            return self._request(
                f"identities/{percent_encode(id)}", None, "DELETE"
            )
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "delete")

    def get_tokenized_fields(self, id: Any) -> Any:
        """GET identities/{id}/tokenized-fields (raw id)."""
        try:
            message = validate_identity_id(id)
            if message:
                return self._format_response(400, message, None)
            return self._request(f"identities/{id}/tokenized-fields", None, "GET")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "getTokenizedFields"
            )

    def tokenize_field(self, id: Any, field: Any) -> Any:
        """POST identities/{id}/tokenize/{field} (raw id AND raw field)."""
        try:
            message = validate_tokenize_identity_field(id, field)
            if message:
                return self._format_response(400, message, None)
            return self._request(f"identities/{id}/tokenize/{field}", None, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "tokenizeField"
            )

    def tokenize(self, id: Any, data: Any) -> Any:
        """POST identities/{id}/tokenize — data sent AS-IS (no copy)."""
        try:
            message = validate_tokenize_identity_data(id, data)
            if message:
                return self._format_response(400, message, None)
            return self._request(f"identities/{id}/tokenize", data, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "tokenize")

    def detokenize_field(self, id: Any, field: Any) -> Any:
        """GET identities/{id}/detokenize/{field} (raw id AND raw field)."""
        try:
            message = validate_tokenize_identity_field(id, field)
            if message:
                return self._format_response(400, message, None)
            return self._request(f"identities/{id}/detokenize/{field}", None, "GET")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "detokenizeField"
            )

    def detokenize(self, id: Any, data: Any) -> Any:
        """POST identities/{id}/detokenize — data sent AS-IS; empty `fields`
        means detokenize all currently tokenized fields."""
        try:
            message = validate_detokenize_identity_data(id, data)
            if message:
                return self._format_response(400, message, None)
            return self._request(f"identities/{id}/detokenize", data, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "detokenize"
            )
