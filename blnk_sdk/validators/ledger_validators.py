"""Validators for ledger requests.

Validators return `str | None` — None means valid; a non-None value is the
exact error message callers surface. Check order is part of the SDK's
behavior: the first failing check wins. Validators accept both raw dicts
(the canonical dict view) and DTO dataclasses (normalized via to_dict();
None fields become absent keys, i.e. "not provided").
"""

from __future__ import annotations

from typing import Any, Optional

from ..coercion import is_truthy
from ..types import DTO
from .common import is_valid_meta_data


def _dict_view(data: Any) -> Any:
    """Canonical validator input is the dict view."""
    if isinstance(data, DTO):
        return data.to_dict()
    return data


def validate_create_ledger(data: Any) -> Optional[str]:
    """Validates the payload for creating a ledger."""
    data = _dict_view(data)

    # Structured-payload gate: falsy values (None/0/""/False/NaN) and truthy
    # non-objects (str/number/True) are rejected; dicts and lists pass.
    # Note: the message names CreateLedgerBalance; callers depend on this
    # exact string.
    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Data must be a valid object of type CreateLedgerBalance"

    # name only needs to be a string — an empty string passes (create has no
    # emptiness check, unlike update). A list payload has no name field and
    # fails here.
    name = data.get("name") if isinstance(data, dict) else None
    if not isinstance(name, str):
        return "name field must be a valid string"

    # meta_data is optional: an absent key skips the check; a key explicitly
    # present with None fails it. Any structured value — lists included — is
    # valid meta_data.
    if "meta_data" in data and not is_valid_meta_data(data["meta_data"]):
        return "meta_data must be a valid object if provided"

    return None


def validate_update_ledger(data: Any) -> Optional[str]:
    """Validates the payload for updating a ledger."""
    data = _dict_view(data)

    # Structured-payload gate.
    if not is_truthy(data) or not is_valid_meta_data(data):
        return "Data must be a valid object of type UpdateLedger"

    # name must be a string.
    name = data.get("name") if isinstance(data, dict) else None
    if not isinstance(name, str):
        return "name field must be a valid string"

    # Unlike create, update rejects empty and whitespace-only names.
    if name.strip() == "":
        return "name field is required"

    return None
