"""The LedgerBalances service.

Manages ledger balances: create/get balances, indicator lookup, identity
updates, snapshots, at-timestamp reads, and fund lineage.
See https://docs.blnkfinance.com/balances/asset-classes for details.

Every method is wrapped in try/except; raised errors go through handle_error
with the method's reporting name (e.g. "getByIndicator") — logs and callers
depend on these exact strings. Validation failure returns
`format_response(400, message, None)` and the request fn is NOT called.
No method passes header_options.
"""

from __future__ import annotations

from typing import Any, Callable

from ..coercion import format_number, is_truthy
from ..logger import handle_error
from ..types import DTO
from ..uri_utils import percent_encode
from ..validators.ledger_balance import (
    validate_create_balance_snapshot,
    validate_create_ledger_balance,
    validate_get_balance,
    validate_get_balance_at,
    validate_get_by_indicator,
    validate_update_balance_identity,
)


def _payload(data: Any) -> Any:
    """DTOs serialize to their dict view; raw dicts pass through unchanged —
    the caller's object is forwarded as-is (no renames, no transforms)."""
    return data.to_dict() if isinstance(data, DTO) else data


def _option(options: Any, name: str) -> Any:
    """Read an optional field from dict or DTO options (None when absent)."""
    if isinstance(options, dict):
        return options.get(name)
    return getattr(options, name, None)


class LedgerBalances:
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
        """POST balances — body forwarded unmodified."""
        try:
            error = validate_create_ledger_balance(data)
            if error:
                return self._format_response(400, error, None)
            return self._request("balances", _payload(data), "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "create")

    def get(self, id: str, options: Any = None) -> Any:
        """GET balances/{id}[?from_source=true][&with_queued=true].

        The `id` is never validated (`get("")` performs `GET balances/`) and
        is NOT URL-encoded.
        """
        try:
            if options is not None:
                error = validate_get_balance(options)
                if error:
                    return self._format_response(400, error, None)

            endpoint = f"balances/{id}"
            params: list[str] = []
            if options is not None and is_truthy(_option(options, "from_source")):
                params.append("from_source=true")
            if options is not None and is_truthy(_option(options, "with_queued")):
                params.append("with_queued=true")
            if params:
                endpoint += "?" + "&".join(params)

            return self._request(endpoint, None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "get")

    def get_by_indicator(self, indicator: str, currency: str) -> Any:
        """GET balances/indicator/{indicator}/currency/{currency} — both
        segments are URL-encoded."""
        try:
            error = validate_get_by_indicator(indicator, currency)
            if error:
                return self._format_response(400, error, None)

            return self._request(
                f"balances/indicator/{percent_encode(indicator)}"
                f"/currency/{percent_encode(currency)}",
                None,
                "GET",
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "getByIndicator"
            )

    def update_identity(self, balance_id: str, data: Any) -> Any:
        """PUT balances/{balance_id}/identity — body forwarded unmodified;
        balance_id NOT URL-encoded."""
        try:
            if not balance_id:
                return self._format_response(400, "balance id is required", None)

            error = validate_update_balance_identity(data)
            if error:
                return self._format_response(400, error, None)

            return self._request(
                f"balances/{balance_id}/identity", _payload(data), "PUT"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "updateIdentity"
            )

    def create_snapshot(self, options: Any = None) -> Any:
        """POST balances-snapshots[?batch_size={n}] — no body; batch_size
        travels ONLY in the query string, and is appended only when it is
        truthy AND greater than zero.
        """
        try:
            if options is not None:
                error = validate_create_balance_snapshot(options)
                if error:
                    return self._format_response(400, error, None)

            batch_size = _option(options, "batch_size") if options is not None else None
            if is_truthy(batch_size) and batch_size > 0:
                endpoint = (
                    f"balances-snapshots?batch_size={format_number(batch_size)}"
                )
            else:
                endpoint = "balances-snapshots"

            return self._request(endpoint, None, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "createSnapshot"
            )

    def get_at(self, balance_id: str, options: Any) -> Any:
        """GET balances/{balance_id}/at?timestamp={timestamp}
        [&from_source=true] — the timestamp value is URL-encoded verbatim;
        balance_id is NOT encoded; from_source is unvalidated — any truthy
        value appends the flag."""
        try:
            if not balance_id:
                return self._format_response(400, "balance id is required", None)

            error = validate_get_balance_at(options)
            if error:
                return self._format_response(400, error, None)

            timestamp = _option(options, "timestamp")
            endpoint = (
                f"balances/{balance_id}/at?timestamp={percent_encode(timestamp)}"
            )
            if is_truthy(_option(options, "from_source")):
                endpoint += "&from_source=true"

            return self._request(endpoint, None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "getAt")

    def get_lineage(self, balance_id: str) -> Any:
        """GET balances/{balance_id}/lineage — balance_id NOT URL-encoded."""
        try:
            if not balance_id:
                return self._format_response(400, "balance id is required", None)

            return self._request(f"balances/{balance_id}/lineage", None, "GET")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "getLineage"
            )
