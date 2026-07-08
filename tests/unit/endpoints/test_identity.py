"""Unit tests for Identity.create: request shapes, minimal payloads,
identity_id validation, dob serialization, and error forwarding."""

from __future__ import annotations

from datetime import datetime, timezone

from blnk_sdk.http_client import format_response
from blnk_sdk.services.identity import Identity
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest


def _captured(captured_request: CapturingRequest) -> list:
    return [call[:3] for call in captured_request.calls]


def test_create_organization_identity() -> None:
    """Create Organization Identity"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    data = {
        "category": "test",
        "identity_type": "organization",
        "city": "test",
        "country": "test",
        "email_address": "test@test.com",
        "organization_name": "test org",
        "state": "test",
        "post_code": "test",
        "street": "test",
        "phone_number": "1234567890",
    }

    response = identity.create(data)
    assert _captured(captured_request) == [("identities", data, "POST")]
    assert response.status == 201
    assert response.data["identity_type"] == data["identity_type"]


def test_create_accepts_minimal_organization_payload() -> None:
    """create accepts minimal organization payload"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)
    data = {
        "identity_type": "organization",
    }

    response = identity.create(data)
    assert _captured(captured_request) == [("identities", data, "POST")]
    assert response.status == 201


def test_create_accepts_minimal_individual_payload() -> None:
    """create accepts minimal individual payload"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)
    data = {
        "identity_type": "individual",
    }

    response = identity.create(data)
    assert _captured(captured_request) == [("identities", data, "POST")]
    assert response.status == 201


def test_it_should_handle_errors_thrown_during_creation() -> None:
    """it should handle errors thrown during creation"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(False, "Error creating identity", 500)
    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    data = {
        "category": "test",
        "identity_type": "organization",
        "city": "test",
        "country": "test",
        "email_address": "test@test.com",
        "organization_name": "test org",
        "state": "test",
        "post_code": "test",
        "street": "test",
        "phone_number": "1234567890",
    }

    response = identity.create(data)
    assert _captured(captured_request) == [("identities", data, "POST")]
    assert response.status == 500
    assert response.data is None


def test_create_forwards_identity_id_and_iso_dob() -> None:
    """create forwards identity_id and ISO dob"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    data = {
        "identity_id": "idt_11111111-1111-4111-8111-111111111111",
        "category": "customer",
        "identity_type": "individual",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": "female",
        "dob": "1990-01-15T00:00:00Z",
        "nationality": "US",
        "city": "New York",
        "country": "USA",
        "email_address": "jane@example.com",
        "state": "NY",
        "post_code": "10001",
        "street": "123 Main St",
        "phone_number": "1234567890",
    }

    identity.create(data)

    assert _captured(captured_request) == [
        (
            "identities",
            {
                **data,
                "dob": "1990-01-15T00:00:00Z",
            },
            "POST",
        ),
    ]


def test_create_serializes_date_dob() -> None:
    """create serializes Date dob"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    data = {
        "category": "customer",
        "identity_type": "individual",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": "female",
        "dob": datetime(1990, 1, 15, tzinfo=timezone.utc),
        "nationality": "US",
        "city": "New York",
        "country": "USA",
        "email_address": "jane@example.com",
        "state": "NY",
        "post_code": "10001",
        "street": "123 Main St",
        "phone_number": "1234567890",
    }

    identity.create(data)

    assert _captured(captured_request) == [
        (
            "identities",
            {
                **data,
                "dob": "1990-01-15T00:00:00Z",
            },
            "POST",
        ),
    ]


def test_create_rejects_invalid_identity_id() -> None:
    """create rejects invalid identity_id"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    data = {
        "identity_id": "user_123",
        "category": "customer",
        "identity_type": "individual",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": "female",
        "dob": "1990-01-15T00:00:00Z",
        "nationality": "US",
        "city": "New York",
        "country": "USA",
        "email_address": "jane@example.com",
        "state": "NY",
        "post_code": "10001",
        "street": "123 Main St",
        "phone_number": "1234567890",
    }

    response = identity.create(data)

    assert _captured(captured_request) == []
    assert response.status == 400
    assert response.message == "identity_id must start with idt_ followed by a valid UUID"
