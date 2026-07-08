"""Unit tests for Identity.detokenize_field: request shape, field-name
path handling, validation failures, and error forwarding."""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.identity import Identity
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

MOCK_RESPONSE = {
    "field": "EmailAddress",
    "value": "jane@example.com",
}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)


def _captured(captured_request: CapturingRequest) -> list:
    return [call[:3] for call in captured_request.calls]


def test_detokenize_field_gets_identities_id_detokenize_field() -> None:
    """detokenizeField GETs identities/{id}/detokenize/{field}"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize_field("idt_test_123", "EmailAddress")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/detokenize/EmailAddress", None, "GET"),
    ]
    assert response.status == 200
    assert response.data["field"] == "EmailAddress"
    assert response.data["value"] == "jane@example.com"


def test_detokenize_field_uses_pascal_case_struct_field_name_in_path() -> None:
    """detokenizeField uses PascalCase struct field name in path"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(
            status=200, message="Success", data={"field": "FirstName", "value": "Jane"}
        )

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    identity.detokenize_field("idt_test_123", "FirstName")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/detokenize/FirstName", None, "GET"),
    ]


def test_detokenize_field_rejects_empty_identity_id() -> None:
    """detokenizeField rejects empty identity id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize_field("", "EmailAddress")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "identity id is required"


def test_detokenize_field_rejects_empty_field_name() -> None:
    """detokenizeField rejects empty field name"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize_field("idt_test_123", "")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "field name is required"


def test_detokenize_field_forwards_api_errors() -> None:
    """detokenizeField forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=400, message="Field is not tokenized", data=None)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.detokenize_field("idt_test_123", "PhoneNumber")

    assert _captured(captured_request) == [
        ("identities/idt_test_123/detokenize/PhoneNumber", None, "GET"),
    ]
    assert response.status == 400
