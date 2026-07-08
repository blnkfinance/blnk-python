"""Unit tests for Reconciliation.get: request shape, empty-id
validation, and error forwarding.

Response timestamp fields stay plain strings (they are never parsed);
a GET carries no body, so the captured data argument is None.
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.reconciliation import Reconciliation
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

MOCK_RECONCILIATION = {
    "reconciliation_id": "recon_test_123",
    "upload_id": "instant_abc",
    "status": "completed",
    "matched_transactions": 2,
    "unmatched_transactions": 1,
    "is_dry_run": True,
    "started_at": "2026-06-12T04:23:48.196087Z",
    "completed_at": "2026-06-12T04:23:49.196087Z",
}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    """Always answer 200 Success with the module's mock reconciliation."""
    return ApiResponse(status=200, message="Success", data=MOCK_RECONCILIATION)


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_get_calls_reconciliation_id() -> None:
    """get calls reconciliation/{id}"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.get("recon_test_123")

    assert _args(captured_request) == [
        ("reconciliation/recon_test_123", None, "GET"),
    ]
    assert response.status == 200
    assert response.data["reconciliation_id"] == "recon_test_123"
    assert response.data["status"] == "completed"


def test_get_rejects_empty_reconciliation_id() -> None:
    """get rejects empty reconciliation id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.get("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "reconciliation id is required"


def test_get_forwards_api_errors() -> None:
    """get forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=404, message="Reconciliation not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.get("recon_missing")

    assert _args(captured_request) == [
        ("reconciliation/recon_missing", None, "GET"),
    ]
    assert response.status == 404
