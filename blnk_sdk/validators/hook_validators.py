"""Validators for webhook requests.

Pure functions returning the exact error message string on failure, or None
when valid; the first failing check wins. No logging, no HTTP, no payload
mutation.
"""

from __future__ import annotations

from typing import Any, Optional

from ..string_utils import is_valid_number, is_valid_string
from ..types import DTO

__all__ = [
    "validate_create_hook_data",
    "validate_list_hooks_options",
    "validate_update_hook_data",
]


def _is_valid_hook_type(type: Any) -> bool:
    """Exact, case-sensitive membership in the two supported hook types;
    lowercase or padded variants are invalid."""
    return type in ["PRE_TRANSACTION", "POST_TRANSACTION"]


def _prop(obj: Any, name: str) -> Any:
    """Reads a field from a validated payload view: dict lookup, where an
    absent key reads as None ("not provided"); list payloads have no named
    fields, so every lookup reads as None."""
    if isinstance(obj, dict):
        return obj.get(name)
    return None


def validate_create_hook_data(data: Any) -> Optional[str]:
    """Validates the payload for creating a hook."""
    # Structured-payload gate: dicts and lists both pass; DTOs pass via their
    # dict view; falsy values (None/""/0/False/NaN) and truthy non-objects
    # (str/number/True) fail.
    d: Any = data
    if not isinstance(d, (dict, list)):
        if isinstance(d, DTO):
            d = d.to_dict()
        else:
            return "Data must be a valid object of type CreateHookData"

    # Emptiness is checked without trimming — a whitespace-only name passes.
    name = _prop(d, "name")
    if not is_valid_string(name) or name == "":
        return "name is required"

    url = _prop(d, "url")
    if not is_valid_string(url) or url == "":
        return "url is required"

    hook_type = _prop(d, "type")
    if not is_valid_string(hook_type) or not _is_valid_hook_type(hook_type):
        return "type must be PRE_TRANSACTION or POST_TRANSACTION"

    # active must be a real boolean; truthy stand-ins are rejected.
    active = _prop(d, "active")
    if not isinstance(active, bool):
        return "active must be a boolean"

    # Note the comparison direction: NaN passes (NaN <= 0 is false), infinity
    # passes; 0 and negatives fail.
    timeout = _prop(d, "timeout")
    if not is_valid_number(timeout) or timeout <= 0:
        return "timeout must be a positive number"

    # NaN passes (NaN < 0 is false); 0 and infinity pass; negatives fail.
    retry_count = _prop(d, "retry_count")
    if not is_valid_number(retry_count) or retry_count < 0:
        return "retry_count must be a non-negative number"

    return None


def validate_update_hook_data(data: Any) -> Optional[str]:
    """Validates the payload for updating a hook.

    Delegates to validate_create_hook_data. Note: an invalid update payload
    yields the message naming CreateHookData; callers depend on this exact
    string.
    """
    return validate_create_hook_data(data)


def validate_list_hooks_options(options: Any = None) -> Optional[str]:
    """Validates optional list-hooks options.

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

    # An absent "type" key means "not provided" and skips the check; a key
    # explicitly present with None is checked and fails. List payloads have
    # no "type" field and validate.
    if isinstance(o, dict) and "type" in o:
        hook_type = o["type"]
        if not is_valid_string(hook_type) or not _is_valid_hook_type(hook_type):
            return "type must be PRE_TRANSACTION or POST_TRANSACTION"

    return None
