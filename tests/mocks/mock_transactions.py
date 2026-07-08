"""Stub transaction service and canned transaction payloads for the core
client tests."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from blnk_sdk.api_response import ApiResponse

_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _as_dict(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        return dict(data)
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return {}


def create_dummy_transaction_response() -> Dict[str, Any]:
    """Builds a canned transaction payload.

    Note the deliberately mixed field types, which tests depend on:
    created_at is a live datetime object while the other date fields are the
    zero-time string "0001-01-01T00:00:00Z"; parent_transaction is the empty
    string; the transaction id suffix is nine random base-36 characters.
    """
    return {
        "transaction_id": "txn_" + "".join(random.choices(_BASE36, k=9)),
        "amount": 1000,
        "precision": 2,
        "precise_amount": 100000,
        "reference": "REF12345",
        "description": "Sample transaction description",
        "currency": "USD",
        "status": "INFLIGHT",
        "hash": "0b9c25fb5b00d6c71cb4ca87026bf6dc316e63353d3330deb588bd0b3d74dcc0",
        "parent_transaction": "",
        "source": "source_12345",
        "destination": "destination_67890",
        "sources": [{"identifier": "account1", "distribution": "left"}],
        "allow_overdraft": False,
        "inflight": True,
        "skip_queue": False,
        "atomic": False,
        "created_at": datetime.now(timezone.utc),
        "scheduled_for": "0001-01-01T00:00:00Z",
        "inflight_expiry_date": "0001-01-01T00:00:00Z",
        "inflight_commit_date": "0001-01-01T00:00:00Z",
        "meta_data": {},
    }


class MockTransaction:
    """Stub service used for Ledgers/LedgerBalances/Transactions in the core
    client tests — one class deliberately serves all three service names."""

    def __init__(
        self,
        request: Callable[..., Any],
        logger: Any,
        format_response: Callable[..., Any],
    ) -> None:
        self._request = request
        self._logger = logger
        self._format_response = format_response

    def create(self, data: Any) -> ApiResponse:
        # Dummy fields WIN over caller data.
        return ApiResponse(
            status=200,
            message="Success",
            data={**_as_dict(data), **create_dummy_transaction_response()},
        )

    def update_status(self, id: str, update: Any) -> ApiResponse:
        # Merge order: dummy fields, then the id argument, then the caller's
        # update, then status "COMMIT" — so the caller's status is always
        # overwritten, and an update carrying transaction_id overrides the id
        # argument. Tests depend on this exact precedence.
        return ApiResponse(
            status=200,
            message="Success",
            data={
                **create_dummy_transaction_response(),
                "transaction_id": id,
                **_as_dict(update),
                "status": "COMMIT",
            },
        )

    def refund(self, id: str) -> ApiResponse:
        return ApiResponse(
            status=200,
            message="Success",
            data={**create_dummy_transaction_response(), "transaction_id": id},
        )
