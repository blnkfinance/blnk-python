"""Unit tests for `IdentityDataResponse` (1 case, root
`IdentityDataResponse API shape`).

The response DTO is parsed via `from_dict`. Note the nanosecond-precision
`created_at` the response type must tolerate (kept as a plain string, never
parsed)."""

from __future__ import annotations

from blnk_sdk.types.identity import IdentityDataResponse


def test_response_dob_is_a_string() -> None:
    """response dob is a string"""
    response = IdentityDataResponse.from_dict(
        {
            "identity_id": "idt_11111111-1111-4111-8111-111111111111",
            "identity_type": "individual",
            "first_name": "Alice",
            "last_name": "Smith",
            "gender": "female",
            "dob": "1985-05-15T00:00:00Z",
            "email_address": "alice@example.com",
            "phone_number": "+1234567890",
            "nationality": "Canadian",
            "category": "customer",
            "street": "789 Elm St",
            "country": "Canada",
            "state": "Ontario",
            "post_code": "M4B 1B3",
            "city": "Toronto",
            "created_at": "2024-11-26T08:36:36.238244338Z",
            "meta_data": {"customer_id": "CUST123456"},
        }
    )

    assert isinstance(response.dob, str)
    assert response.identity_id.startswith("idt_")
