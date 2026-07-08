"""Validators for reconciliation requests.

Validators return `str | None` — None means valid; a non-None value is the
exact error message callers surface. Check order is part of the SDK's
behavior: the first failing check wins. Validators accept both raw dicts
(the canonical dict view) and DTO dataclasses (normalized via to_dict();
None fields become absent keys, i.e. "not provided").
"""

from __future__ import annotations

from typing import Any, Optional

from ..coercion import format_number, is_truthy
from ..string_utils import is_valid_array, is_valid_number, is_valid_string
from ..types import DTO
from .common import is_valid_meta_data

MAX_INSTANT_RECON_ITEMS = 10000

_CRITERIA_FIELDS = ("amount", "currency", "reference", "description", "date")
_OPERATORS = ("equals", "greater_than", "less_than", "contains")
_STRATEGIES = ("one_to_one", "one_to_many", "many_to_one")


def _dict_view(data: Any) -> Any:
    """Canonical validator input is the dict view."""
    if isinstance(data, DTO):
        return data.to_dict()
    return data


def _get(data: Any, key: str) -> Any:
    """Reads a field: dict lookup; on anything else (lists included) every
    key reads as None ("not provided")."""
    if isinstance(data, dict):
        return data.get(key)
    return None


def _is_valid_criteria_field(field: Any) -> bool:
    """Exact, case-sensitive membership in the supported criteria fields."""
    return field in _CRITERIA_FIELDS


def _is_valid_operator(operator: Any) -> bool:
    """Exact, case-sensitive membership in the supported operators."""
    return operator in _OPERATORS


def _is_valid_criteria(criteria: Any) -> bool:
    """Checks a criteria object: a structured payload with a valid field, a
    valid operator, and — when present — a numeric allowable_drift.

    Only an absent allowable_drift key is exempt; a key explicitly present
    with None fails. NaN and infinities count as numbers; booleans do not."""
    if not is_truthy(criteria) or not is_valid_meta_data(criteria):
        return False
    if not _is_valid_criteria_field(_get(criteria, "field")):
        return False
    if not _is_valid_operator(_get(criteria, "operator")):
        return False
    if isinstance(criteria, dict) and "allowable_drift" in criteria:
        return is_valid_number(criteria["allowable_drift"])
    return True


def _is_valid_strategy(strategy: Any) -> bool:
    """Exact, case-sensitive membership in the supported strategies."""
    return strategy in _STRATEGIES


def _is_valid_external_transaction(txn: Any) -> bool:
    """Checks an external transaction's field types. Empty strings pass; a
    NaN or infinite amount passes; `date` is a plain string and is never
    parsed."""
    return (
        is_truthy(txn)
        and is_valid_meta_data(txn)
        and is_valid_string(_get(txn, "id"))
        and is_valid_number(_get(txn, "amount"))
        and is_valid_string(_get(txn, "reference"))
        and is_valid_string(_get(txn, "currency"))
        and is_valid_string(_get(txn, "description"))
        and is_valid_string(_get(txn, "date"))
        and is_valid_string(_get(txn, "source"))
    )


def validate_matcher(data: Any) -> Optional[str]:
    """Validates a matcher payload. Used by both create_matching_rule and
    update_matching_rule (identical rules and messages)."""
    data = _dict_view(data)

    # Structured-payload gate: falsy values and truthy non-objects are
    # rejected; dicts and lists pass — a list then fails the `name` check
    # below (it has no named fields).
    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Data must be a valid object of type Matcher"

    # String type checks only — empty strings pass.
    if not is_valid_string(_get(data, "name")):
        return "name must be a valid string"

    if not is_valid_string(_get(data, "description")):
        return "description must be a valid string"

    criteria = _get(data, "criteria")
    if not is_valid_array(criteria):
        return "criteria must be a valid array"

    # An empty criteria array is valid (the loop body never runs).
    for criterion in criteria:
        if not _is_valid_criteria(criterion):
            return (
                "Each criterion must be a valid object of type Criteria with "
                "valid field, operator, and optional allowable_drift"
            )

    return None


def validate_run_instant_recon_data(data: Any) -> Optional[str]:
    """Validates the payload for an instant reconciliation run. Used only by
    run_instant."""
    data = _dict_view(data)

    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Data must be a valid object of type RunInstantReconData"

    external_transactions = _get(data, "external_transactions")
    if not is_valid_array(external_transactions) or len(external_transactions) == 0:
        return "external_transactions must be a non-empty array"

    # Strict greater-than — a batch of exactly 10000 items passes.
    if len(external_transactions) > MAX_INSTANT_RECON_ITEMS:
        return (
            "too many external_transactions; max is "
            f"{format_number(MAX_INSTANT_RECON_ITEMS)}"
        )

    # Transactions are validated before strategy — a payload with both
    # defects reports the transaction message.
    for txn in external_transactions:
        if not _is_valid_external_transaction(txn):
            return (
                "Each external transaction must include id, amount, reference, "
                "currency, description, date, and source"
            )

    # The string-type check and the membership check share one message.
    strategy = _get(data, "strategy")
    if not is_valid_string(strategy) or not _is_valid_strategy(strategy):
        return "strategy must be one of: one_to_one, one_to_many, many_to_one"

    matching_rule_ids = _get(data, "matching_rule_ids")
    if not is_valid_array(matching_rule_ids) or len(matching_rule_ids) == 0:
        return "matching_rule_ids must be a non-empty array"

    for rule_id in matching_rule_ids:
        if not is_valid_string(rule_id):
            return "Each matching_rule_id must be a valid string"

    # Optional fields: only an absent key is exempt; a key explicitly present
    # with None fails the type check. (`data` is guaranteed to be a dict
    # here: non-dicts fail the external_transactions check.)
    if "dry_run" in data and not isinstance(data["dry_run"], bool):
        return "dry_run must be a boolean"

    if "grouping_criteria" in data and not is_valid_string(data["grouping_criteria"]):
        return "grouping_criteria must be a valid string"

    return None
