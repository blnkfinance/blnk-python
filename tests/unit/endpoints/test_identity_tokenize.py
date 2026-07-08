"""Unit tests for Identity.tokenize: request shape, field-name handling,
validation failures, and error forwarding."""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.identity import Identity
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

VALID_DATA = {"fields": ["FirstName", "EmailAddress"]}

MOCK_RESPONSE = {"message": "Fields tokenized successfully"}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)


def _captured(captured_request: CapturingRequest) -> list:
    return [call[:3] for call in captured_request.calls]


def test_tokenize_uses_pascal_case_struct_field_names() -> None:
    """tokenize uses PascalCase struct field names"""
    mock_logger = create_mock_logger()
    pascal_case_data = {
        "fields": ["FirstName", "LastName", "EmailAddress", "PhoneNumber"],
    }
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize("idt_test_123", pascal_case_data)

    assert _captured(captured_request) == [
        ("identities/idt_test_123/tokenize", pascal_case_data, "POST"),
    ]
    assert response.status == 200


def test_tokenize_posts_identities_id_tokenize() -> None:
    """tokenize POSTs identities/{id}/tokenize"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize("idt_test_123", VALID_DATA)

    assert _captured(captured_request) == [
        ("identities/idt_test_123/tokenize", VALID_DATA, "POST"),
    ]
    assert response.status == 200
    assert response.data["message"] == "Fields tokenized successfully"


def test_tokenize_rejects_empty_identity_id() -> None:
    """tokenize rejects empty identity id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize("", VALID_DATA)

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "identity id is required"


def test_tokenize_rejects_empty_fields() -> None:
    """tokenize rejects empty fields"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize("idt_test_123", {"fields": []})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "at least one field must be specified"


def test_tokenize_forwards_api_errors() -> None:
    """tokenize forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=404, message="Identity not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize("idt_missing", VALID_DATA)

    assert _captured(captured_request) == [
        ("identities/idt_missing/tokenize", VALID_DATA, "POST"),
    ]
    assert response.status == 404
