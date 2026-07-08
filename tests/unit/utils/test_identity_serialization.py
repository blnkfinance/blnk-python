"""Unit tests for `serialize_identity_data` (3 cases,
root `serializeIdentityData`)."""

from __future__ import annotations

from datetime import datetime, timezone

from blnk_sdk.identity_serialization import serialize_identity_data

BASE_INDIVIDUAL = {
    "identity_type": "individual",
    "first_name": "Jane",
    "last_name": "Doe",
    "gender": "female",
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


def test_passes_through_iso_dob_string() -> None:
    """passes through ISO dob string"""
    data = {
        **BASE_INDIVIDUAL,
        "dob": "1990-01-15T00:00:00Z",
    }
    payload = serialize_identity_data(data)
    assert payload["dob"] == "1990-01-15T00:00:00Z"


def test_serializes_date_dob_to_iso_string_without_milliseconds() -> None:
    """serializes datetime dob to an ISO string without fractional seconds"""
    data = {
        **BASE_INDIVIDUAL,
        "dob": datetime(1990, 1, 15, tzinfo=timezone.utc),
    }
    payload = serialize_identity_data(data)
    assert payload["dob"] == "1990-01-15T00:00:00Z"


def test_forwards_optional_identity_id() -> None:
    """forwards optional identity_id"""
    data = {
        **BASE_INDIVIDUAL,
        "identity_id": "idt_11111111-1111-4111-8111-111111111111",
        "dob": "1990-01-15T00:00:00Z",
    }
    payload = serialize_identity_data(data)
    assert payload["identity_id"] == "idt_11111111-1111-4111-8111-111111111111"
