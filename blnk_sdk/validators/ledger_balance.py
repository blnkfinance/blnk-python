"""Validators for ledger-balance requests.

Validators return the exact error message string on failure, None when valid;
the first failing check wins.

Absent-vs-None semantics: validators operate on the payload's dict view. An
absent key is treated as "not provided" and skips the optional-field checks;
a key explicitly present with None fails the type checks. DTO inputs are
converted via `to_dict()`, which drops None fields, so a None DTO field reads
as absent.
"""

from __future__ import annotations

from typing import Any, Optional

from ..string_utils import is_valid_string
from ..types import DTO
from .common import is_valid_meta_data  # re-exported via __all__

__all__ = [
    "ALLOCATION_STRATEGIES",
    "is_valid_meta_data",
    "validate_create_balance_snapshot",
    "validate_create_ledger_balance",
    "validate_get_balance",
    "validate_get_balance_at",
    "validate_get_by_indicator",
    "validate_update_balance_identity",
]

ALLOCATION_STRATEGIES = ("FIFO", "LIFO", "PROPORTIONAL")


def _object_view(data: Any) -> Optional[dict]:
    """Structured-payload guard.

    dict and DTO inputs count as objects; anything else (None, str, number,
    bool, ...) fails the guard. Returns the dict view, or None when the
    guard fails (an empty dict is a valid object).
    """
    if isinstance(data, dict):
        return data
    if isinstance(data, DTO):
        return data.to_dict()
    return None


def validate_create_ledger_balance(data: Any) -> Optional[str]:
    """Validates the payload for creating a ledger balance (used by
    `create`)."""
    # Validate if data is an object
    d = _object_view(data)
    if d is None:
        return "Data must be a valid object of type CreateLedgerBalance"

    # ledger_id only needs to be a string — an empty string passes.
    if not is_valid_string(d.get("ledger_id")):
        return "ledger_id must be a valid string"

    # identity_id is optional: an absent key skips the check; a key
    # explicitly present with None fails it.
    if "identity_id" in d and not is_valid_string(d["identity_id"]):
        return "identity_id must be a valid string if provided"

    # currency is only checked to be a string — any string passes, even
    # though the message names 'USD' and 'NGN'; callers depend on the exact
    # message text.
    if not is_valid_string(d.get("currency")):
        return "currency must be either 'USD' or 'NGN'"

    # meta_data is optional; any structured value (lists included) passes.
    if "meta_data" in d and not is_valid_meta_data(d["meta_data"]):
        return "meta_data must be a valid object if provided"

    if "track_fund_lineage" in d and not isinstance(d["track_fund_lineage"], bool):
        return "track_fund_lineage must be a boolean if provided"

    if (
        "allocation_strategy" in d
        and d["allocation_strategy"] not in ALLOCATION_STRATEGIES
    ):
        return "allocation_strategy must be one of FIFO, LIFO, or PROPORTIONAL"

    # All validations passed
    return None


def validate_get_by_indicator(indicator: Any, currency: Any) -> Optional[str]:
    """Validates the indicator/currency pair for balance lookups."""
    if not is_valid_string(indicator) or indicator == "":
        return "indicator is required"

    if not is_valid_string(currency) or currency == "":
        return "currency is required"

    return None


def validate_update_balance_identity(data: Any) -> Optional[str]:
    """Validates the payload for updating a balance's identity."""
    d = _object_view(data)
    if d is None:
        return "Data must be a valid object of type UpdateBalanceIdentity"

    if not is_valid_string(d.get("identity_id")) or d["identity_id"] == "":
        return "identity_id is required"

    return None


def validate_create_balance_snapshot(data: Any = None) -> Optional[str]:
    """Validates optional balance-snapshot options.

    A None payload means "no options" and is valid. (Callers such as
    `create_snapshot` only invoke this when options are provided, but the
    None early-out remains part of the validator's own behavior.)
    """
    if data is None:
        return None

    d = _object_view(data)
    if d is None:
        return "Data must be a valid object of type CreateBalanceSnapshotRequest"

    # Relational check only — there is no numeric type check, and 0 passes
    # ("positive" here effectively means "non-negative").
    if "batch_size" in d and d["batch_size"] < 0:
        return "batch_size must be positive"

    return None


def validate_get_balance(data: Any) -> Optional[str]:
    """Validates options for retrieving a balance."""
    d = _object_view(data)
    if d is None:
        return "Data must be a valid object of type GetBalanceRequest"

    if "from_source" in d and not isinstance(d["from_source"], bool):
        return "from_source must be a boolean if provided"

    if "with_queued" in d and not isinstance(d["with_queued"], bool):
        return "with_queued must be a boolean if provided"

    return None


def validate_get_balance_at(data: Any) -> Optional[str]:
    """Validates options for retrieving a balance at a point in time.

    Note: `from_source` is intentionally not validated here, unlike
    validate_get_balance.
    """
    d = _object_view(data)
    if d is None:
        return "Data must be a valid object of type GetBalanceAtRequest"

    if not is_valid_string(d.get("timestamp")) or d["timestamp"] == "":
        return "timestamp is required"

    return None
