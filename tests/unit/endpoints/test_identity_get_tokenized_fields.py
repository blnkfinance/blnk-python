"""Unit tests for Identity.get_tokenized_fields: request shape, empty
result handling, empty-id validation, and error forwarding."""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.identity import Identity
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

MOCK_RESPONSE = {
    "tokenized_fields": ["FirstName", "LastName", "EmailAddress", "PhoneNumber"],
}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)


def _captured(captured_request: CapturingRequest) -> list:
    return [call[:3] for call in captured_request.calls]


def test_get_tokenized_fields_gets_identities_id_tokenized_fields() -> None:
    """getTokenizedFields GETs identities/{id}/tokenized-fields"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.get_tokenized_fields("idt_test_123")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/tokenized-fields", None, "GET"),
    ]
    assert response.status == 200
    assert response.data["tokenized_fields"] == MOCK_RESPONSE["tokenized_fields"]


def test_get_tokenized_fields_returns_empty_list_for_fresh_identity() -> None:
    """getTokenizedFields returns empty list for fresh identity"""
    mock_logger = create_mock_logger()
    empty_response = {"tokenized_fields": []}

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=200, message="Success", data=empty_response)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.get_tokenized_fields("idt_test_123")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/tokenized-fields", None, "GET"),
    ]
    assert response.status == 200
    assert response.data["tokenized_fields"] == []


def test_get_tokenized_fields_rejects_empty_identity_id() -> None:
    """getTokenizedFields rejects empty identity id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.get_tokenized_fields("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "identity id is required"


def test_get_tokenized_fields_forwards_api_errors() -> None:
    """getTokenizedFields forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=404, message="Identity not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.get_tokenized_fields("idt_missing")

    assert _captured(captured_request) == [
        ("identities/idt_missing/tokenized-fields", None, "GET"),
    ]
    assert response.status == 404
