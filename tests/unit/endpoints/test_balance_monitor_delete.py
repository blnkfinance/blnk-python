"""Unit tests for BalanceMonitor.delete.

Covers the DELETE request shape, URL encoding of the monitor id, the
empty-id validation failure that returns 400 without any HTTP call, and
forwarding of API error responses. Each case builds its own inline mock
request wrapped in a CapturingRequest; a DELETE carries no body, so the
captured data argument is None. The final case exercises the full client
through the injected transport to verify that a 200 response with an
empty body succeeds without a JSON parse error (the stub's json()
raising ValueError must never be reached).
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.client import Blnk
from blnk_sdk.http_client import format_response
from blnk_sdk.services.balance_monitors import BalanceMonitor
from tests.mocks.blnk_client_mocks import (
    create_mock_blnk_client_options,
    create_mock_logger,
)
from tests.mocks.capture import CapturingRequest
from tests.mocks.transport_mock import make_response

DELETE_RESPONSE = {"message": "BalanceMonitor deleted successfully"}


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_delete_deletes_balance_monitors_id() -> None:
    """delete DELETEs balance-monitors/{id}"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=DELETE_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)

    response = balance_monitor.delete("mon_test_123")

    assert _args(captured_request) == [
        ("balance-monitors/mon_test_123", None, "DELETE")
    ]
    assert response.status == 200
    assert response.data["message"] == "BalanceMonitor deleted successfully"


def test_delete_url_encodes_monitor_id() -> None:
    """delete URL-encodes monitor id"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=DELETE_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)

    balance_monitor.delete("mon_test/special")

    assert _args(captured_request) == [
        ("balance-monitors/mon_test%2Fspecial", None, "DELETE")
    ]


def test_delete_returns_400_for_empty_id() -> None:
    """delete returns 400 for empty id"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=DELETE_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)

    response = balance_monitor.delete("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "monitor id is required"


def test_delete_forwards_api_errors() -> None:
    """delete forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=404, message="Balance monitor not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)

    response = balance_monitor.delete("mon_missing")

    assert _args(captured_request) == [
        ("balance-monitors/mon_missing", None, "DELETE")
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
        {"BalanceMonitor": BalanceMonitor},
        format_response,
        empty_body_transport,
    )

    response = blnk.balance_monitor.delete("mon_test_123")

    assert response.status == 200
    assert response.message == "Success"
    assert response.data is None
