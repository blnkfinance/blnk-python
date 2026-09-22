"""Unit tests for the Ledgers service: create and update.

One mock logger is created at module scope and deliberately shared by
every test; the third_party_request fixture provides a fresh successful
201 mock request per test. Captured request calls are asserted as
(endpoint, data, method) tuples — this service never passes per-call
header options.
"""

from __future__ import annotations

import pytest

from blnk_sdk.http_client import format_response
from blnk_sdk.services.ledgers import Ledgers
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest

MOCK_LOGGER = create_mock_logger()  # deliberately shared by the whole suite


@pytest.fixture
def third_party_request():
    """Provide a fresh successful mock request (201 Created) per test."""
    return create_mock_blnk_request(True, None, 201)


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


def test_creates_a_ledger_with_valid_data(third_party_request) -> None:
    """Creates a ledger with valid data"""
    captured_request = CapturingRequest(third_party_request)
    ledger = Ledgers(captured_request, MOCK_LOGGER, format_response)
    data = {
        "name": "My Ledger",
        "meta_data": {
            "company_name": "Test Company",
        },
    }

    response = ledger.create(data)

    assert _args(captured_request) == [("ledgers", data, "POST")]
    assert response.status == 201
    assert response.data["name"] == data["name"]


def test_it_should_handle_missing_required_fields() -> None:
    """it should handle missing required fields"""
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    # simulates a developer passing `any` and missing required data types
    data = {
        "meta_data": {
            "company_name": "Test Company",
        },
    }

    response = ledgers.create(data)

    # request won't get called since this fails validation
    assert _args(captured_request) == []
    assert response.status == 400, "Response is 400"
    assert response.data is None


def test_it_should_handle_thrown_errors_gracefully() -> None:
    """it should handle thrown errors gracefully"""
    third_party_request = create_mock_blnk_request(True, "Network Error")
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = Ledgers(captured_request, MOCK_LOGGER, format_response)

    data = {
        "name": "Test Ledger",
        "meta_data": {
            "company_name": "Test Company",
        },
    }

    response = ledger_balance.create(data)

    # the call is recorded even though the mock threw
    assert _args(captured_request) == [("ledgers", data, "POST")]

    assert response.status == 500, "Response is 500"
    assert response.data is None
    assert response.message == "Network Error"


def test_update_calls_put_ledgers_id() -> None:
    """update calls PUT /ledgers/{id}"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)
    ledger_id = "ldg_073f7ffe-9dfd-42ce-aa50-d1dca1788adc"
    data = {"name": "Updated Customer Savings Account"}

    response = ledgers.update(ledger_id, data)

    assert _args(captured_request) == [(f"ledgers/{ledger_id}", data, "PUT")]
    assert response.status == 200
    assert response.data["name"] == data["name"]


def test_update_rejects_empty_ledger_id(third_party_request) -> None:
    """update rejects empty ledger id"""
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.update("", {"name": "Updated Name"})

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "ledger id is required"


def test_update_rejects_missing_name(third_party_request) -> None:
    """update rejects missing name"""
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.update("ldg_123", {})

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.data is None


def test_update_handles_thrown_errors_gracefully() -> None:
    """update handles thrown errors gracefully"""
    third_party_request = create_mock_blnk_request(True, "Network Error")
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)
    data = {"name": "Updated Name"}

    response = ledgers.update("ldg_123", data)

    assert _args(captured_request) == [("ledgers/ldg_123", data, "PUT")]
    assert response.status == 500
    assert response.message == "Network Error"


def test_list_calls_get_ledgers() -> None:
    """list calls GET /ledgers with no query when no options are given"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.list()

    assert _args(captured_request) == [("ledgers", None, "GET")]
    assert response.status == 200


def test_list_empty_options_omits_query() -> None:
    """list with empty options still uses Core defaults (no query string)"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.list({})

    assert _args(captured_request) == [("ledgers", None, "GET")]
    assert response.status == 200


def test_list_forwards_limit_and_offset() -> None:
    """list forwards limit and offset as query parameters"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.list({"limit": 25, "offset": 50})

    assert _args(captured_request) == [("ledgers?limit=25&offset=50", None, "GET")]
    assert response.status == 200


def test_list_rejects_limit_below_one() -> None:
    """list rejects a limit below 1 without calling the API"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.list({"limit": 0})

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "limit must be at least 1"


def test_list_rejects_unknown_option_keys() -> None:
    """list rejects a misspelled option so Core defaults are not used by accident"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.list({"limt": 50})

    assert _args(captured_request) == []
    assert response.status == 400
    assert response.message == "unsupported list option: limt"


def test_list_handles_thrown_errors_gracefully() -> None:
    """list handles thrown errors gracefully"""
    third_party_request = create_mock_blnk_request(True, "Network Error")
    captured_request = CapturingRequest(third_party_request)
    ledgers = Ledgers(captured_request, MOCK_LOGGER, format_response)

    response = ledgers.list()

    assert response.status == 500
    assert response.message == "Network Error"
