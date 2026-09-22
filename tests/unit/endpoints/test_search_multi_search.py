"""Unit tests for Search.multi_search: body shape, validation, and error
handling.

Captured request calls are asserted as (endpoint, data, method) tuples —
this service never passes per-call header options. Valid payloads are
forwarded by reference after serialize (dicts unchanged; DTOs as to_dict).
"""

from __future__ import annotations

from blnk_sdk.http_client import format_response
from blnk_sdk.services.search import Search
from blnk_sdk.types.search import MultiSearchParams, SearchParams
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_multi_search_posts_searches_array() -> None:
    """posts a searches array with collection beside each entry's params"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    params = (
        MultiSearchParams()
        .add("transactions", SearchParams(q="ref_001", query_by="reference"))
        .add(
            "balances",
            SearchParams(q="*", filter_by="currency:USD", per_page=50),
        )
    )

    response = search.multi_search(params)

    assert _args(captured_request) == [("multi-search", params.to_dict(), "POST")]
    assert params.to_dict() == {
        "searches": [
            {
                "collection": "transactions",
                "q": "ref_001",
                "query_by": "reference",
            },
            {
                "collection": "balances",
                "q": "*",
                "filter_by": "currency:USD",
                "per_page": 50,
            },
        ]
    }
    assert response.status == 200


def test_multi_search_rejects_empty_searches() -> None:
    """rejects an empty searches list without calling the API"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.multi_search(MultiSearchParams())

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "searches must be a non-empty array"


def test_multi_search_rejects_unknown_collection() -> None:
    """rejects an unknown collection and names the entry"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    params = (
        MultiSearchParams()
        .add("ledgers", SearchParams(q="savings"))
        .add("accounts", SearchParams(q="x"))
    )

    response = search.multi_search(params)

    assert _args(captured_request) == []
    assert response.status == 400
    assert (
        response.message
        == "searches[1].collection must be ledgers, transactions, balances, or identities"
    )


def test_multi_search_rejects_missing_q() -> None:
    """rejects a missing q and names the entry"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.multi_search(MultiSearchParams().add("ledgers", {}))

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == 'searches[0]: Field "q" must be filled'


def test_multi_search_rejects_null_params() -> None:
    """rejects null params"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.multi_search(None)

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "Multi-search params must be a valid object"


def test_multi_search_handles_thrown_errors() -> None:
    """handles thrown errors gracefully"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, "Network Error")
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.multi_search(
        MultiSearchParams().add("ledgers", SearchParams(q="a"))
    )

    assert response.status == 500
    assert response.message == "Network Error"
