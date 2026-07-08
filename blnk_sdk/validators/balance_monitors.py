"""Validators for balance-monitor requests.

Validators return the exact error message string on failure, None when valid;
the first failing check wins.

Absent-vs-None semantics: validators operate on the payload's dict view. An
absent key is treated as "not provided" and skips the optional-field checks;
a key explicitly present with None fails the type checks. DTO inputs are
converted via `to_dict()`, which drops None-valued fields, so a None DTO
field reads as absent.
"""

from __future__ import annotations

from typing import Any, Optional

from ..string_utils import is_valid_number, is_valid_operator, is_valid_string
from ..types import DTO

__all__ = ["validate_monitor_data", "validate_monitor_id"]


def _object_view(data: Any) -> Optional[Any]:
    """Structured-payload gate.

    dicts and lists both pass; DTOs pass via their dict view; falsy values
    and str/number/bool fail. Returns the dict/list view, or None when the
    gate fails (empty dicts and lists still pass).
    """
    if isinstance(data, (dict, list)):
        return data
    if isinstance(data, DTO):
        return data.to_dict()
    return None


def _get(view: Any, key: str) -> Any:
    """Reads a field from the view: a missing key reads as None ("not
    provided"); list views have no named fields, so every key reads as
    None."""
    if isinstance(view, dict):
        return view.get(key)
    return None


def validate_monitor_id(id: Any) -> Optional[str]:
    """Validates a monitor id. Used only by BalanceMonitor.delete — get and
    update intentionally perform no id validation. A whitespace-only id is
    accepted."""
    if not is_valid_string(id) or id == "":
        return "monitor id is required"

    return None


def validate_monitor_data(data: Any) -> Optional[str]:
    """Validates monitor data for BalanceMonitor.create and .update."""
    # Validate if data is an object
    d = _object_view(data)
    if d is None:
        return "Data must be a valid object of type MonitorData"

    # balance_id only needs to be a string — an empty string passes. A list
    # payload passes the object gate but has no balance_id, so it fails here.
    if not is_valid_string(_get(d, "balance_id")):
        return "balance_id must be a valid string"

    # Every condition failure reports the same composite message.
    if not _is_valid_condition(_get(d, "condition")):
        return "condition must be a valid MonitorCondition object"

    # description is optional: an absent key skips the check; a key
    # explicitly present with None fails it.
    if "description" in d and not is_valid_string(d["description"]):
        return "description must be a valid string if provided"

    # Validate call_back_url if provided
    if "call_back_url" in d and not is_valid_string(d["call_back_url"]):
        return "call_back_url must be a valid string if provided"

    # All validations passed
    return None


def _is_valid_condition(condition: Any) -> bool:
    """Checks a monitor condition: a structured payload (lists pass the gate
    but then lack the named fields), a string `field` (empty strings pass),
    an operator among the six supported symbols, and numeric `value` and
    `precision` (NaN and infinities count as numbers; booleans do not)."""
    c = _object_view(condition)
    return (
        c is not None
        and is_valid_string(_get(c, "field"))
        and is_valid_operator(_get(c, "operator"))
        and is_valid_number(_get(c, "value"))
        and is_valid_number(_get(c, "precision"))
    )
