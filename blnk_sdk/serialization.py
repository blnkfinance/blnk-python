"""Shared serialization helpers.

RFC3339 date validation, the stripped-milliseconds UTC date serializer used by
the transactions, identity, hooks, and api-keys services, and the JSON dumper
used for every request body.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Optional, Union

# Matches the timestamp layout Blnk Core parses
# (`2006-01-02T15:04:05Z07:00`): RFC3339 without fractional seconds.
# Offsets may be `+HH:MM` or `+HHMM`; a bare `+HH` is rejected.
RFC3339_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}(?::\d{2}|\d{2}))$"
)

_OFFSET_NO_COLON = re.compile(r"([+-]\d{2})(\d{2})$")

_OFFSET_MINUTES = re.compile(r"[+-]\d{2}:(\d{2})$")

TransactionDateInput = Union[datetime, str]


def _parse_rfc3339(trimmed: str) -> Optional[datetime]:
    """Strict parse of an RFC3339 string that already matched RFC3339_DATETIME.

    Returns None for calendar-impossible dates (Feb 30 etc.) that the regex
    alone cannot reject, and for timezone offsets whose minute component is
    out of range (``fromisoformat`` would silently normalize ``+00:60`` to
    ``+01:00``).
    """
    normalized = trimmed
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    else:
        normalized = _OFFSET_NO_COLON.sub(r"\1:\2", normalized)
    offset_minutes = _OFFSET_MINUTES.search(normalized)
    if offset_minutes and int(offset_minutes.group(1)) > 59:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def is_valid_transaction_date_input(value: Any) -> bool:
    """Validate a transaction date input.

    - datetime values are always accepted.
    - Strings are trimmed; empty strings fail; the rest must match
      RFC3339_DATETIME and parse to a real calendar date.
    - Anything else fails.
    """
    if isinstance(value, datetime):
        return True
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed == "":
            return False
        if not RFC3339_DATETIME.match(trimmed):
            return False
        return _parse_rfc3339(trimmed) is not None
    return False


def to_utc_iso_no_millis(value: datetime) -> str:
    """UTC ISO-8601 with fractional seconds ALWAYS STRIPPED (truncated, never
    rounded): `YYYY-MM-DDTHH:mm:ssZ` — the timestamp format Blnk Core expects.

    Naive datetimes are treated as LOCAL time, then converted to UTC.
    """
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def serialize_transaction_date(value: Any) -> Any:
    """Serialize a date field value: None stays None; a datetime becomes a
    stripped-milliseconds UTC ISO string; strings (and anything else) pass
    through unchanged."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return to_utc_iso_no_millis(value)
    return value


def datetime_to_utc_iso(value: datetime) -> str:
    """UTC ISO-8601 with EXACTLY three fractional digits (milliseconds).

    Used only when a raw datetime appears inside an arbitrary payload value
    handed to compact_json_dumps; dedicated date FIELDS use
    serialize_transaction_date instead.
    """
    d = value.astimezone(timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def _jsonable(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None  # NaN/Infinity are not valid JSON; serialize as null.
    if isinstance(value, datetime):
        return datetime_to_utc_iso(value)
    if isinstance(value, dict):
        return {key: _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict) and not isinstance(value, type):
        return _jsonable(to_dict())
    return value


def compact_json_dumps(value: Any) -> str:
    """Serialize a request body to compact JSON: no whitespace around
    separators, insertion key order, non-ASCII kept verbatim, NaN/Infinity ->
    null, datetimes -> millisecond-precision UTC ISO strings."""
    return json.dumps(_jsonable(value), separators=(",", ":"), ensure_ascii=False)
