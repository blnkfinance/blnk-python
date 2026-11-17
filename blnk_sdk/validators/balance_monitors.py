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

__all__ = [
    "validate_monitor_data",
    "validate_monitor_id",
    "validate_monitor_trigger",
    "validate_update_monitor_request",
]

# Core's NormalizeTrigger accepts "" (its default, edge), "edge" and "level".
_VALID_TRIGGERS = ("", "edge", "level")
_TRIGGER_MESSAGE = 'trigger must be "edge" or "level" if provided'

# Top-level keys Core reads on PUT balance-monitors/{id}. call_back_url is
# left out on purpose: Core ignores it on update.
_UPDATE_KEYS = ("balance_id", "description", "condition", "trigger")
_UPDATE_CONDITION_KEYS = ("field", "operator", "value", "precision")


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

    if "trigger" in d:
        trigger_error = validate_monitor_trigger(d["trigger"])
        if trigger_error:
            return trigger_error

    # All validations passed
    return None


def validate_monitor_trigger(trigger: Any) -> Optional[str]:
    """Validates a monitor trigger: "edge", "level", or "" (Core's default,
    edge)."""
    if not is_valid_string(trigger) or trigger not in _VALID_TRIGGERS:
        return _TRIGGER_MESSAGE
    return None


def validate_update_monitor_request(data: Any) -> Optional[str]:
    """Validates the body for BalanceMonitor.update_partial.

    Every field is optional, because Core keeps whatever a PUT leaves out,
    but at least one must be set. Unknown keys are rejected, including
    `call_back_url`, which Core ignores on update. `condition.field` and
    `condition.operator` may not be empty strings: Core reads an empty
    field and operator sent with `value: 0` as "keep the stored
    threshold", so the SDK never sends that shape.
    """
    if isinstance(data, list):
        return "Data must be a valid object of type UpdateMonitorRequest"
    d = _object_view(data)
    if d is None:
        return "Data must be a valid object of type UpdateMonitorRequest"

    for key in d:
        if key == "call_back_url":
            return "call_back_url cannot be changed on update; Core ignores it"
        if key not in _UPDATE_KEYS:
            return f"unsupported update field: {key}"

    if not d:
        return "at least one field must be set to update a monitor"

    if "balance_id" in d and (
        not is_valid_string(d["balance_id"]) or d["balance_id"].strip() == ""
    ):
        return "balance_id must be a non-empty string if provided"

    if "description" in d and not is_valid_string(d["description"]):
        return "description must be a valid string if provided"

    if "trigger" in d:
        trigger_error = validate_monitor_trigger(d["trigger"])
        if trigger_error:
            return trigger_error

    if "condition" in d:
        condition_error = _validate_update_condition(d["condition"])
        if condition_error:
            return condition_error

    return None


def _validate_update_condition(condition: Any) -> Optional[str]:
    if isinstance(condition, list):
        return "condition must be a valid UpdateMonitorCondition object"
    c = _object_view(condition)
    if c is None:
        return "condition must be a valid UpdateMonitorCondition object"

    for key in c:
        if key not in _UPDATE_CONDITION_KEYS:
            return f"unsupported condition field: {key}"

    if not c:
        return "condition must set at least one field if provided"

    if "field" in c and (not is_valid_string(c["field"]) or c["field"] == ""):
        return "condition.field must be a non-empty string if provided"

    if "operator" in c and not is_valid_operator(c["operator"]):
        return "condition.operator must be one of >, <, =, !=, >=, <= if provided"

    if "value" in c and not is_valid_number(c["value"]):
        return "condition.value must be a number if provided"

    if "precision" in c and not is_valid_number(c["precision"]):
        return "condition.precision must be a number if provided"

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
