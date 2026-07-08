"""Unit tests for Identity.delete: request shape, id URL-encoding,
empty-id validation, and error forwarding.

A DELETE carries no body, so the captured data argument is None. The
final case exercises the full client through the injected transport to
verify that a 200 response with an empty body succeeds without a JSON
parse error."""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.client import Blnk
from blnk_sdk.http_client import format_response
from blnk_sdk.services.identity import Identity
from tests.mocks.blnk_client_mocks import (
    create_mock_blnk_client_options,
    create_mock_logger,
)
from tests.mocks.capture import CapturingRequest
from tests.mocks.transport_mock import make_response

DELETE_RESPONSE = {"message": "Identity deleted successfully"}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    return ApiResponse(status=200, message="Success", data=DELETE_RESPONSE)


def _captured(captured_request: CapturingRequest) -> list:
    return [call[:3] for call in captured_request.calls]


def test_delete_deletes_identities_id() -> None:
    """delete DELETEs identities/{id}"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.delete("idt_test_123")

    assert _captured(captured_request) == [
        ("identities/idt_test_123", None, "DELETE"),
    ]
    assert response.status == 200
    assert response.data["message"] == "Identity deleted successfully"


def test_delete_url_encodes_identity_id() -> None:
    """delete URL-encodes identity id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    identity.delete("idt_test/special")

    assert _captured(captured_request) == [
        ("identities/idt_test%2Fspecial", None, "DELETE"),
    ]


def test_delete_returns_400_for_empty_id() -> None:
    """delete returns 400 for empty id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.delete("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "identity id is required"


def test_delete_forwards_api_errors() -> None:
    """delete forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=404, message="Identity not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    identity = Identity(captured_request, mock_logger, format_response)

    response = identity.delete("idt_missing")

    assert _captured(captured_request) == [
        ("identities/idt_missing", None, "DELETE"),
    ]
    assert response.status == 404


def test_delete_succeeds_on_200_ok_with_empty_body() -> None:
    """delete succeeds on 200 OK with empty body"""

    def empty_body_transport(_url, _init):
        return make_response(
            ok=True,
            status=200,
            status_text="OK",
            json_raises=ValueError("Unexpected end of JSON input"),
            text_body="",
        )

    blnk = Blnk(
        "test-key",
        create_mock_blnk_client_options(),
        {"Identity": Identity},
        format_response,
        empty_body_transport,
    )

    response = blnk.identity.delete("idt_test_123")

    assert response.status == 200
    assert response.message == "Success"
    assert response.data is None
