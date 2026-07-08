"""Unit tests for `validate_tokenize_identity_data`
(1 case, root `ValidateTokenizeIdentityData`)."""

from __future__ import annotations

from blnk_sdk.validators.identity_validators import validate_tokenize_identity_data


def test_validate_tokenize_identity_data() -> None:
    """ValidateTokenizeIdentityData"""
    valid_data = {
        "fields": ["FirstName", "EmailAddress"],
    }

    assert validate_tokenize_identity_data("idt_test_123", valid_data) is None
    assert (
        validate_tokenize_identity_data("", valid_data) == "identity id is required"
    )
    assert (
        validate_tokenize_identity_data("idt_test_123", {"fields": []})
        == "at least one field must be specified"
    )
    assert (
        validate_tokenize_identity_data(
            "idt_test_123",
            {"fields": ["FirstName", ""]},
        )
        == "each field must be a non-empty string"
    )
