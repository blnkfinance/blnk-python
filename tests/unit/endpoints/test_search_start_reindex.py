"""Unit tests for Search.start_reindex: request shape, batch_size
forwarding, and batch_size validation.

Note: `start_reindex()` with no arguments sends the EMPTY dict `{}` as
the request data (not None) — the captured data argument is asserted to
be exactly `{}`.
"""

from __future__ import annotations

from blnk_sdk.http_client import format_response
from blnk_sdk.services.search import Search
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_start_reindex_posts_to_search_reindex_with_empty_body() -> None:
    """startReindex posts to search/reindex with empty body"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 202)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.start_reindex()

    assert _args(captured_request) == [("search/reindex", {}, "POST")]
    assert response.status == 202


def test_start_reindex_forwards_batch_size() -> None:
    """startReindex forwards batch_size"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 202)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.start_reindex({"batch_size": 500})

    assert _args(captured_request) == [("search/reindex", {"batch_size": 500}, "POST")]
    assert response.status == 202


def test_start_reindex_rejects_invalid_batch_size() -> None:
    """startReindex rejects invalid batch_size"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    search = Search(captured_request, mock_logger, format_response)

    response = search.start_reindex({"batch_size": 0})

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "batch_size must be a positive integer if provided"
