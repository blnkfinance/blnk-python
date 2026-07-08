"""String and value validation helpers shared by the service validators."""

from __future__ import annotations

from typing import Any

# Comparison operators accepted by balance-monitor conditions.
OPERATION_TYPES = ("!=", "<", "<=", "=", ">", ">=")


def is_valid_string(val: Any) -> bool:
    """True for any str — the empty string PASSES."""
    return isinstance(val, str)


def is_valid_number(val: Any) -> bool:
    """True for numeric values — NaN and the infinities deliberately PASS.

    bool is explicitly excluded even though it subclasses int; booleans are
    never valid where a number is required.
    """
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def is_valid_array(val: Any) -> bool:
    """True only for lists — tuples and other sequences do not qualify."""
    return isinstance(val, list)


def is_valid_operator(val: Any) -> bool:
    return val in OPERATION_TYPES
