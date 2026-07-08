"""Unit tests for `validate_identity_id` (1 case,
root `ValidateIdentityId`)."""

from __future__ import annotations

from blnk_sdk.validators.identity_validators import validate_identity_id


def test_validate_identity_id() -> None:
    """ValidateIdentityId"""
    assert validate_identity_id("idt_test_123") is None
    assert validate_identity_id("") == "identity id is required"
