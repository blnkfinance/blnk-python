"""Unit tests for `validate_tokenize_identity_field`
(1 case, root `ValidateTokenizeIdentityField`)."""

from __future__ import annotations

from blnk_sdk.validators.identity_validators import validate_tokenize_identity_field


def test_validate_tokenize_identity_field() -> None:
    """ValidateTokenizeIdentityField"""
    assert validate_tokenize_identity_field("idt_test_123", "FirstName") is None
    assert (
        validate_tokenize_identity_field("", "FirstName")
        == "identity id is required"
    )
    assert (
        validate_tokenize_identity_field("idt_test_123", "")
        == "field name is required"
    )
