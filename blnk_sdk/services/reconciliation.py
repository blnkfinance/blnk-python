"""The Reconciliation service — file uploads, matching rules, and
reconciliation runs.

Endpoint strings have NO leading slash (the client concatenates onto base_url,
which is guaranteed to end with "/"). No header_options are ever passed
(3-arg request calls). Path interpolation (`reconciliation/matching-rules/{id}`,
`reconciliation/{id}`) performs NO URL-encoding. Every method body is wrapped
in try/except -> handle_error with the method's reporting name (e.g.
"createMatchingRule") — logs and callers depend on these exact strings; no
method ever raises to the caller (contrast Ledgers.get).
"""

from __future__ import annotations

import os
from typing import Any, Callable

from ..logger import handle_error
from ..multipart import MultipartBody
from ..validators.reconciliation_validator import (
    validate_matcher,
    validate_run_instant_recon_data,
)


def _serialize(data: Any) -> Any:
    """DTOs are serialized to wire dicts before the request; raw dicts are
    forwarded by reference — the caller's object passes through unmodified."""
    if not isinstance(data, dict):
        to_dict = getattr(data, "to_dict", None)
        if callable(to_dict):
            return to_dict()
    return data


class Reconciliation:
    def __init__(
        self,
        request: Callable[..., Any],
        logger: Any,
        format_response: Callable[..., Any],
    ) -> None:
        self._request = request
        self._logger = logger
        self._format_response = format_response

    @staticmethod
    def _is_readable_stream(stream: Any) -> bool:
        """Best-effort readability check for a file-like object: falsy,
        closed, or readable() False -> invalid."""
        if not stream:
            return False
        if getattr(stream, "closed", False):
            return False
        readable = getattr(stream, "readable", None)
        if callable(readable):
            try:
                return bool(readable())
            except ValueError:
                return False
        if readable is not None:
            return bool(readable)
        return True

    def upload(self, file_input: Any, source: str) -> Any:
        """POST reconciliation/upload — multipart: part `file` first, then part
        `source`. Path branch: a missing local file yields a 404 response
        `File does not exist at path: {path}` without any HTTP call being
        made. Stream branch: an unreadable stream yields 400
        `Invalid read stream provided`."""
        try:
            form_data = MultipartBody()
            if isinstance(file_input, str):
                if not os.path.exists(file_input):
                    return self._format_response(
                        404, f"File does not exist at path: {file_input}", None
                    )
                form_data.append("file", open(file_input, "rb"))
            else:
                if not self._is_readable_stream(file_input):
                    return self._format_response(
                        400, "Invalid read stream provided", None
                    )
                form_data.append("file", file_input)

            # `source` is NOT validated (empty string allowed).
            form_data.append("source", source)
            return self._request("reconciliation/upload", form_data, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "upload")

    def create_matching_rule(self, data: Any) -> Any:
        """POST reconciliation/matching-rules — validates via validate_matcher,
        then forwards `data` unmodified."""
        try:
            payload = _serialize(data)
            validator_response = validate_matcher(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request("reconciliation/matching-rules", payload, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "createMatchingRule"
            )

    def update_matching_rule(self, rule_id: Any, data: Any) -> Any:
        """PUT reconciliation/matching-rules/{rule_id} — truthiness id guard
        first, then validate_matcher (same rules/messages as create)."""
        try:
            if not rule_id:
                return self._format_response(400, "matching rule id is required", None)

            payload = _serialize(data)
            validator_response = validate_matcher(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)

            return self._request(
                f"reconciliation/matching-rules/{rule_id}", payload, "PUT"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "updateMatchingRule"
            )

    def delete_matching_rule(self, rule_id: Any) -> Any:
        """DELETE reconciliation/matching-rules/{rule_id} — truthiness id
        guard; body-less request."""
        try:
            if not rule_id:
                return self._format_response(400, "matching rule id is required", None)

            return self._request(
                f"reconciliation/matching-rules/{rule_id}", None, "DELETE"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "deleteMatchingRule"
            )

    def run(self, data: Any) -> Any:
        """POST reconciliation/start.

        Intentionally performs NO validation of any kind — `data` is
        forwarded untouched (even a falsy value simply produces a body-less
        POST per core client rules). Do NOT add validation."""
        try:
            return self._request("reconciliation/start", _serialize(data), "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "run")

    def run_instant(self, data: Any) -> Any:
        """POST reconciliation/start-instant — validates via
        validate_run_instant_recon_data, then forwards `data` unmodified."""
        try:
            payload = _serialize(data)
            validator_response = validate_run_instant_recon_data(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)

            return self._request("reconciliation/start-instant", payload, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "runInstant"
            )

    def get(self, reconciliation_id: Any) -> Any:
        """GET reconciliation/{reconciliation_id} — truthiness id guard;
        body-less request. Unlike Ledgers.get, this one HAS both the guard
        and the try/except."""
        try:
            if not reconciliation_id:
                return self._format_response(400, "reconciliation id is required", None)

            return self._request(f"reconciliation/{reconciliation_id}", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "get")
