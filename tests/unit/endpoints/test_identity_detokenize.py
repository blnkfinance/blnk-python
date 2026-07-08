"""Unit tests for Identity.detokenize: request shape, empty-fields
behavior, validation failures, and error forwarding."""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.identity import Identity
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

VALID_DATA = {"fields": ["FirstName", "EmailAddress"]}

MOCK_RESPONSE = {
    "fields": {
        "FirstName": "Jane",
        "EmailAddress": "jane@example.com",
    },
}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)


def _captured(captured_request: CapturingRequest) -> list:
    return [call[:3] for call in captured_request.calls]


def test_detokenize_posts_identities_id_detokenize() -> None:
    """detokenize POSTs identities/{id}/detokenize"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize("idt_test_123", VALID_DATA)

    assert _captured(captured_request) == [
        ("identities/idt_test_123/detokenize", VALID_DATA, "POST"),
    ]
    assert response.status == 200
    assert response.data["fields"]["FirstName"] == "Jane"
    assert response.data["fields"]["EmailAddress"] == "jane@example.com"


def test_detokenize_allows_empty_fields_to_detokenize_all() -> None:
    """detokenize allows empty fields to detokenize all"""
    mock_logger = create_mock_logger()
    empty_fields_data = {"fields": []}
    all_fields_response = {
        "fields": {
            "FirstName": "Jane",
            "EmailAddress": "jane@example.com",
            "PhoneNumber": "+1234567890",
        },
    }

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=200, message="Success", data=all_fields_response)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize("idt_test_123", empty_fields_data)

    assert _captured(captured_request) == [
        ("identities/idt_test_123/detokenize", empty_fields_data, "POST"),
    ]
    assert response.status == 200
    assert len((response.data or {}).get("fields", {})) == 3


def test_detokenize_rejects_empty_identity_id() -> None:
    """detokenize rejects empty identity id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize("", VALID_DATA)

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "identity id is required"


def test_detokenize_rejects_blank_field_names() -> None:
    """detokenize rejects blank field names"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize("idt_test_123", {"fields": ["FirstName", ""]})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "each field must be a non-empty string"


def test_detokenize_forwards_api_errors() -> None:
    """detokenize forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=400, message="Field is not tokenized", data=None)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize("idt_test_123", {"fields": ["Street"]})

    assert _captured(captured_request) == [
        ("identities/idt_test_123/detokenize", {"fields": ["Street"]}, "POST"),
    ]
    assert response.status == 400
