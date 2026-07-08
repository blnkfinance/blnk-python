"""Unit tests for Search.filter: per-collection request shapes and
payload validation.

NOTE the path shape: the collection comes FIRST (`transactions/filter`),
unlike `search` (`search/transactions`).
"""

from __future__ import annotations

from blnk_sdk.http_client import format_response
from blnk_sdk.services.search import Search
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_filter_forwards_transactions_collection() -> None:
    """filter forwards transactions collection"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    params = {
        "filters": [{"field": "status", "operator": "eq", "value": "APPLIED"}],
        "logical_operator": "and",
        "sort_by": "created_at",
        "sort_order": "desc",
        "include_count": True,
        "limit": 20,
        "offset": 0,
    }

    response = search.filter(params, "transactions")

    assert _args(captured_request) == [("transactions/filter", params, "POST")]
    assert response.status == 200


def test_filter_forwards_ledgers_collection() -> None:
    """filter forwards ledgers collection"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    params = {
        "filters": [{"field": "name", "operator": "like", "value": "%General%"}],
    }

    response = search.filter(params, "ledgers")

    assert _args(captured_request) == [("ledgers/filter", params, "POST")]
    assert response.status == 200


def test_filter_rejects_invalid_collection() -> None:
    """filter rejects invalid collection"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.filter(
        {"filters": [{"field": "status", "operator": "eq", "value": "APPLIED"}]},
        "accounts",
    )

    assert _args(captured_request) == []
    assert response.status == 400


def test_filter_rejects_missing_filter_value() -> None:
    """filter rejects missing filter value"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.filter(
        {"filters": [{"field": "status", "operator": "eq"}]},
        "transactions",
    )

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == 'filters[0].value is required for operator "eq"'


def test_filter_rejects_invalid_limit() -> None:
    """filter rejects invalid limit"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.filter(
        {
            "filters": [{"field": "status", "operator": "eq", "value": "APPLIED"}],
            "limit": 500,
        },
        "transactions",
    )

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "limit must be an integer between 1 and 100 if provided"
