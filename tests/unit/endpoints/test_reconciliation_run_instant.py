"""Unit tests for Reconciliation.run_instant: request shape, payload
validation, and error forwarding.

An external transaction's `date` is a plain string sent to the wire
verbatim — never parsed or reformatted.
"""

from __future__ import annotations

import re

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.reconciliation import Reconciliation
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

VALID_DATA = {
    "external_transactions": [
        {
            "id": "txn_1",
            "amount": 5.49,
            "reference": "INV-2023-002",
            "currency": "GBP",
            "description": "Card payment",
            "date": "2024-11-15T14:25:30Z",
            "source": "bank-api",
        },
    ],
    "strategy": "one_to_one",
    "dry_run": True,
    "matching_rule_ids": ["rule_abc123"],
}


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_run_instant_posts_reconciliation_start_instant() -> None:
    """runInstant POSTs reconciliation/start-instant"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(
            status=200,
            message="Success",
            data={"reconciliation_id": "rec_test_123"},
        )

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.run_instant(VALID_DATA)

    assert _args(captured_request) == [
        ("reconciliation/start-instant", VALID_DATA, "POST"),
    ]
    assert response.status == 200
    assert response.data["reconciliation_id"] == "rec_test_123"


def test_run_instant_returns_400_for_invalid_payload() -> None:
    """runInstant returns 400 for invalid payload"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(
            status=200,
            message="Success",
            data={"reconciliation_id": "rec_test_123"},
        )

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.run_instant(
        {**VALID_DATA, "external_transactions": []}
    )

    assert len(captured_request.calls) == 0
    assert response.status == 400
    # actual message: `external_transactions must be a non-empty array`
    assert re.search(r"external_transactions", response.message)


def test_run_instant_forwards_api_errors() -> None:
    """runInstant forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        # RETURNED 500, not thrown.
        return ApiResponse(
            status=500, message="Failed to start instant reconciliation", data=None
        )

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.run_instant(VALID_DATA)

    assert _args(captured_request) == [
        ("reconciliation/start-instant", VALID_DATA, "POST"),
    ]
    assert response.status == 500
