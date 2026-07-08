"""Value-coercion helpers shared by the core client and the validators.

Provides:
- is_truthy: the SDK's truthiness rule (NaN and "" are falsy; empty
  dicts/lists are TRUTHY).
- format_number: renders a number the way it appears in SDK messages.

`isinstance(True, int)` is True in Python — every numeric check here excludes
bool explicitly so booleans are never treated as numbers.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any


def is_truthy(value: Any) -> bool:
    """The truthiness rule used throughout the SDK.

    Falsy: None, False, 0/-0.0, NaN, and the empty string. Empty dicts, lists,
    and other objects are TRUTHY (note: this differs from Python's built-in
    bool()).
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return False
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    return True


def format_number(value: Any) -> str:
    """Render a number the way it appears in SDK messages and logs.

    Integral finite values < 1e21 render without a decimal point ("100", not
    "100.0"); very large or very small magnitudes use exponential notation
    ("1e+21", "1.5e-7"); NaN and the infinities render as
    "NaN"/"Infinity"/"-Infinity". Callers depend on these exact renderings in
    message text (e.g. timeout messages).
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)

    f = float(value)
    if math.isnan(f):
        return "NaN"
    if math.isinf(f):
        return "Infinity" if f > 0 else "-Infinity"
    if f == 0:
        return "0"  # Negative zero also renders as "0".
    if f < 0:
        return "-" + format_number(-f)

    # Positive finite non-zero. repr() gives the shortest round-trip digits.
    _sign, digit_tuple, exponent = Decimal(repr(f)).as_tuple()
    digits = "".join(map(str, digit_tuple))
    stripped = digits.rstrip("0")
    exponent += len(digits) - len(stripped)
    digits = stripped

    k = len(digits)
    n = k + exponent  # value = 0.digits * 10^n

    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + digits
    e = n - 1
    exp_str = ("+" if e >= 0 else "-") + str(abs(e))
    if k == 1:
        return digits + "e" + exp_str
    return digits[0] + "." + digits[1:] + "e" + exp_str
