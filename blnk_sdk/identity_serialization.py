"""Identity payload serialization.

Built on blnk_sdk.serialization (the shared date helpers):
`is_valid_identity_date_input` delegates to `is_valid_transaction_date_input`,
and `serialize_identity_data` returns a shallow copy with ONLY `dob`
transformed via `serialize_transaction_date`.
"""

from __future__ import annotations

from typing import Any, Dict

from .serialization import (
    is_valid_transaction_date_input,
    serialize_transaction_date,
)


def is_valid_identity_date_input(value: Any) -> bool:
    """Delegates to the shared transaction-date validity algorithm
    (datetime -> True; string -> trim + RFC3339_DATETIME regex + strict
    calendar parse; anything else -> False)."""
    return is_valid_transaction_date_input(value)


def serialize_identity_data(data: Any) -> Dict[str, Any]:
    """Identity payload serializer applied by `create` and `update` ONLY.

    Returns a shallow copy of the payload with `dob` as the ONLY transformed
    field; everything else (including meta_data) is copied through untouched.

    - An absent (None) dob is simply OMITTED from the dict — the key must
      not be sent as null.
    - datetime dob -> UTC `YYYY-MM-DDTHH:mm:ssZ`, milliseconds ALWAYS STRIPPED
      (truncated, never rounded).
    - A string dob passes through BYTE-FOR-BYTE — no trimming or
      re-formatting (validation trims before matching, serialization does not).

    Accepts a raw dict or an IdentityData DTO; always returns the wire dict.
    """
    if isinstance(data, dict):
        payload: Dict[str, Any] = dict(data)
    else:
        to_dict = getattr(data, "to_dict", None)
        payload = to_dict() if callable(to_dict) else dict(data)

    dob = serialize_transaction_date(payload.get("dob"))
    if dob is None:
        payload.pop("dob", None)
    else:
        payload["dob"] = dob
    return payload
