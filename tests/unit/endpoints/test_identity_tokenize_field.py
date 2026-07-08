"""Unit tests for Identity.tokenize_field: request shape, field-name
path handling, validation failures, and error forwarding."""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.identity import Identity
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

MOCK_RESPONSE = {"message": "Field tokenized successfully"}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)


def _captured(captured_request: CapturingRequest) -> list:
    return [call[:3] for call in captured_request.calls]


def test_tokenize_field_posts_identities_id_tokenize_field() -> None:
    """tokenizeField POSTs identities/{id}/tokenize/{field}"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize_field("idt_test_123", "FirstName")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/tokenize/FirstName", None, "POST"),
    ]
    assert response.status == 200
    assert response.data["message"] == "Field tokenized successfully"


def test_tokenize_field_uses_pascal_case_struct_field_name_in_path() -> None:
    """tokenizeField uses PascalCase struct field name in path"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    identity.tokenize_field("idt_test_123", "EmailAddress")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/tokenize/EmailAddress", None, "POST"),
    ]


def test_tokenize_field_rejects_empty_identity_id() -> None:
    """tokenizeField rejects empty identity id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize_field("", "FirstName")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "identity id is required"


def test_tokenize_field_rejects_empty_field_name() -> None:
    """tokenizeField rejects empty field name"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize_field("idt_test_123", "")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "field name is required"


def test_tokenize_field_forwards_api_errors() -> None:
    """tokenizeField forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=409, message="Field already tokenized", data=None)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.tokenize_field("idt_test_123", "FirstName")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/tokenize/FirstName", None, "POST"),
    ]
    assert response.status == 409
