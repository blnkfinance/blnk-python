"""Validators for identity requests.

Pure, synchronous validators: each returns the exact error message string on
failure, or None when valid; the first failing check wins. Validators accept
both raw dicts and DTOs (validation runs on the dict view; for the optional
fields here, an absent key and an explicit None both mean "not provided").
"""

from __future__ import annotations

import re
from typing import Any, Optional

from ..identity_serialization import is_valid_identity_date_input
from ..coercion import is_truthy
from ..string_utils import is_valid_array, is_valid_string
from .common import is_valid_meta_data

# Case-insensitive: an uppercase `IDT_` prefix and uppercase hex digits are
# accepted.
IDENTITY_ID_PATTERN = re.compile(
    r"^idt_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VALID_GENDERS = ("male", "female", "other")


def _dict_view(data: Any) -> Any:
    """Canonical validator input is the dict view (DTO.to_dict() omits
    None-valued fields, so None optionals read as absent)."""
    if isinstance(data, dict):
        return data
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return data


def _is_structured_value(value: Any) -> bool:
    """Structured-value check for the reachable input space: dicts, lists and
    DTO instances pass; str/number/bool primitives fail. (None never reaches
    this check — the preceding truthiness guard rejects it first.)"""
    return not isinstance(value, (str, int, float, bool))


def _fields_of(data: Any) -> Any:
    """Reads the `fields` entry: an absent key reads as None, so a list
    passed as `data` yields None here and then fails the array check."""
    if isinstance(data, dict):
        return data.get("fields")
    return getattr(data, "fields", None)


def validate_identity(data: Any) -> Optional[str]:
    """Validates identity data for `create` and `update`.

    Optional fields are only checked when present with a non-None value on
    the dict view; an absent key or an explicit None both mean "not
    provided"."""
    view = _dict_view(data)

    # 1. Strict, case-sensitive string equality. Absent/None identity_type
    #    also fails here (it equals neither literal).
    identity_type = view.get("identity_type")
    if identity_type != "individual" and identity_type != "organization":
        return "identity_type must be individual or organization"

    # 2. Case-insensitive, full-string anchored regex. Non-string values fail
    #    with the same message.
    identity_id = view.get("identity_id")
    if identity_id is not None and (
        not isinstance(identity_id, str)
        or not IDENTITY_ID_PATTERN.fullmatch(identity_id)
    ):
        return "identity_id must start with idt_ followed by a valid UUID"

    # 3. Note: the message says "ISO 8601", but only full RFC 3339 date-times
    #    without fractional seconds validate (date-only strings are rejected;
    #    datetime objects are always accepted).
    dob = view.get("dob")
    if dob is not None and not is_valid_identity_date_input(dob):
        return "dob must be a valid ISO 8601 date string or Date"

    # 4. Exact-membership, case-sensitive.
    gender = view.get("gender")
    if gender is not None and gender not in VALID_GENDERS:
        return "gender must be male, female, or other if provided"

    # 5. is_valid_meta_data accepts lists as well as dicts.
    meta_data = view.get("meta_data")
    if meta_data is not None and not is_valid_meta_data(meta_data):
        return "meta_data must be a valid object if provided"

    return None


def validate_identity_id(id: Any) -> Optional[str]:
    """Validates an identity id. Used by `delete`, `get_tokenized_fields`,
    and as step 1 of the tokenize/detokenize validators.

    Only the type and emptiness are checked — whitespace-only ids pass, and
    IDENTITY_ID_PATTERN is not applied here (any non-empty string is
    accepted as a path id)."""
    if not is_valid_string(id) or id == "":
        return "identity id is required"

    return None


def validate_tokenize_identity_field(id: Any, field: Any) -> Optional[str]:
    """Validates a tokenize/detokenize field request. Used by
    `tokenize_field` and `detokenize_field`. The field value is not checked
    against the list of tokenizable identity fields, and whitespace-only
    field names pass."""
    id_error = validate_identity_id(id)
    if id_error:
        return id_error

    if not is_valid_string(field) or len(field) == 0:
        return "field name is required"

    return None


def validate_detokenize_identity_data(id: Any, data: Any) -> Optional[str]:
    """Validates detokenize request data. Used by `detokenize`. An empty
    fields array is allowed (detokenize-all semantics)."""
    id_error = validate_identity_id(id)
    if id_error:
        return id_error

    # A falsy or non-structured payload is rejected before any field checks.
    if not is_truthy(data) or not _is_structured_value(data):
        return "Data must be a valid object of type DetokenizeIdentityData"

    fields = _fields_of(data)
    if not is_valid_array(fields):
        return "fields must be an array"

    for field in fields:
        if not is_valid_string(field) or len(field) == 0:
            return "each field must be a non-empty string"

    return None


def validate_tokenize_identity_data(id: Any, data: Any) -> Optional[str]:
    """Validates tokenize request data. Used by `tokenize`.

    Unlike the detokenize validator there is no separate "fields must be an
    array" branch — a non-array `fields` also yields "at least one field
    must be specified"."""
    id_error = validate_identity_id(id)
    if id_error:
        return id_error

    if not is_truthy(data) or not _is_structured_value(data):
        return "Data must be a valid object of type TokenizeIdentityData"

    fields = _fields_of(data)
    if not is_valid_array(fields) or len(fields) == 0:
        return "at least one field must be specified"

    for field in fields:
        if not is_valid_string(field) or len(field) == 0:
            return "each field must be a non-empty string"

    return None
