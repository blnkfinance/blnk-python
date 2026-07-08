"""Unit tests for Metadata.update: request shape, validation failures,
and error forwarding.

VALID_DATA / MOCK_RESPONSE are shared by the whole module; each case
builds its own inline mock request wrapped in a CapturingRequest.
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.metadata import Metadata
from tests.mocks.blnk_client_mocks import create_mock_logger
from tests.mocks.capture import CapturingRequest

VALID_DATA = {
    "meta_data": {
        "project_owner": "Acme LLC",
        "update_status": "Approved",
    },
}

MOCK_RESPONSE = {
    "meta_data": {
        "project_owner": "Acme LLC",
        "update_status": "Approved",
    },
}


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_update_posts_id_metadata() -> None:
    """update POSTs {id}/metadata"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    metadata = Metadata(captured_request, mock_logger, format_response)

    response = metadata.update("ldg_test_123", VALID_DATA)

    assert _args(captured_request) == [
        ("ldg_test_123/metadata", VALID_DATA, "POST")
    ]
    assert response.status == 200
    assert response.data["meta_data"] == VALID_DATA["meta_data"]


def test_update_rejects_empty_id() -> None:
    """update rejects empty id"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    metadata = Metadata(captured_request, mock_logger, format_response)

    response = metadata.update("", VALID_DATA)

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "id is required"


def test_update_rejects_invalid_meta_data() -> None:
    """update rejects invalid meta_data"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    metadata = Metadata(captured_request, mock_logger, format_response)

    response = metadata.update("ldg_test_123", {"meta_data": None})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "meta_data must be a valid object"


def test_update_forwards_api_errors() -> None:
    """update forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=404, message="Entity not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    metadata = Metadata(captured_request, mock_logger, format_response)

    response = metadata.update("ldg_missing", VALID_DATA)

    assert _args(captured_request) == [
        ("ldg_missing/metadata", VALID_DATA, "POST")
    ]
    assert response.status == 404
