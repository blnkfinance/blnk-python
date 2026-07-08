"""Transaction payload serialization.

Re-exports the shared date helpers from blnk_sdk.serialization (their
canonical home) and adds serialize_create_transaction, the payload
serializer used by Transactions.create / Transactions.create_bulk.
"""

from __future__ import annotations

from typing import Any, Dict

from .serialization import (  # noqa: F401 — re-exports
    RFC3339_DATETIME,
    TransactionDateInput,
    is_valid_transaction_date_input,
    serialize_transaction_date,
)

__all__ = [
    "RFC3339_DATETIME",
    "TransactionDateInput",
    "is_valid_transaction_date_input",
    "serialize_create_transaction",
    "serialize_transaction_date",
]

# The exactly-four date keys serialize_create_transaction overwrites.
_DATE_FIELDS = (
    "inflight_expiry_date",
    "scheduled_for",
    "effective_date",
    "inflight_commit_date",
)


def _dict_view(data: Any) -> Any:
    """Dict view of a payload: dicts pass through, DTOs via to_dict()."""
    if isinstance(data, dict):
        return data
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return data


def serialize_create_transaction(data: Any) -> Dict[str, Any]:
    """Shallow-copies the payload and overwrites exactly four date keys with
    serialize_transaction_date(...). Every other field passes through
    untouched (padded precise_amount strings, meta_data, split legs, ...).

    Absent (None) date keys are OMITTED from the payload dict entirely —
    the key must not be sent as null.
    """
    view = _dict_view(data)
    payload = dict(view)
    for key in _DATE_FIELDS:
        serialized = serialize_transaction_date(view.get(key))
        if serialized is None:
            payload.pop(key, None)
        else:
            payload[key] = serialized
    return payload
