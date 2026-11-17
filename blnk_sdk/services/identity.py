"""The Identity service — identity records and field tokenization.

Every method returns an ApiResponse value and NEVER raises: validation failure
-> format_response(400, <msg>, None) with the request fn NOT called; raised
errors -> handle_error -> 500. No identity method ever passes header_options.

Path behavior notes:
- Every path id (and tokenize/detokenize field name) goes through
  `endpoint_path`: a value that is not a single safe path segment (empty,
  "." / "..", or containing / \\ ? # % or a control character) returns 400
  without a request; anything else is percent-encoded.
- `tokenize`/`detokenize` send their data argument AS-IS (no copy/transform);
  `create`/`update` serialize via serialize_identity_data first.
- Verb asymmetry: `tokenize_field` is POST, `detokenize_field` is GET (so only
  detokenize_field participates in the core GET-retry policy).
"""

from __future__ import annotations

from typing import Any, Callable

from ..identity_serialization import serialize_identity_data
from ..logger import handle_error
from ..uri_utils import endpoint_path
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
        """GET identities/{id} — id validated and encoded by path_segment."""
        try:
            return self._request(endpoint_path("identities/{}", id), None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "get")

    def list(self) -> Any:
        """GET identities."""
        try:
            return self._request("identities", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "list")

    def update(self, id: Any, data: Any) -> Any:
        """PUT identities/{id} — id checked by path_segment first, then the
        body is validated."""
        try:
            endpoint = endpoint_path("identities/{}", id)
            message = validate_identity(data)
            if message:
                return self._format_response(400, message, None)
            payload = serialize_identity_data(data)
            return self._request(endpoint, payload, "PUT")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "update")

    def delete(self, id: Any) -> Any:
        """DELETE identities/{id} — id validated and encoded by path_segment.
        No request body."""
        try:
            message = validate_identity_id(id)
            if message:
                return self._format_response(400, message, None)
            return self._request(
                endpoint_path("identities/{}", id), None, "DELETE"
            )
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "delete")

    def get_tokenized_fields(self, id: Any) -> Any:
        """GET identities/{id}/tokenized-fields."""
        try:
            message = validate_identity_id(id)
            if message:
                return self._format_response(400, message, None)
            return self._request(
                endpoint_path("identities/{}/tokenized-fields", id), None, "GET"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "getTokenizedFields"
            )

    def tokenize_field(self, id: Any, field: Any) -> Any:
        """POST identities/{id}/tokenize/{field} (both segments validated)."""
        try:
            message = validate_tokenize_identity_field(id, field)
            if message:
                return self._format_response(400, message, None)
            return self._request(
                endpoint_path("identities/{}/tokenize/{}", id, field), None, "POST"
            )
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
            return self._request(
                endpoint_path("identities/{}/tokenize", id), data, "POST"
            )
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "tokenize")

    def detokenize_field(self, id: Any, field: Any) -> Any:
        """GET identities/{id}/detokenize/{field} (both segments validated)."""
        try:
            message = validate_tokenize_identity_field(id, field)
            if message:
                return self._format_response(400, message, None)
            return self._request(
                endpoint_path("identities/{}/detokenize/{}", id, field), None, "GET"
            )
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
            return self._request(
                endpoint_path("identities/{}/detokenize", id), data, "POST"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "detokenize"
            )
