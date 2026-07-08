"""Unit tests for Reconciliation.delete_matching_rule: request shape,
empty-id validation, and error forwarding.

A DELETE carries no body, so the captured data argument is None.
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.reconciliation import Reconciliation
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

MOCK_RESPONSE = {"message": "Matching rule deleted successfully"}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    """Always answer 200 Success with the module's mock response body."""
    return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_delete_matching_rule_deletes_reconciliation_matching_rules_id() -> None:
    """deleteMatchingRule DELETEs reconciliation/matching-rules/{id}"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.delete_matching_rule("rule_test_123")

    assert _args(captured_request) == [
        ("reconciliation/matching-rules/rule_test_123", None, "DELETE"),
    ]
    assert response.status == 200
    assert response.data["message"] == "Matching rule deleted successfully"


def test_delete_matching_rule_rejects_empty_rule_id() -> None:
    """deleteMatchingRule rejects empty rule id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.delete_matching_rule("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "matching rule id is required"


def test_delete_matching_rule_forwards_api_errors() -> None:
    """deleteMatchingRule forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=404, message="Matching rule not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.delete_matching_rule("rule_missing")

    assert _args(captured_request) == [
        ("reconciliation/matching-rules/rule_missing", None, "DELETE"),
    ]
    assert response.status == 404
