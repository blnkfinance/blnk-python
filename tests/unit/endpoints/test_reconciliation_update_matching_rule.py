"""Unit tests for Reconciliation.update_matching_rule: request shape,
validation failures, and error forwarding.

VALID_DATA's second criterion has NO allowable_drift key — an absent key
counts as "not provided" and passes validation. MOCK_RESPONSE timestamps
carry sub-millisecond precision and stay plain strings.
"""

from __future__ import annotations

import re

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.reconciliation import Reconciliation
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

VALID_DATA = {
    "name": "Updated matcher",
    "description": "Amount with 2% drift matcher",
    "criteria": [
        {"field": "amount", "operator": "equals", "allowable_drift": 0.02},
        {"field": "currency", "operator": "equals"},
    ],
}

MOCK_RESPONSE = {
    **VALID_DATA,
    "rule_id": "rule_test_123",
    "created_at": "2026-06-12T04:31:55.613241Z",
    "updated_at": "2026-06-12T04:31:55.715443261Z",
}


def _success_request(endpoint, data, method, header_options=None) -> ApiResponse:
    """Always answer 200 Success with the module's mock response body."""
    return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_update_matching_rule_puts_reconciliation_matching_rules_id() -> None:
    """updateMatchingRule PUTs reconciliation/matching-rules/{id}"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.update_matching_rule("rule_test_123", VALID_DATA)

    assert _args(captured_request) == [
        ("reconciliation/matching-rules/rule_test_123", VALID_DATA, "PUT"),
    ]
    assert response.status == 200
    assert response.data["rule_id"] == "rule_test_123"
    assert response.data["name"] == "Updated matcher"


def test_update_matching_rule_rejects_empty_rule_id() -> None:
    """updateMatchingRule rejects empty rule id"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.update_matching_rule("", VALID_DATA)

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "matching rule id is required"


def test_update_matching_rule_returns_400_for_invalid_payload() -> None:
    """updateMatchingRule returns 400 for invalid payload"""
    mock_logger = create_mock_logger()
    captured_request = CapturingRequest(_success_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.update_matching_rule(
        "rule_test_123",
        {
            **VALID_DATA,
            "criteria": [
                {
                    "field": "invalid",
                    "operator": "equals",
                },
            ],
        },
    )

    assert len(captured_request.calls) == 0
    assert response.status == 400
    # actual message: the catch-all criterion message (check 5).
    assert re.search(r"criterion|criteria", response.message, re.IGNORECASE)


def test_update_matching_rule_forwards_api_errors() -> None:
    """updateMatchingRule forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None) -> ApiResponse:
        return ApiResponse(status=404, message="Matching rule not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    reconciliation = Reconciliation(captured_request, mock_logger, format_response)

    response = reconciliation.update_matching_rule("rule_missing", VALID_DATA)

    assert _args(captured_request) == [
        ("reconciliation/matching-rules/rule_missing", VALID_DATA, "PUT"),
    ]
    assert response.status == 404
