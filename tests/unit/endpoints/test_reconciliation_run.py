"""Unit tests for Reconciliation.run.

Note: `run` performs NO local validation; it forwards the caller's data
(and any server 400) untouched.
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.reconciliation import Reconciliation
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

VALID_DATA = {
    "upload_id": "upload_test_123",
    "matching_rule_ids": ["rule_test_123"],
    "dry_run": True,
    "strategy": "one_to_one",
    "grouping_criteria": "amount",
}


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_run_posts_reconciliation_start() -> None:
    """run POSTs reconciliation/start"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(
            status=200,
            message="Success",
            data={"reconciliation_id": "recon_test_123"},
        )

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.run(VALID_DATA)

    assert _args(captured_request) == [
        ("reconciliation/start", VALID_DATA, "POST"),
    ]
    assert response.status == 200
    assert response.data["reconciliation_id"] == "recon_test_123"
    # the response data must contain EXACTLY one key
    assert len(response.data or {}) == 1


def test_run_forwards_api_errors() -> None:
    """run forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(
            status=400, message="matching_rule_ids is required", data=None
        )

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.run(VALID_DATA)

    assert _args(captured_request) == [
        ("reconciliation/start", VALID_DATA, "POST"),
    ]
    assert response.status == 400
