"""The BalanceMonitor service — balance monitor management.

Endpoint strings have NO leading slash (the client concatenates onto base_url,
which is guaranteed to end with "/"). No header_options are ever passed
(3-arg request calls). `get`/`update` interpolate the RAW id — no validation,
no URL-encoding; only `delete` validates its id and URL-encodes it.
"""

from __future__ import annotations

from typing import Any, Callable

from ..logger import handle_error
from ..string_utils import is_valid_string
from ..uri_utils import percent_encode
from ..validators.balance_monitors import validate_monitor_data, validate_monitor_id


def _serialize(data: Any) -> Any:
    """DTOs are serialized to wire dicts before the request; raw dicts are
    forwarded by reference — the caller's object passes through unmodified."""
    if not isinstance(data, dict):
        to_dict = getattr(data, "to_dict", None)
        if callable(to_dict):
            return to_dict()
    return data


class BalanceMonitor:
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
        """POST balance-monitors — validates, then forwards `data` unmodified.
        MonitorData intentionally carries no meta_data field."""
        try:
            payload = _serialize(data)
            validator_response = validate_monitor_data(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request("balance-monitors", payload, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "create")

    def get(self, id: str) -> Any:
        """GET balance-monitors/{id} — raw id, no validation or encoding;
        get("") issues a real GET balance-monitors/."""
        try:
            return self._request(f"balance-monitors/{id}", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "get")

    def list(self) -> Any:
        """GET balance-monitors."""
        try:
            return self._request("balance-monitors", None, "GET")
        except Exception as error:
            # Note: errors from list() surface under the name "get";
            # callers depend on this exact string.
            return handle_error(error, self._logger, self._format_response, "get")

    def list_by_balance_id(self, balance_id: str) -> Any:
        """GET balance-monitors/balances/{balance_id}.

        Distinct from `list()`, which still returns every monitor. The
        balance_id is interpolated raw (no URL-encoding). Empty or
        whitespace-only ids return 400 without a request.
        """
        try:
            if not is_valid_string(balance_id) or balance_id.strip() == "":
                return self._format_response(400, "balance id is required", None)
            return self._request(
                f"balance-monitors/balances/{balance_id}", None, "GET"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "listByBalanceId"
            )

    def update(self, id: str, data: Any) -> Any:
        """PUT balance-monitors/{id} — raw (un-encoded) id, body validated."""
        try:
            payload = _serialize(data)
            validator_response = validate_monitor_data(payload)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request(f"balance-monitors/{id}", payload, "PUT")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "update")

    def delete(self, id: str) -> Any:
        """DELETE balance-monitors/{id} with the id URL-encoded — the only
        method that validates AND encodes its id."""
        try:
            validator_response = validate_monitor_id(id)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request(
                f"balance-monitors/{percent_encode(id)}", None, "DELETE"
            )
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "delete")
