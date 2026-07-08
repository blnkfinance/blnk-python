"""Unit tests for the Hooks service: create, list, get, update, and delete.

Covers request shapes (endpoint, payload, method), local validation
failures that return 400 without any HTTP call, and forwarding of API
error responses. VALID_DATA / MOCK_RESPONSE are shared by the whole
module; UPDATE_DATA / DELETE_RESPONSE are fixtures for the update and
delete groups. Each case builds its own inline mock request wrapped in a
CapturingRequest; requests without a body are captured with a None data
argument. The final case exercises the full client through the injected
transport to verify that a 200 response with an empty body succeeds
without a JSON parse error (the stub's json() raising ValueError is
never reached on the text-first read path).
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.client import Blnk
from blnk_sdk.http_client import format_response
from blnk_sdk.services.hooks import Hooks
from tests.mocks.blnk_client_mocks import (
    create_mock_blnk_client_options,
    create_mock_logger,
)
from tests.mocks.capture import CapturingRequest
from tests.mocks.transport_mock import make_response

VALID_DATA = {
    "name": "Pre-transaction validation",
    "url": "https://api.example.com/validate",
    "type": "PRE_TRANSACTION",
    "active": True,
    "timeout": 30,
    "retry_count": 3,
}

MOCK_RESPONSE = {
    "id": "hk_test_123",
    "name": VALID_DATA["name"],
    "url": VALID_DATA["url"],
    "type": VALID_DATA["type"],
    "active": VALID_DATA["active"],
    "timeout": VALID_DATA["timeout"],
    "retry_count": VALID_DATA["retry_count"],
    "created_at": "2026-06-12T04:50:00.000Z",
    "last_run": "0001-01-01T00:00:00Z",
    "last_success": False,
}

# Fixture shared by the `Hooks.update` cases.
UPDATE_DATA = {
    "name": "Pre-transaction validation (updated)",
    "url": "https://api.example.com/validate-v2",
    "type": "PRE_TRANSACTION",
    "active": False,
    "timeout": 45,
    "retry_count": 5,
}

# Fixture shared by the `Hooks.delete` cases.
DELETE_RESPONSE = {"message": "hook deleted successfully"}


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


# --------------------------------------------------------------------------- #
# Hooks.create


def test_create_posts_hooks() -> None:
    """create POSTs hooks"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=201, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.create(VALID_DATA)

    assert _args(captured_request) == [("hooks", VALID_DATA, "POST")]
    assert response.status == 201
    assert response.data["id"] == "hk_test_123"
    assert response.data["type"] == "PRE_TRANSACTION"


def test_create_returns_400_for_invalid_payload() -> None:
    """create returns 400 for invalid payload"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=201, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.create({**VALID_DATA, "type": "INVALID"})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "type must be PRE_TRANSACTION or POST_TRANSACTION"


def test_create_forwards_api_errors() -> None:
    """create forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(
            status=403, message="hook management requires master key", data=None
        )

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.create(VALID_DATA)

    assert _args(captured_request) == [("hooks", VALID_DATA, "POST")]
    assert response.status == 403


# --------------------------------------------------------------------------- #
# Hooks.list


def test_list_gets_hooks_without_type_filter() -> None:
    """list GETs hooks without type filter"""
    mock_logger = create_mock_logger()
    list_response = [MOCK_RESPONSE]

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=list_response)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.list()

    assert _args(captured_request) == [("hooks", None, "GET")]
    assert response.status == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == "hk_test_123"


def test_list_gets_hooks_type_when_type_provided() -> None:
    """list GETs hooks?type= when type provided"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=[])

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.list({"type": "POST_TRANSACTION"})

    assert _args(captured_request) == [
        ("hooks?type=POST_TRANSACTION", None, "GET")
    ]
    assert response.status == 200


def test_list_returns_400_for_invalid_type() -> None:
    """list returns 400 for invalid type"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=[])

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.list({"type": "INVALID"})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "type must be PRE_TRANSACTION or POST_TRANSACTION"


def test_list_forwards_api_errors() -> None:
    """list forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(
            status=403, message="hook management requires master key", data=None
        )

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.list()

    assert _args(captured_request) == [("hooks", None, "GET")]
    assert response.status == 403


# --------------------------------------------------------------------------- #
# Hooks.get


def test_get_gets_hooks_id() -> None:
    """get GETs hooks/{id}"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.get("hk_test_123")

    assert _args(captured_request) == [("hooks/hk_test_123", None, "GET")]
    assert response.status == 200
    assert response.data["id"] == "hk_test_123"
    assert response.data["type"] == "PRE_TRANSACTION"


def test_get_returns_400_for_empty_id() -> None:
    """get returns 400 for empty id"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.get("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "hook id is required"


def test_get_forwards_api_errors() -> None:
    """get forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=404, message="hook not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.get("hk_missing")

    assert _args(captured_request) == [("hooks/hk_missing", None, "GET")]
    assert response.status == 404


# --------------------------------------------------------------------------- #
# Hooks.update


def test_update_puts_hooks_id() -> None:
    """update PUTs hooks/{id}"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(
            status=200, message="Success", data={**MOCK_RESPONSE, **UPDATE_DATA}
        )

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.update("hk_test_123", UPDATE_DATA)

    assert _args(captured_request) == [("hooks/hk_test_123", UPDATE_DATA, "PUT")]
    assert response.status == 200
    assert response.data["active"] is False
    assert response.data["timeout"] == 45


def test_update_returns_400_for_empty_id() -> None:
    """update returns 400 for empty id"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.update("", UPDATE_DATA)

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "hook id is required"


def test_update_returns_400_for_invalid_payload() -> None:
    """update returns 400 for invalid payload"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=MOCK_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.update("hk_test_123", {**UPDATE_DATA, "timeout": 0})

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "timeout must be a positive number"


def test_update_forwards_api_errors() -> None:
    """update forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=404, message="hook not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.update("hk_missing", UPDATE_DATA)

    assert _args(captured_request) == [("hooks/hk_missing", UPDATE_DATA, "PUT")]
    assert response.status == 404


# --------------------------------------------------------------------------- #
# Hooks.delete


def test_delete_deletes_hooks_id() -> None:
    """delete DELETEs hooks/{id}"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=DELETE_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.delete("hk_test_123")

    assert _args(captured_request) == [("hooks/hk_test_123", None, "DELETE")]
    assert response.status == 200
    assert response.data["message"] == "hook deleted successfully"


def test_delete_returns_400_for_empty_id() -> None:
    """delete returns 400 for empty id"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=200, message="Success", data=DELETE_RESPONSE)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.delete("")

    assert len(captured_request.calls) == 0
    assert response.status == 400
    assert response.message == "hook id is required"


def test_delete_forwards_api_errors() -> None:
    """delete forwards API errors"""
    mock_logger = create_mock_logger()

    def third_party_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=404, message="hook not found", data=None)

    captured_request = CapturingRequest(third_party_request)
    hooks = Hooks(captured_request, mock_logger, format_response)

    response = hooks.delete("hk_missing")

    assert _args(captured_request) == [("hooks/hk_missing", None, "DELETE")]
    assert response.status == 404


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
        {"Hooks": Hooks},
        format_response,
        empty_body_transport,
    )

    response = blnk.hooks.delete("hk_test_123")

    assert response.status == 200
    assert response.message == "Success"
    assert response.data is None
