"""Unit tests for Search.get_reindex_status: request shape and error
forwarding.

Both cases use inline mocks returning fixed ApiResponse payloads.
`get_reindex_status` sends no request body, so the captured tuples are
("search/reindex", None, "GET").
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.search import Search
from blnk_sdk.types.search import ReindexProgress
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_get_reindex_status_gets_search_reindex() -> None:
    """getReindexStatus GETs search/reindex"""
    mock_logger = create_mock_logger()
    # started_at is a raw server string passed through verbatim — the fixture
    # has EIGHT fractional digits; never reformat.
    progress = ReindexProgress(
        status="in_progress",
        phase="indexing_transactions",
        total_records=100,
        processed_records=50,
        started_at="2026-06-12T02:03:08.81867638Z",
    )

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=progress)

    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.get_reindex_status()

    assert _args(captured_request) == [("search/reindex", None, "GET")]
    assert response.status == 200
    assert response.data.status == "in_progress"
    assert response.data.phase == "indexing_transactions"


def test_get_reindex_status_forwards_api_errors() -> None:
    """getReindexStatus forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(
            status=404,
            message="No reindex operation has been started",
            data=None,
        )

    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.get_reindex_status()

    assert _args(captured_request) == [("search/reindex", None, "GET")]
    assert response.status == 404
