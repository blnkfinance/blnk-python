"""Unit tests for the API-key validators (3 cases:
`ValidateCreateApiKeyData`, `ValidateListApiKeysOptions`,
`ValidateDeleteApiKeyOptions`).

Each test function covers one validator, running its assertions in order.
Error messages are asserted as exact full strings; omitted options are
passed as None.
"""

from __future__ import annotations

from blnk_sdk.validators.api_key_validators import (
    validate_create_api_key_data,
    validate_delete_api_key_options,
    validate_list_api_keys_options,
)


def test_validate_create_api_key_data() -> None:
    """ValidateCreateApiKeyData"""
    valid_data = {
        "name": "Service Account",
        "owner": "merchant_a",
        "scopes": ["ledgers:read"],
        "expires_at": "2026-03-11T00:00:00Z",
    }

    assert validate_create_api_key_data(valid_data) is None
    assert (
        validate_create_api_key_data({**valid_data, "name": ""})
        == "name is required"
    )
    assert (
        validate_create_api_key_data({**valid_data, "owner": ""})
        == "owner is required"
    )
    assert (
        validate_create_api_key_data({**valid_data, "scopes": []})
        == "at least one scope must be specified"
    )
    assert (
        validate_create_api_key_data({**valid_data, "scopes": ["ledgers:read", ""]})
        == "each scope must be a non-empty string"
    )
    assert (
        validate_create_api_key_data({**valid_data, "expires_at": "not-a-date"})
        == "expires_at must be a valid ISO 8601 datetime string"
    )


def test_validate_list_api_keys_options() -> None:
    """ValidateListApiKeysOptions"""
    assert validate_list_api_keys_options(None) is None
    assert validate_list_api_keys_options({}) is None
    assert validate_list_api_keys_options({"owner": "merchant_a"}) is None
    assert (
        validate_list_api_keys_options({"owner": ""})
        == "owner must be a non-empty string"
    )


def test_validate_delete_api_key_options() -> None:
    """ValidateDeleteApiKeyOptions"""
    assert validate_delete_api_key_options(None) is None
    assert validate_delete_api_key_options({"owner": "merchant_a"}) is None
    assert (
        validate_delete_api_key_options({"owner": ""})
        == "owner must be a non-empty string"
    )
