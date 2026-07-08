"""Unit tests for the ApiKeys service: create, list, and delete.

Covers request shapes (endpoint, payload, method), local validation
failures that return 400 without any HTTP call, URL encoding of ids and
query parameters (expected endpoints are computed with the same
percent_encode helper the service uses), and forwarding of API
error responses. Each case builds its own inline mock request wrapped in
a CapturingRequest. The final two cases exercise the full client through
the injected transport to verify that 204/200 responses with empty
bodies succeed without a JSON parse error (the stub's json() raising
ValueError is never reached on the text-first read path).
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.client import Blnk
from blnk_sdk.http_client import format_response
from blnk_sdk.services.api_keys import ApiKeys
from blnk_sdk.uri_utils import percent_encode
from tests.mocks.blnk_client_mocks import (
    create_mock_blnk_client_options,
    create_mock_logger,
)
from tests.mocks.capture import CapturingRequest
from tests.mocks.transport_mock import make_response

VALID_DATA = {
    "name": "Service Account",
    "owner": "merchant_a",
    "scopes": ["ledgers:read", "balances:write"],
    "expires_at": "2026-03-11T00:00:00Z",
}

MOCK_RESPONSE = {
    "api_key_id": "api_key_test_123",
    "key": "YVLIhuIplUzLRCcT9r7DQ_jsGKCXAn39JQ3n_o-Ll2Q=",
    "name": VALID_DATA["name"],
    "owner_id": VALID_DATA["owner"],
    "scopes": VALID_DATA["scopes"],
    "expires_at": VALID_DATA["expires_at"],
    "created_at": "2026-06-12T05:50:00.000Z",
    "last_used_at": "0001-01-01T00:00:00Z",
    "is_revoked": False,
}

# Fixture shared by the `ApiKeys.list` cases.
LIST_ITEM = {
    "api_key_id": "api_key_test_123",
    "key": "$2a$10$hashedkeyvalue",
    "name": "Service Account",
    "owner_id": "merchant_a",
    "scopes": ["ledgers:read"],
    "expires_at": "2026-03-11T00:00:00Z",
    "created_at": "2026-06-12T05:50:00.000Z",
    "last_used_at": "0001-01-01T00:00:00Z",
    "is_revoked": False,
}


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


# --------------------------------------------------------------------------- #
# ApiKeys.create


def test_create_posts_api_keys() -> None:
    """create POSTs api-keys"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=201, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.create(VALID_DATA)

    assert _args(captured_request) == [("api-keys", VALID_DATA, "POST")]
    assert response.status == 201
    assert response.data["api_key_id"] == "api_key_test_123"
    assert response.data["key"] == MOCK_RESPONSE["key"]
    assert response.data["owner_id"] == "merchant_a"


def test_create_returns_400_for_invalid_payload() -> None:
    """create returns 400 for invalid payload"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=201, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.create({**VALID_DATA, "scopes": []})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "at least one scope must be specified"


def test_create_forwards_api_errors() -> None:
    """create forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=403, message="forbidden", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.create(VALID_DATA)

    assert _args(captured_request) == [("api-keys", VALID_DATA, "POST")]
    assert response.status == 403


# --------------------------------------------------------------------------- #
# ApiKeys.list


def test_list_gets_api_keys_without_owner_filter() -> None:
    """list GETs api-keys without owner filter"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=[LIST_ITEM])

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.list()

    assert _args(captured_request) == [("api-keys", None, "GET")]
    assert response.status == 200
    assert len(response.data) == 1
    assert response.data[0]["api_key_id"] == "api_key_test_123"


def test_list_gets_api_keys_owner_when_owner_provided() -> None:
    """list GETs api-keys?owner= when owner provided"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=[])

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.list({"owner": "merchant_a"})

    assert _args(captured_request) == [("api-keys?owner=merchant_a", None, "GET")]
    assert response.status == 200


def test_list_url_encodes_owner_query_param() -> None:
    """list URL-encodes owner query param"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=[])

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.list({"owner": "merchant a&role=admin"})

    assert _args(captured_request) == [
        (
            f"api-keys?owner={percent_encode('merchant a&role=admin')}",
            None,
            "GET",
        )
    ]
    assert response.status == 200


def test_list_returns_400_for_empty_owner() -> None:
    """list returns 400 for empty owner"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=[])

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.list({"owner": ""})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "owner must be a non-empty string"


def test_list_forwards_api_errors() -> None:
    """list forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=403, message="forbidden", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.list({"owner": "merchant_a"})

    assert _args(captured_request) == [("api-keys?owner=merchant_a", None, "GET")]
    assert response.status == 403


# --------------------------------------------------------------------------- #
# ApiKeys.delete


def test_delete_deletes_api_keys_id() -> None:
    """delete DELETEs api-keys/{id}"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=204, message="Success", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.delete("api_key_test_123")

    assert _args(captured_request) == [
        ("api-keys/api_key_test_123", None, "DELETE")
    ]
    assert response.status == 204
    assert response.data is None


def test_delete_deletes_api_keys_id_owner_when_owner_provided() -> None:
    """delete DELETEs api-keys/{id}?owner= when owner provided"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=204, message="Success", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.delete("api_key_test_123", {"owner": "merchant_a"})

    assert _args(captured_request) == [
        ("api-keys/api_key_test_123?owner=merchant_a", None, "DELETE")
    ]
    assert response.status == 204


def test_delete_url_encodes_id_and_owner() -> None:
    """delete URL-encodes id and owner"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=204, message="Success", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.delete("api/key?id=1", {"owner": "merchant a&role=admin"})

    assert _args(captured_request) == [
        (
            f"api-keys/{percent_encode('api/key?id=1')}"
            f"?owner={percent_encode('merchant a&role=admin')}",
            None,
            "DELETE",
        )
    ]
    assert response.status == 204


def test_delete_returns_400_for_empty_id() -> None:
    """delete returns 400 for empty id"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=204, message="Success", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.delete("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "api key id is required"


def test_delete_returns_400_for_empty_owner() -> None:
    """delete returns 400 for empty owner"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=204, message="Success", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.delete("api_key_test_123", {"owner": ""})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "owner must be a non-empty string"


def test_delete_forwards_api_errors() -> None:
    """delete forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=404, message="API key not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    api_keys = ApiKeys(captured_request, mock_logger, format_response)

    response = api_keys.delete("api_key_missing", {"owner": "merchant_a"})

    assert _args(captured_request) == [
        ("api-keys/api_key_missing?owner=merchant_a", None, "DELETE")
    ]
    assert response.status == 404


def test_delete_succeeds_through_request_layer_on_204_no_content() -> None:
    """delete succeeds through request layer on 204 No Content"""

    def no_content_transport(_url, _init):
        return make_response(
            ok=True,
            status=204,
            status_text="No Content",
            json_raises=ValueError("Unexpected end of JSON input"),
            text_body="",
        )

    blnk = Blnk(
        "test-key",
        create_mock_blnk_client_options(),
        {"ApiKeys": ApiKeys},
        format_response,
        no_content_transport,
    )

    response = blnk.api_keys.delete("api_key_test_123")

    assert response.status == 204
    assert response.message == "Success"
    assert response.data is None


def test_delete_succeeds_on_200_ok_with_empty_body() -> None:
    """delete succeeds on 200 OK with empty body"""

    def empty_body_transport(_url, _init):
        return make_response(
            ok=True,
            status=200,
            status_text="OK",
            json_raises=ValueError("Unexpected end of JSON input"),
            text_body="",
        )

    blnk = Blnk(
        "test-key",
        create_mock_blnk_client_options(),
        {"ApiKeys": ApiKeys},
        format_response,
        empty_body_transport,
    )

    response = blnk.api_keys.delete("api_key_test_123")

    assert response.status == 200
    assert response.message == "Success"
    assert response.data is None
