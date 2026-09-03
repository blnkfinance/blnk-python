"""Validators for transaction requests.

Pure validation: every public function takes a request payload and returns
`str | None` — None means valid; a non-None value is the exact error message
(trailing periods and all). Callers turn a non-None result into
`format_response(400, message, None)` and must not send the request.

Validators are synchronous and never mutate the payload. Certain structurally
malformed inputs raise (TypeError/AttributeError) instead of returning a
message — the endpoint's try/except converts that into a 500 via
handle_error.

Canonical input is the dict view of a payload: an absent key means "not
provided", while a key explicitly present with None counts as provided and
fails the relevant checks. DTO inputs are accepted and converted via
`to_dict()` (which omits None fields, so a None DTO field reads as absent).

Precise amounts use exact int arithmetic; plain amounts use float
arithmetic.
"""

from __future__ import annotations

import math
import re
from typing import Any, List, Optional, Tuple

from blnk_sdk.constants import MAX_BULK_CREATE_ITEMS, MAX_BULK_INFLIGHT_ITEMS
from blnk_sdk.coercion import format_number, is_truthy
from blnk_sdk.serialization import is_valid_transaction_date_input
from blnk_sdk.string_utils import is_valid_number, is_valid_string
from blnk_sdk.validators.common import is_valid_meta_data

__all__ = [
    "validate_create_transactions",
    "validate_update_transactions",
    "validate_refund_transaction",
    "validate_bulk_void_inflight",
    "validate_bulk_commit_inflight",
    "validate_bulk_transactions",
    "validate_recover_queue",
]

# 2**53 - 1 — the largest integer a float64 represents exactly (the
# "Number.MAX_SAFE_INTEGER" named in the distribution error message below).
_MAX_SAFE_INTEGER = 9007199254740991

# `\d` is ASCII-only (re.ASCII) — non-ASCII digits are rejected. Patterns
# are applied with fullmatch(), so a trailing newline never sneaks past an
# end anchor.
_NON_NEGATIVE_INTEGER_STRING = re.compile(r"^\d+$", re.ASCII)

# Fixed-amount split legs: non-negative integer or decimal strings only.
# Rejects exponent (`1e3`), hex (`0x10`), and whitespace-padded values.
_FIXED_AMOUNT_DISTRIBUTION = re.compile(r"^(?:\d+|\d+\.\d+)$", re.ASCII)

# Percentage split legs such as `20%` or `33.33%`.
_PERCENTAGE_DISTRIBUTION = re.compile(r"^(?:\d+|\d+\.\d+)%$", re.ASCII)

# NOTE: `µs` is the literal U+00B5 MICRO SIGN followed by `s`.
_GO_DURATION_UNIT = "(?:ns|us|µs|ms|s|m|h)"
_GO_DURATION_PATTERN = re.compile(
    r"^(?:\d+(?:\.\d+)?" + _GO_DURATION_UNIT + r")+$", re.ASCII
)

_DISTRIBUTION_SUM_EPSILON = 1e-9

# Sentinel meaning "key absent", distinguishable from a key explicitly
# present with None (see _validate_optional_date_field).
_MISSING = object()

# (arithmetic mode, value): ("number", float-like) | ("bigint", exact int)
_TransactionTotal = Tuple[str, Any]


def _dict_view(data: Any) -> Any:
    """Canonical validator input is a dict; DTOs convert via to_dict()."""
    if isinstance(data, dict):
        return data
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict) and not isinstance(data, type):
        return to_dict()
    return data


def _validate_optional_date_field(value: Any, field_name: str) -> Optional[str]:
    # An absent field is valid. A key explicitly present with None counts as
    # provided: it falls through and fails the date check.
    if value is _MISSING:
        return None
    if not is_valid_transaction_date_input(value):
        return f"Invalid {field_name}."
    return None


def _parse_precise_integer(value: Any) -> Optional[int]:
    """Parses a precise integer amount into an exact int.

    Numbers: None unless finite, >= 0 and integral (fractions rejected).
    Strings: trimmed, must be all digits (leading zeros fine; `+5`, `-1`,
    `12.5`, ``, `1e3` rejected); arbitrarily large values stay exact. Any
    other type raises AttributeError from `.strip()`, which the endpoint
    surfaces as a 500.
    """
    if is_valid_number(value):
        if isinstance(value, float):
            if not math.isfinite(value) or value < 0 or not value.is_integer():
                return None
            return int(value)
        if value < 0:
            return None
        return value

    trimmed = value.strip()  # raises AttributeError for bool/None/dict/list
    if not _NON_NEGATIVE_INTEGER_STRING.fullmatch(trimmed):
        return None
    return int(trimmed)


def _has_precise_distribution(leg: Any) -> bool:
    # Present and non-None (an absent key reads as None). A non-dict leg
    # carries no fields; a None leg is a caller error that surfaces as a
    # 500 through the endpoint's catch-all.
    if not isinstance(leg, dict) and leg is not None:
        return False
    return leg.get("precise_distribution") is not None


def _uses_precise_integer_arithmetic(data: dict) -> bool:
    sources = data.get("sources")
    if sources is not None and any(_has_precise_distribution(leg) for leg in sources):
        return True
    destinations = data.get("destinations")
    if destinations is not None and any(
        _has_precise_distribution(leg) for leg in destinations
    ):
        return True
    if isinstance(data.get("precise_amount"), str):
        return True
    if data.get("precise_amount") is not None and not is_valid_number(
        data.get("amount")
    ):
        return True
    return False


def _resolve_transaction_total(data: dict) -> Optional[_TransactionTotal]:
    """Resolves the transaction total used for split-leg validation. When
    both `amount` and `precise_amount` are provided, `amount` takes
    precedence."""
    has_amount = is_valid_number(data.get("amount"))
    has_precise_amount = data.get("precise_amount") is not None

    if not has_amount and not has_precise_amount:
        return None

    if _uses_precise_integer_arithmetic(data):
        if has_amount:
            # Fractional amounts silently truncate toward zero; non-finite
            # amounts raise (ValueError/OverflowError), which the endpoint
            # surfaces as a 500.
            return ("bigint", math.trunc(data["amount"]))

        parsed = _parse_precise_integer(data["precise_amount"])
        if parsed is None:
            return None
        return ("bigint", parsed)

    if has_amount:
        return ("number", data["amount"])

    # Defensive fallback: with no `amount` and a present `precise_amount`,
    # _uses_precise_integer_arithmetic is always true, so this path is not
    # reachable in practice; kept as a safety net.
    parsed = _parse_precise_integer(data["precise_amount"])
    if parsed is None:
        return None
    if parsed <= _MAX_SAFE_INTEGER:
        return ("number", float(parsed))
    return ("bigint", parsed)


def _has_positive_length(value: Any) -> bool:
    """True when the value counts as a provided, non-empty collection.

    Lists, tuples and strings use len(); an empty one counts as absent. Any
    other truthy value must carry a positive numeric `length` — read as a
    mapping entry for dicts, as an attribute otherwise (booleans count as
    1/0); a missing or non-numeric length counts as absent."""
    if not is_truthy(value):
        return False
    if isinstance(value, (list, tuple, str)):
        return len(value) > 0
    if isinstance(value, dict):
        length = value.get("length")
    else:
        length = getattr(value, "length", None)
    if isinstance(length, bool):
        length = 1 if length else 0
    if isinstance(length, (int, float)):
        return length > 0
    return False  # a missing or non-numeric length counts as absent


def _validate_split_leg_routing(data: dict) -> Optional[str]:
    has_source = is_truthy(data.get("source"))
    has_sources = _has_positive_length(data.get("sources"))
    has_destination = is_truthy(data.get("destination"))
    has_destinations = _has_positive_length(data.get("destinations"))

    if has_source and has_sources:
        return "Both 'source' and 'sources' cannot be provided together."

    if has_destination and has_destinations:
        return "Both 'destination' and 'destinations' cannot be provided together."

    if has_sources:
        if has_destinations:
            return "'sources' requires a single 'destination'; use 'destination' instead of 'destinations'."
        if not has_destination:
            return "'destination' is required when using 'sources'."

    if has_destinations:
        if has_sources:
            # Defensive: the has_sources branch above already returned, so
            # no input produces this message; kept as a safety net.
            return "'destinations' requires a single 'source'; use 'source' instead of 'sources'."
        if not has_source:
            return "'source' is required when using 'destinations'."

    return None


def _parse_percentage_distribution(distribution: str) -> Optional[float]:
    if not _PERCENTAGE_DISTRIBUTION.fullmatch(distribution):
        return None

    # The regex guarantees `\d+` or `\d+.\d+`, so plain float parsing is safe
    # here (huge digit runs overflow to inf and fail the finite check).
    value = float(distribution[:-1])
    if not math.isfinite(value) or value < 0 or value > 100:
        return None

    return value


def _parse_fixed_amount_distribution(distribution: Any) -> Optional[float]:
    # Rejects whitespace-padded values before the regex runs. A non-string
    # raises AttributeError here, which the endpoint surfaces as a 500.
    if distribution.strip() != distribution:
        return None

    if not _FIXED_AMOUNT_DISTRIBUTION.fullmatch(distribution):
        return None

    value = float(distribution)  # may lose precision for very long digit runs
    if not math.isfinite(value) or value < 0:
        return None

    return value


def _distribution_totals_approximately_equal(sum_value: float, amount: float) -> bool:
    return abs(sum_value - amount) <= _DISTRIBUTION_SUM_EPSILON


def _is_fixed_decimal_distribution(distribution: Any) -> bool:
    parsed = _parse_fixed_amount_distribution(distribution)
    return parsed is not None and not float(parsed).is_integer()


def _has_decimal_percentage_distribution(distribution: Any) -> bool:
    parsed = _parse_percentage_distribution(distribution)
    return parsed is not None and not float(parsed).is_integer()


def _leg_uses_decimal_distribution(leg: dict) -> bool:
    # An absent distribution key means "not provided". A key explicitly
    # present with None (or another non-string) falls through into
    # _parse_fixed_amount_distribution and raises — only reachable from the
    # exact-integer dispatch.
    if "distribution" not in leg:
        return False

    distribution = leg["distribution"]
    return _is_fixed_decimal_distribution(
        distribution
    ) or _has_decimal_percentage_distribution(distribution)


def _validate_split_legs(
    legs: Any, total: _TransactionTotal, leg_label: str
) -> Optional[str]:
    leg_array_name = "sources" if leg_label == "source" else "destinations"

    if not isinstance(legs, list) or len(legs) == 0:
        return f"'{leg_array_name}' must be a non-empty array."

    for leg in legs:
        # A primitive leg carries no fields and fails the identifier check;
        # None stays a caller error surfaced as a 500 by the endpoint.
        if not isinstance(leg, dict) and leg is not None:
            leg = {}
        if not is_valid_string(leg.get("identifier")):
            return f"Each {leg_label} leg must include a valid identifier."

        has_distribution = leg.get("distribution") is not None
        has_precise_distribution_value = _has_precise_distribution(leg)

        if not has_distribution and not has_precise_distribution_value:
            return f"Each {leg_label} leg must include either 'distribution' or 'precise_distribution'."

        precise_distribution = leg.get("precise_distribution")
        if (
            has_precise_distribution_value
            and precise_distribution is not None  # redundant with the flag above
            and not isinstance(precise_distribution, str)
            and not is_valid_number(precise_distribution)
        ):
            return f"precise_distribution must be a string or number for leg: {leg.get('identifier')}."

    if total[0] == "bigint":
        return _validate_distribution_legs_bigint(legs, total[1])

    return _validate_distribution_legs_number(legs, total[1])


def _bigint_trunc_div(dividend: int, divisor: int) -> int:
    """Integer division that truncates toward zero (Python's `//` floors)."""
    quotient = abs(dividend) // abs(divisor)
    if (dividend < 0) != (divisor < 0):
        return -quotient
    return quotient


def _validate_distribution_legs_bigint(
    legs: List[dict], total: int
) -> Optional[str]:
    has_decimal_distribution = any(_leg_uses_decimal_distribution(leg) for leg in legs)

    if has_decimal_distribution and total > _MAX_SAFE_INTEGER:
        return "Decimal distribution values are not supported with precise amounts beyond Number.MAX_SAFE_INTEGER."

    if has_decimal_distribution and total <= _MAX_SAFE_INTEGER:
        return _validate_distribution_legs_with_decimals(legs, float(total))

    sum_value = 0  # exact int arithmetic — no precision loss
    has_left = False

    for leg in legs:
        if _has_precise_distribution(leg):
            precise_value = _parse_precise_integer(leg["precise_distribution"])
            if precise_value is None:
                return f"Invalid precise_distribution for leg: {leg.get('identifier')}."
            sum_value += precise_value
            continue

        distribution = leg.get("distribution")
        if not is_truthy(distribution) or not is_valid_string(distribution):
            return f"Invalid distribution type for leg: {leg.get('identifier')}."

        if distribution.endswith("%"):
            percentage_value = _parse_percentage_distribution(distribution)
            if percentage_value is None:
                return f"Invalid percentage value in leg: {leg.get('identifier')}."
            # (total * pct) / 100 with truncation toward zero. Decimal
            # percentages never reach this path, so int(pct) is safe.
            sum_value += _bigint_trunc_div(total * int(percentage_value), 100)
        elif distribution == "left":
            if has_left:
                return "Multiple 'left' distribution types are not allowed."
            has_left = True
        else:
            fixed_amount = _parse_fixed_amount_distribution(distribution)
            if fixed_amount is None or not float(fixed_amount).is_integer():
                return f"Invalid distribution type for leg: {leg.get('identifier')}."
            sum_value += int(fixed_amount)

    if has_left:
        remaining = total - sum_value
        if remaining < 0:
            return "Total distribution exceeds the specified amount."
    elif sum_value != total:
        return f"Total distribution sum ({sum_value}) does not equal the specified amount ({total})."

    return None


def _validate_distribution_legs_number(legs: List[dict], amount: Any) -> Optional[str]:
    return _validate_distribution_legs_with_decimals(legs, amount)


def _validate_distribution_legs_with_decimals(
    legs: List[dict], amount: Any
) -> Optional[str]:
    amount = float(amount)  # distribution math on this path is float-based
    sum_value = 0.0
    has_left = False

    for leg in legs:
        if _has_precise_distribution(leg):
            precise_value = _parse_precise_integer(leg["precise_distribution"])
            if precise_value is None:
                return f"Invalid precise_distribution for leg: {leg.get('identifier')}."
            if precise_value > _MAX_SAFE_INTEGER:
                # Values beyond the exact-float range are rejected with the
                # same message as an unparseable precise_distribution.
                return f"Invalid precise_distribution for leg: {leg.get('identifier')}."
            sum_value += float(precise_value)
            continue

        distribution = leg.get("distribution")
        if not is_truthy(distribution) or not is_valid_string(distribution):
            return f"Invalid distribution type for leg: {leg.get('identifier')}."

        if distribution.endswith("%"):
            percentage_value = _parse_percentage_distribution(distribution)
            if percentage_value is None:
                return f"Invalid percentage value in leg: {leg.get('identifier')}."
            sum_value += (percentage_value / 100) * amount
        elif distribution == "left":
            if has_left:
                return "Multiple 'left' distribution types are not allowed."
            has_left = True
        else:
            fixed_amount = _parse_fixed_amount_distribution(distribution)
            if fixed_amount is None:
                return f"Invalid distribution type for leg: {leg.get('identifier')}."
            sum_value += fixed_amount

    if has_left:
        remaining = amount - sum_value
        if remaining < -_DISTRIBUTION_SUM_EPSILON:
            return "Total distribution exceeds the specified amount."
    elif not _distribution_totals_approximately_equal(sum_value, amount):
        # format_number renders integral floats without a trailing `.0`.
        return (
            f"Total distribution sum ({format_number(sum_value)}) "
            f"does not equal the specified amount ({format_number(amount)})."
        )

    return None


def _is_valid_go_duration(value: str) -> bool:
    trimmed = value.strip()
    return len(trimmed) > 0 and _GO_DURATION_PATTERN.fullmatch(trimmed) is not None


def validate_create_transactions(data: Any) -> Optional[str]:
    """Validates the payload for creating a transaction."""
    data = _dict_view(data)

    transaction_total = _resolve_transaction_total(data)
    if transaction_total is None:
        if data.get("precise_amount") is not None and not is_valid_number(
            data.get("amount")
        ):
            return "precise_amount must be a non-negative integer string or number."
        return "Either 'amount' or 'precise_amount' must be provided."

    if "amount" in data and not is_valid_number(data["amount"]):
        return "Amount must be a number."

    precise_amount = data.get("precise_amount")
    if precise_amount is not None:
        is_valid_precise_amount = is_valid_number(precise_amount) or isinstance(
            precise_amount, str
        )
        if not is_valid_precise_amount:
            return "precise_amount must be a string or number."
        if _parse_precise_integer(precise_amount) is None:
            return "precise_amount must be a non-negative integer string or number."

    # Required; only the numeric type is checked — NaN, negative and
    # infinite values pass.
    if not is_valid_number(data.get("precision")):
        return "Precision must be a number."
    if not isinstance(data.get("reference"), str):
        return "Reference must be a string."
    if not isinstance(data.get("description"), str):
        return "Description must be a string."
    if not is_valid_string(data.get("currency")):  # an empty string passes
        return "Invalid currency."

    split_leg_error = _validate_split_leg_routing(data)
    if split_leg_error:
        return split_leg_error

    source = data.get("source")
    if is_truthy(source) and not isinstance(source, str):
        return "Invalid source."

    destination = data.get("destination")
    if is_truthy(destination) and not isinstance(destination, str):
        return "Destination must be a string."  # asymmetric with "Invalid source." above

    # A present-but-empty `sources` list still enters split-leg validation
    # (is_truthy treats an empty list as present) and fails the non-empty
    # check there.
    if is_truthy(data.get("sources")):
        sources_error = _validate_split_legs(
            data["sources"], transaction_total, "source"
        )
        if sources_error:
            return sources_error

    if is_truthy(data.get("destinations")):
        destinations_error = _validate_split_legs(
            data["destinations"], transaction_total, "destination"
        )
        if destinations_error:
            return destinations_error

    if "inflight" in data and not isinstance(data["inflight"], bool):
        return "Inflight must be a boolean if provided."

    inflight_expiry_error = _validate_optional_date_field(
        data.get("inflight_expiry_date", _MISSING), "inflight expiry date"
    )
    if inflight_expiry_error:
        return inflight_expiry_error

    scheduled_for_error = _validate_optional_date_field(
        data.get("scheduled_for", _MISSING), "scheduled date"
    )
    if scheduled_for_error:
        return scheduled_for_error

    effective_date_error = _validate_optional_date_field(
        data.get("effective_date", _MISSING), "effective_date"
    )
    if effective_date_error:
        return effective_date_error

    inflight_commit_error = _validate_optional_date_field(
        data.get("inflight_commit_date", _MISSING), "inflight_commit_date"
    )
    if inflight_commit_error:
        return inflight_commit_error

    if "skip_queue" in data and not isinstance(data["skip_queue"], bool):
        return "skip_queue must be a boolean if provided."

    if "atomic" in data and not isinstance(data["atomic"], bool):
        return "atomic must be a boolean if provided."  # lowercase, unlike the bulk validator

    if "allow_overdraft" in data and not isinstance(data["allow_overdraft"], bool):
        return "Allow overdraft must be a boolean if provided."

    if "meta_data" in data and not is_valid_meta_data(data["meta_data"]):
        return "meta_data must be a valid object if provided"  # note: no trailing period

    if "dry_run" in data and not isinstance(data["dry_run"], bool):
        return "dry_run must be a boolean if provided."

    # No unknown-field check here — extra fields flow through to the API.
    return None


def validate_update_transactions(data: Any) -> Optional[str]:
    """Validates the payload for updating a transaction."""
    data = _dict_view(data)

    # Required; any string is accepted — not restricted to commit/void.
    if not isinstance(data.get("status"), str):
        return "Status must be a string."

    if "amount" in data and not is_valid_number(data["amount"]):
        return "Amount must be a number."

    precise_amount = data.get("precise_amount")
    if precise_amount is not None:
        is_valid_precise_amount = is_valid_number(precise_amount) or isinstance(
            precise_amount, str
        )
        if not is_valid_precise_amount:
            return "precise_amount must be a string or number."
        if _parse_precise_integer(precise_amount) is None:
            return "precise_amount must be a non-negative integer string or number."

    if "meta_data" in data and not is_valid_meta_data(data["meta_data"]):
        return "meta_data must be a valid object if provided"

    if "skip_queue" in data and not isinstance(data["skip_queue"], bool):
        return "skip_queue must be a boolean if provided."

    if "dry_run" in data and not isinstance(data["dry_run"], bool):
        return "dry_run must be a boolean if provided."

    allowed_fields = [
        "status",
        "amount",
        "precise_amount",
        "meta_data",
        "skip_queue",
        "dry_run",
    ]
    for key in data:  # iterates in insertion order
        if key not in allowed_fields:
            return f"Invalid field: {key}"  # note: no trailing period

    return None


def validate_refund_transaction(data: Any) -> Optional[str]:
    """Validates the payload for refunding a transaction. An empty payload
    is valid."""
    data = _dict_view(data)

    if "skip_queue" in data and not isinstance(data["skip_queue"], bool):
        return "skip_queue must be a boolean if provided."

    if "dry_run" in data and not isinstance(data["dry_run"], bool):
        return "dry_run must be a boolean if provided."

    if "description" in data and not isinstance(data["description"], str):
        return "description must be a string if provided."

    if "meta_data" in data and not is_valid_meta_data(data["meta_data"]):
        return "meta_data must be a valid object if provided"

    allowed_fields = ["skip_queue", "dry_run", "description", "meta_data"]
    for key in data:
        if key not in allowed_fields:
            return f"Invalid field: {key}"

    return None


def validate_bulk_void_inflight(data: Any) -> Optional[str]:
    """Validates the payload for bulk-voiding inflight transactions."""
    data = _dict_view(data)

    if "skip_queue" in data and not isinstance(data["skip_queue"], bool):
        return "skip_queue must be a boolean if provided."

    if "dry_run" in data and not isinstance(data["dry_run"], bool):
        return "dry_run must be a boolean if provided."

    transaction_ids = data.get("transaction_ids")
    if not isinstance(transaction_ids, list):
        return "transaction_ids must be an array."

    if len(transaction_ids) == 0:
        return "transaction_ids array cannot be empty."

    if len(transaction_ids) > MAX_BULK_INFLIGHT_ITEMS:
        return f"Too many transaction_ids; max is {MAX_BULK_INFLIGHT_ITEMS}."

    for i, transaction_id in enumerate(transaction_ids):
        if not isinstance(transaction_id, str) or transaction_id.strip() == "":
            return f"transaction_id is required at index {i}."

    allowed_fields = ["skip_queue", "dry_run", "transaction_ids"]
    for key in data:  # unknown fields run LAST
        if key not in allowed_fields:
            return f"Invalid field: {key}"

    return None


def validate_bulk_commit_inflight(data: Any) -> Optional[str]:
    """Validates the payload for bulk-committing inflight transactions.

    A None element inside `transactions` raises AttributeError on field
    access — the endpoint surfaces it as a 500.
    """
    data = _dict_view(data)

    if "skip_queue" in data and not isinstance(data["skip_queue"], bool):
        return "skip_queue must be a boolean if provided."

    if "dry_run" in data and not isinstance(data["dry_run"], bool):
        return "dry_run must be a boolean if provided."

    transactions = data.get("transactions")
    if not isinstance(transactions, list):
        return "Transactions must be an array."

    if len(transactions) == 0:
        return "Transactions array cannot be empty."

    if len(transactions) > MAX_BULK_INFLIGHT_ITEMS:
        return f"Too many transactions; max is {MAX_BULK_INFLIGHT_ITEMS}."

    for i, item in enumerate(transactions):
        transaction_id = item.get("transaction_id")  # raises for None elements
        if not isinstance(transaction_id, str) or transaction_id.strip() == "":
            return f"transaction_id is required at index {i}."

        if "amount" in item and not is_valid_number(item["amount"]):
            return f"amount must be a number at index {i}."  # lowercase, unlike the create message

        precise_amount = item.get("precise_amount")
        if precise_amount is not None:
            is_valid_precise_amount = is_valid_number(precise_amount) or isinstance(
                precise_amount, str
            )
            if not is_valid_precise_amount:
                return f"precise_amount must be a string or number at index {i}."
            if _parse_precise_integer(precise_amount) is None:
                return (
                    "precise_amount must be a non-negative integer string "
                    f"or number at index {i}."
                )

    allowed_fields = ["skip_queue", "dry_run", "transactions"]
    for key in data:  # unknown fields run LAST
        if key not in allowed_fields:
            return f"Invalid field: {key}"

    return None


def validate_bulk_transactions(data: Any) -> Optional[str]:
    """Validates a bulk-transactions payload."""
    data = _dict_view(data)

    if "atomic" in data and not isinstance(data["atomic"], bool):
        return "Atomic must be a boolean if provided."  # capitalized, unlike the create message

    if "inflight" in data and not isinstance(data["inflight"], bool):
        return "Inflight must be a boolean if provided."

    if "run_async" in data and not isinstance(data["run_async"], bool):
        return "Run_async must be a boolean if provided."  # note the capitalization

    if "skip_queue" in data and not isinstance(data["skip_queue"], bool):
        return "skip_queue must be a boolean if provided."

    if "dry_run" in data and not isinstance(data["dry_run"], bool):
        return "dry_run must be a boolean if provided."

    transactions = data.get("transactions")
    if not isinstance(transactions, list):
        return "Transactions must be an array."

    if len(transactions) == 0:
        return "Transactions array cannot be empty."

    if len(transactions) > MAX_BULK_CREATE_ITEMS:
        return f"Too many transactions; max is {MAX_BULK_CREATE_ITEMS}."

    for i, transaction in enumerate(transactions):
        # A primitive element carries no fields, so it fails the per-item
        # checks with a 400 message instead of crashing the validator; None
        # remains a caller error surfaced as a 500 by the endpoint.
        if not isinstance(transaction, dict) and transaction is not None:
            if not callable(getattr(transaction, "to_dict", None)):
                transaction = {}
        validation_error = validate_create_transactions(transaction)
        if validation_error:
            return f"Transaction at index {i}: {validation_error}"

    # References are guaranteed strings by the per-item validation above.
    references = [_dict_view(t).get("reference") for t in transactions]
    if len(references) != len(set(references)):
        return "All transactions must have unique references within the bulk request."

    # No unknown-field check on the wrapper object.
    return None


def validate_recover_queue(data: Any) -> Optional[str]:
    """Validates the payload for recovering the transaction queue."""
    data = _dict_view(data)

    # Unknown fields are checked first here, unlike the other validators.
    allowed_fields = ["threshold"]
    for key in data:
        if key not in allowed_fields:
            return f"Invalid field: {key}"

    if "threshold" not in data:  # an absent threshold is valid
        return None

    threshold = data["threshold"]
    if not isinstance(threshold, str) or not _is_valid_go_duration(threshold):
        return "threshold must be a valid duration string (e.g. 5m, 1h)."

    return None
