"""Unit tests for Search.search: per-collection request shapes,
collection validation, and query-parameter validation.

Captured request calls are asserted as (endpoint, data, method) tuples —
this service never passes per-call header options. The search params are
forwarded by reference, untouched.
"""

from __future__ import annotations

from blnk_sdk.http_client import format_response
from blnk_sdk.services.search import Search
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_search_forwards_identities_collection() -> None:
    """search forwards identities collection"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    params = {
        "q": "jane",
        "query_by": "first_name,last_name,email_address",
        "per_page": 10,
    }

    response = search.search(params, "identities")

    assert _args(captured_request) == [("search/identities", params, "POST")]
    assert response.status == 200


def test_search_rejects_invalid_collection() -> None:
    """search rejects invalid collection"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.search({"q": "test"}, "accounts")

    assert _args(captured_request) == []
    assert response.status == 400
    assert (
        response.message
        == "collection must be ledgers, transactions, balances, or identities"
    )


def test_search_rejects_empty_q() -> None:
    """search rejects empty q"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.search({"q": "   "}, "identities")

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == 'Field "q" must be filled'


def test_search_forwards_ledgers_collection() -> None:
    """search forwards ledgers collection"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    params = {"q": "General", "per_page": 5}
    response = search.search(params, "ledgers")

    assert _args(captured_request) == [("search/ledgers", params, "POST")]
    assert response.status == 201


def test_search_forwards_transactions_collection() -> None:
    """search forwards transactions collection"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    params = {"q": "payment", "per_page": 5}
    response = search.search(params, "transactions")

    assert _args(captured_request) == [("search/transactions", params, "POST")]
    assert response.status == 201


def test_search_rejects_invalid_per_page() -> None:
    """search rejects invalid per_page"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.search({"q": "*", "per_page": 500}, "identities")

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "per_page must be an integer between 1 and 250 if provided"
