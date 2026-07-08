"""Validators for API-key requests.

Pure functions returning the exact error message string on failure, or None
when valid; the first failing check wins. No logging, no HTTP, no payload
mutation.
"""

from __future__ import annotations

from typing import Any, Optional

from ..serialization import is_valid_transaction_date_input
from ..string_utils import is_valid_array, is_valid_string
from ..types import DTO

__all__ = [
    "validate_create_api_key_data",
    "validate_delete_api_key_options",
    "validate_list_api_keys_options",
]


def _prop(obj: Any, name: str) -> Any:
    """Reads a field from a validated payload view: dict lookup, where an
    absent key reads as None ("not provided"); list payloads have no named
    fields, so every lookup reads as None."""
    if isinstance(obj, dict):
        return obj.get(name)
    return None


def validate_create_api_key_data(data: Any) -> Optional[str]:
    """Validates the payload for creating an API key."""
    # Structured-payload gate: dicts and lists both pass; DTOs pass via their
    # dict view; falsy values (None/""/0/False/NaN) and truthy non-objects
    # (str/number/True) fail.
    d: Any = data
    if not isinstance(d, (dict, list)):
        if isinstance(d, DTO):
            d = d.to_dict()
        else:
            return "Data must be a valid object of type CreateApiKeyData"

    # Emptiness is checked without trimming — a whitespace-only name passes.
    name = _prop(d, "name")
    if not is_valid_string(name) or name == "":
        return "name is required"

    owner = _prop(d, "owner")
    if not is_valid_string(owner) or owner == "":
        return "owner is required"

    scopes = _prop(d, "scopes")
    if not is_valid_array(scopes) or len(scopes) == 0:
        return "at least one scope must be specified"

    # Per-element, in array order — first offending element wins.
    for scope in scopes:
        if not is_valid_string(scope) or scope == "":
            return "each scope must be a non-empty string"

    # Note: the message says "ISO 8601", but only RFC 3339 date-times without
    # fractional seconds validate. The value is trimmed for validation only —
    # the original, untrimmed string is what goes to the wire. (datetime
    # inputs never reach the date check: the string check rejects them first.)
    expires_at = _prop(d, "expires_at")
    if not is_valid_string(expires_at) or not is_valid_transaction_date_input(
        expires_at
    ):
        return "expires_at must be a valid ISO 8601 datetime string"

    return None


def validate_list_api_keys_options(options: Any = None) -> Optional[str]:
    """Validates optional list-API-keys options.

    Passing None (or omitting the argument) means "no options" and is always
    valid.
    """
    if options is None:
        return None

    o: Any = options
    if not isinstance(o, (dict, list)):
        if isinstance(o, DTO):
            o = o.to_dict()
        else:
            return "options must be a valid object"

    # An absent "owner" key means "not provided" and skips the check; a key
    # explicitly present with None is checked and fails. No trimming — a
    # whitespace-only owner is accepted. List payloads have no "owner" field
    # and validate.
    if isinstance(o, dict) and "owner" in o:
        owner = o["owner"]
        if not is_valid_string(owner) or owner == "":
            return "owner must be a non-empty string"

    return None


def validate_delete_api_key_options(options: Any = None) -> Optional[str]:
    """Validates optional delete-API-key options.

    Delegates to validate_list_api_keys_options — invalid delete options
    intentionally produce the same generic messages as the list validator.
    """
    return validate_list_api_keys_options(options)
