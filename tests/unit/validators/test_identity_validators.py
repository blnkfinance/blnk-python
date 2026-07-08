"""Unit tests for `validate_identity` (9 cases, two
groups: `ValidateIdentity identity_id and dob` and `ValidateIdentity
optional fields`)."""

from __future__ import annotations

from datetime import datetime, timezone

from blnk_sdk.validators.identity_validators import validate_identity

BASE_INDIVIDUAL = {
    "identity_type": "individual",
    "first_name": "Jane",
    "last_name": "Doe",
    "gender": "female",
    "dob": "1990-01-15T00:00:00Z",
    "nationality": "US",
    "email_address": "jane@example.com",
    "phone_number": "+1234567890",
    "category": "customer",
    "street": "123 Main St",
    "country": "USA",
    "state": "NY",
    "post_code": "10001",
    "city": "New York",
}


# Root: ValidateIdentity identity_id and dob


def test_accepts_caller_supplied_identity_id() -> None:
    """accepts caller-supplied identity_id"""
    assert (
        validate_identity(
            {
                **BASE_INDIVIDUAL,
                "identity_id": "idt_11111111-1111-4111-8111-111111111111",
            }
        )
        is None
    )


def test_accepts_iso_dob_string() -> None:
    """accepts ISO dob string"""
    assert validate_identity(BASE_INDIVIDUAL) is None


def test_accepts_date_dob() -> None:
    """accepts datetime dob"""
    assert (
        validate_identity(
            {
                **BASE_INDIVIDUAL,
                "dob": datetime(1990, 1, 15, tzinfo=timezone.utc),
            }
        )
        is None
    )


def test_rejects_invalid_identity_id() -> None:
    """rejects invalid identity_id"""
    assert (
        validate_identity(
            {
                **BASE_INDIVIDUAL,
                "identity_id": "user_123",
            }
        )
        == "identity_id must start with idt_ followed by a valid UUID"
    )


def test_rejects_invalid_dob_string() -> None:
    """rejects invalid dob string"""
    # Note: the message text says "Date" although the accepted type is
    # datetime; callers depend on this exact string.
    assert (
        validate_identity(
            {
                **BASE_INDIVIDUAL,
                "dob": "not-a-date",
            }
        )
        == "dob must be a valid ISO 8601 date string or Date"
    )


# Root: ValidateIdentity optional fields


def test_accepts_minimal_individual_payload() -> None:
    """accepts minimal individual payload"""
    assert (
        validate_identity(
            {
                "identity_type": "individual",
            }
        )
        is None
    )


def test_accepts_minimal_organization_payload() -> None:
    """accepts minimal organization payload"""
    assert (
        validate_identity(
            {
                "identity_type": "organization",
            }
        )
        is None
    )


def test_rejects_invalid_identity_type() -> None:
    """rejects invalid identity_type"""
    assert (
        validate_identity(
            {
                "identity_type": "business",
            }
        )
        == "identity_type must be individual or organization"
    )


def test_rejects_invalid_gender_when_provided() -> None:
    """rejects invalid gender when provided"""
    assert (
        validate_identity(
            {
                **BASE_INDIVIDUAL,
                "gender": "unknown",
            }
        )
        == "gender must be male, female, or other if provided"
    )
