"""The Transactions service — transaction creation, inflight management,
refunds, lookups, and bulk operations.

Methods never raise: validation failures return (400, <exact message>, None)
WITHOUT calling the request function; anything raised surfaces through
handle_error with the method's reporting name (e.g. "updateStatus") — logs
and callers depend on these exact strings. Endpoint strings have NO leading
slash (the client's base_url ends with "/").
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ..logger import handle_error
from ..transaction_serialization import serialize_create_transaction
from ..uri_utils import percent_encode
from ..validators.transaction_validators import (
    validate_bulk_commit_inflight,
    validate_bulk_transactions,
    validate_bulk_void_inflight,
    validate_create_transactions,
    validate_recover_queue,
    validate_refund_transaction,
    validate_update_transactions,
)


def _dict_view(data: Any) -> Any:
    """Wire-shaped dict view of a payload: dicts pass through unchanged
    (as-is bodies remain the caller's object), DTOs via to_dict()."""
    if isinstance(data, dict):
        return data
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return data


class Transactions:
    """see https://docs.blnkfinance.com/transactions/statuses"""

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
        """POST transactions — body is serialize_create_transaction(data)."""
        try:
            view = _dict_view(data)
            validator_response = validate_create_transactions(view)
            if validator_response:
                return self._format_response(400, validator_response, None)

            payload = serialize_create_transaction(view)
            response = self._request("transactions", payload, "POST")
            return response
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "create")

    def update_status(self, id: str, update: Any) -> Any:
        """PUT transactions/inflight/{id} — body sent as-is; the id is never
        validated nor URL-encoded."""
        try:
            view = _dict_view(update)
            validator_response = validate_update_transactions(view)
            if validator_response:
                return self._format_response(400, validator_response, None)
            return self._request(f"transactions/inflight/{id}", view, "PUT")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "updateStatus"
            )

    def refund(self, id: str, options: Optional[Any] = None) -> Any:
        """POST refund-transaction/{id} — optional body (None when no options
        are given); the id is never validated nor URL-encoded."""
        try:
            body = None
            if options is not None:
                view = _dict_view(options)
                validator_response = validate_refund_transaction(view)
                if validator_response:
                    return self._format_response(400, validator_response, None)
                body = view

            return self._request(f"refund-transaction/{id}", body, "POST")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "refund")

    def get(self, transaction_id: str) -> Any:
        """GET transactions/{transaction_id} — raw id, no encoding."""
        try:
            if not transaction_id:
                return self._format_response(400, "transaction id is required", None)

            return self._request(f"transactions/{transaction_id}", None, "GET")
        except Exception as error:
            return handle_error(error, self._logger, self._format_response, "get")

    def get_by_reference(self, reference: str) -> Any:
        """GET transactions/reference/{reference} with the reference
        URL-encoded."""
        try:
            if not reference:
                return self._format_response(400, "reference is required", None)

            return self._request(
                f"transactions/reference/{percent_encode(reference)}",
                None,
                "GET",
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "getByReference"
            )

    def get_lineage(self, transaction_id: str) -> Any:
        """GET transactions/{transaction_id}/lineage — raw (un-encoded) id."""
        try:
            if not transaction_id:
                return self._format_response(400, "transaction id is required", None)

            return self._request(
                f"transactions/{transaction_id}/lineage", None, "GET"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "getLineage"
            )

    def recover_queue(self, options: Optional[Any] = None) -> Any:
        """POST transactions/recover — the threshold goes in the query
        string, URL-encoded but not trimmed; no body."""
        try:
            threshold = None
            if options is not None:
                view = _dict_view(options)
                validator_response = validate_recover_queue(view)
                if validator_response:
                    return self._format_response(400, validator_response, None)
                threshold = view.get("threshold")

            endpoint = (
                f"transactions/recover?threshold={percent_encode(threshold)}"
                if threshold
                else "transactions/recover"
            )

            return self._request(endpoint, None, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "recoverQueue"
            )

    def bulk_commit_inflight(self, data: Any) -> Any:
        """POST transactions/inflight/bulk/commit — body sent as-is."""
        try:
            view = _dict_view(data)
            validator_response = validate_bulk_commit_inflight(view)
            if validator_response:
                return self._format_response(400, validator_response, None)

            return self._request(
                "transactions/inflight/bulk/commit", view, "POST"
            )
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "bulkCommitInflight"
            )

    def bulk_void_inflight(self, data: Any) -> Any:
        """POST transactions/inflight/bulk/void — body sent as-is."""
        try:
            view = _dict_view(data)
            validator_response = validate_bulk_void_inflight(view)
            if validator_response:
                return self._format_response(400, validator_response, None)

            return self._request("transactions/inflight/bulk/void", view, "POST")
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "bulkVoidInflight"
            )

    def create_bulk(self, data: Any) -> Any:
        """POST transactions/bulk — each item runs through
        serialize_create_transaction; top-level flags pass through."""
        try:
            view = _dict_view(data)
            validator_response = validate_bulk_transactions(view)
            if validator_response:
                return self._format_response(400, validator_response, None)

            payload = {
                **view,
                "transactions": [
                    serialize_create_transaction(transaction)
                    for transaction in view["transactions"]
                ],
            }

            response = self._request("transactions/bulk", payload, "POST")
            return response
        except Exception as error:
            return handle_error(
                error, self._logger, self._format_response, "createBulk"
            )
