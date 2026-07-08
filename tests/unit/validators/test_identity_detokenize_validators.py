"""Unit tests for `validate_detokenize_identity_data`
(1 case, root `ValidateDetokenizeIdentityData`)."""

from __future__ import annotations

from blnk_sdk.validators.identity_validators import validate_detokenize_identity_data


def test_validate_detokenize_identity_data() -> None:
    """ValidateDetokenizeIdentityData"""
    valid_data = {
        "fields": ["FirstName", "EmailAddress"],
    }

    assert validate_detokenize_identity_data("idt_test_123", valid_data) is None
    assert validate_detokenize_identity_data("idt_test_123", {"fields": []}) is None
    assert (
        validate_detokenize_identity_data("", valid_data) == "identity id is required"
    )
    assert (
        validate_detokenize_identity_data(
            "idt_test_123",
            {"fields": ["FirstName", ""]},
        )
        == "each field must be a non-empty string"
    )
