"""Unit tests for the BalanceMonitor service: create, get, list, and update.

Grouped by verb (POST, GET, PUT); every case creates its own mock logger
and mock request. Captured request calls are asserted as (endpoint, data,
method) tuples — this service never passes per-call header options, and
requests without a body are captured with a None data argument.

The POST and PUT groups each contain a case named `It should handle
missing fields`; the PUT group's function name carries a `_put` suffix to
disambiguate.
"""

from __future__ import annotations

from blnk_sdk.http_client import format_response
from blnk_sdk.services.balance_monitors import BalanceMonitor
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest


def _args(captured: CapturingRequest) -> list:
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


# --------------------------------------------------------------------------- #
# POST BalanceMonitor


def test_create_balance_monitor() -> None:
    """Create Balance Monitor"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)
    id = "1234567890"
    data = {
        "balance_id": id,
        "condition": {
            "field": "debit_balance",
            "operator": "<",
            "value": 500,
            "precision": 100,
        },
    }

    response = balance_monitor.create(data)

    assert response.status == 201
    assert response.data["balance_id"] == data["balance_id"]
    assert _args(captured_request) == [("balance-monitors", data, "POST")]
    # data is passed by reference, unmodified
    assert captured_request.calls[0][1] is data


def test_it_should_handle_missing_fields() -> None:
    """It should handle missing fields"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)
    data = {
        "condition": {
            "field": "debit_balance",
            "operator": "<",
            "value": 500,
            "precision": 100,
        },
    }

    response = balance_monitor.create(data)

    assert response.status == 400
    assert response.data is None
    assert _args(captured_request) == []


def test_it_should_handle_invalid_fields() -> None:
    """It should handle invalid fields"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)
    id = "1234567890"
    data = {
        "balance_id": id,
        "condition": {
            "field": "debit_balance",
            "operator": "<",
            "value": "500",
            "precision": 100,
        },
    }

    response = balance_monitor.create(data)

    assert response.status == 400
    assert response.data is None
    assert _args(captured_request) == []


# --------------------------------------------------------------------------- #
# GET BalanceMonitor


def test_get_balance_monitor() -> None:
    """Get Balance Monitor"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)
    id = "1234567890"

    response = balance_monitor.get(id)

    assert response.status == 200
    assert _args(captured_request) == [(f"balance-monitors/{id}", None, "GET")]


def test_list_balance_monitors() -> None:
    """List Balance Monitors"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)

    response = balance_monitor.list()

    assert response.status == 200
    assert _args(captured_request) == [("balance-monitors", None, "GET")]


# --------------------------------------------------------------------------- #
# PUT BalanceMonitor


def test_it_should_update_a_balance_monitor() -> None:
    """It should update a balance monitor"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)
    id = "12345678"
    data = {
        "balance_id": id,
        "condition": {
            "field": "debit_balance",
            "operator": "<",
            "value": 500,
            "precision": 100,
        },
    }

    response = balance_monitor.update(id, data)

    assert response.status == 200
    assert response.data["balance_id"] == data["balance_id"]
    assert _args(captured_request) == [(f"balance-monitors/{id}", data, "PUT")]


def test_it_should_handle_missing_fields_put() -> None:
    """It should handle missing fields (PUT parent)"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    balance_monitor = BalanceMonitor(captured_request, mock_logger, format_response)
    id = "1234567890"
    data = {
        "condition": {
            "field": "debit_balance",
            "operator": "<",
            "value": 500,
            "precision": 100,
        },
    }

    response = balance_monitor.update(id, data)

    assert response.status == 400
    assert response.data is None
    assert _args(captured_request) == []
