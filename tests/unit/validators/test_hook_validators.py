"""Unit tests for the hook validators (13 cases:
`ValidateCreateHookData`, `ValidateListHooksOptions`, `ValidateUpdateHookData`).

Case names repeat across validators (`accepts valid payload`, `rejects
invalid type`), so test functions are prefixed with the validator under
test; the short case name is kept in each docstring. Error messages are
asserted as exact full strings; omitted options are passed as None.
"""

from __future__ import annotations

from blnk_sdk.validators.hook_validators import (
    validate_create_hook_data,
    validate_list_hooks_options,
    validate_update_hook_data,
)

VALID_DATA = {
    "name": "Pre-transaction validation",
    "url": "https://api.example.com/validate",
    "type": "PRE_TRANSACTION",
    "active": True,
    "timeout": 30,
    "retry_count": 3,
}


# --------------------------------------------------------------------------- #
# ValidateCreateHookData


def test_validate_create_hook_data_accepts_valid_payload() -> None:
    """accepts valid payload"""
    assert validate_create_hook_data(VALID_DATA) is None


def test_validate_create_hook_data_rejects_empty_name() -> None:
    """rejects empty name"""
    assert (
        validate_create_hook_data({**VALID_DATA, "name": ""}) == "name is required"
    )


def test_validate_create_hook_data_rejects_empty_url() -> None:
    """rejects empty url"""
    assert validate_create_hook_data({**VALID_DATA, "url": ""}) == "url is required"


def test_validate_create_hook_data_rejects_invalid_type() -> None:
    """rejects invalid type"""
    assert (
        validate_create_hook_data({**VALID_DATA, "type": "INVALID"})
        == "type must be PRE_TRANSACTION or POST_TRANSACTION"
    )


def test_validate_create_hook_data_rejects_non_boolean_active() -> None:
    """rejects non-boolean active"""
    assert (
        validate_create_hook_data({**VALID_DATA, "active": "true"})
        == "active must be a boolean"
    )


def test_validate_create_hook_data_rejects_non_positive_timeout() -> None:
    """rejects non-positive timeout"""
    assert (
        validate_create_hook_data({**VALID_DATA, "timeout": 0})
        == "timeout must be a positive number"
    )


def test_validate_create_hook_data_rejects_negative_retry_count() -> None:
    """rejects negative retry_count"""
    assert (
        validate_create_hook_data({**VALID_DATA, "retry_count": -1})
        == "retry_count must be a non-negative number"
    )


# --------------------------------------------------------------------------- #
# ValidateListHooksOptions


def test_validate_list_hooks_options_accepts_omitted_options() -> None:
    """accepts omitted options"""
    assert validate_list_hooks_options(None) is None


def test_validate_list_hooks_options_accepts_empty_options() -> None:
    """accepts empty options"""
    assert validate_list_hooks_options({}) is None


def test_validate_list_hooks_options_accepts_valid_type() -> None:
    """accepts valid type"""
    assert validate_list_hooks_options({"type": "PRE_TRANSACTION"}) is None


def test_validate_list_hooks_options_rejects_invalid_type() -> None:
    """rejects invalid type"""
    assert (
        validate_list_hooks_options({"type": "INVALID"})
        == "type must be PRE_TRANSACTION or POST_TRANSACTION"
    )


# --------------------------------------------------------------------------- #
# ValidateUpdateHookData


def test_validate_update_hook_data_accepts_valid_payload() -> None:
    """accepts valid payload"""
    assert validate_update_hook_data(VALID_DATA) is None


def test_validate_update_hook_data_rejects_invalid_type() -> None:
    """rejects invalid type"""
    assert (
        validate_update_hook_data({**VALID_DATA, "type": "INVALID"})
        == "type must be PRE_TRANSACTION or POST_TRANSACTION"
    )
