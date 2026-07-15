"""Unit tests for the LedgerBalances service: create, lineage, indicator
lookups, identity updates, snapshots, and point-in-time balance reads.

Note: a few assert failure labels do not match the status they assert
(status 201 labelled `Response is 200`, status 400 labelled `Response is
500`). They are failure diagnostics only and are intentionally left
as-is.

One mock logger is created at module scope and shared by all tests.
"""

from __future__ import annotations

from blnk_sdk.http_client import format_response
from blnk_sdk.services.ledger_balances import LedgerBalances
from blnk_sdk.uri_utils import percent_encode
from tests.mocks.blnk_client_mocks import (
    LEDGER_ID,
    create_mock_blnk_request,
    create_mock_logger,
)
from tests.mocks.capture import CapturingRequest

MOCK_LOGGER = create_mock_logger()


def test_it_should_create_a_ledger_balance_when_valid_data_is_provided() -> None:
    """it should create a ledger balance when valid data is provided"""
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)

    data = {
        "currency": "USD",
        "ledger_id": LEDGER_ID,
        "meta_data": {
            "company_name": "Test Company",
        },
    }

    response = ledger_balance.create(data)

    # verify that the request function was called and with the right parameters
    assert captured_request.calls == [
        (
            "balances",
            {
                "currency": "USD",
                "ledger_id": LEDGER_ID,
                "meta_data": {
                    "company_name": "Test Company",
                },
            },
            "POST",
            None,
        )
    ]
    assert response.status == 201, "Response is 201"
    assert response.data["ledger_id"] == LEDGER_ID


def test_it_should_handle_missing_optional_fields() -> None:
    """it should handle missing optional fields"""
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)

    data = {
        "currency": "USD",
        "ledger_id": LEDGER_ID,
        "meta_data": {
            "company_name": "Test Company",
        },
    }

    response = ledger_balance.create(data)

    # verify that the request function was called and with the right parameters
    assert captured_request.calls == [
        (
            "balances",
            {
                "currency": "USD",
                "ledger_id": "123456",
                "meta_data": {
                    "company_name": "Test Company",
                },
            },
            "POST",
            None,
        )
    ]
    assert response.status == 201, "Response is 200"  # mismatched label, see module docstring
    # identity_id was not provided, so the key must be absent from the response
    assert "identity_id" not in response.data


def test_it_should_handle_missing_required_fields() -> None:
    """it should handle missing required fields"""
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)

    # simulates a developer passing in any and missing required data types
    data = {
        "currency": "USD",
        "meta_data": {
            "company_name": "Test Company",
        },
    }

    response = ledger_balance.create(data)

    # request won't get called since this fails validation, so we use empty
    # list to compare the captured args
    assert captured_request.calls == []
    assert response.status == 400, "Response is 500"  # mismatched label, see module docstring
    assert response.data is None


def test_it_should_handle_thrown_during_balance_creation() -> None:
    """it should handle thrown during balance creation"""
    third_party_request = create_mock_blnk_request(True, "Network Error")
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)

    data = {
        "currency": "USD",
        "ledger_id": LEDGER_ID,
        "meta_data": {
            "company_name": "Test Company",
        },
    }

    response = ledger_balance.create(data)

    # request WAS called (then threw)
    assert captured_request.calls == [("balances", data, "POST", None)]

    assert response.status == 500, "Response is 500"
    assert response.data is None
    assert response.message == "Network Error"


def test_create_forwards_track_fund_lineage_and_allocation_strategy() -> None:
    """create forwards track_fund_lineage and allocation_strategy"""
    third_party_request = create_mock_blnk_request(True, None, 201)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)

    data = {
        "ledger_id": LEDGER_ID,
        "identity_id": "idt_3b63c8da-af29-4cc3-ad38-df17d87456e6",
        "currency": "USD",
        "track_fund_lineage": True,
        "allocation_strategy": "PROPORTIONAL",
    }

    response = ledger_balance.create(data)

    assert captured_request.calls == [
        (
            "balances",
            {
                "ledger_id": LEDGER_ID,
                "identity_id": "idt_3b63c8da-af29-4cc3-ad38-df17d87456e6",
                "currency": "USD",
                "track_fund_lineage": True,
                "allocation_strategy": "PROPORTIONAL",
            },
            "POST",
            None,
        )
    ]
    assert response.status == 201


def test_create_rejects_invalid_allocation_strategy() -> None:
    """create rejects invalid allocation_strategy"""
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)

    data = {
        "ledger_id": LEDGER_ID,
        "currency": "USD",
        "allocation_strategy": "INVALID",
    }

    response = ledger_balance.create(data)

    assert captured_request.calls == []
    assert response.status == 400
    assert (
        response.message
        == "allocation_strategy must be one of FIFO, LIFO, or PROPORTIONAL"
    )


def test_it_should_handle_meta_data_if_it_is_not_an_object() -> None:
    """it should handle meta_data if it is not an object"""
    third_party_request = create_mock_blnk_request(True)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)

    # a data type for meta_data that doesn't meet the object requirement
    data = {
        "currency": "USD",
        "ledger_id": LEDGER_ID,
        "meta_data": 5,
    }

    response = ledger_balance.create(data)

    # verify that the request function was never called
    assert captured_request.calls == []

    assert response.status == 400, "Response is 400"
    assert response.data is None
    assert response.message == "meta_data must be a valid object if provided"


def test_getlineage_calls_correct_endpoint() -> None:
    """getLineage calls correct endpoint"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    response = ledger_balance.get_lineage(balance_id)

    assert captured_request.calls == [
        (f"balances/{balance_id}/lineage", None, "GET", None)
    ]
    assert response.status == 200


def test_getlineage_rejects_empty_balance_id() -> None:
    """getLineage rejects empty balance id"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.get_lineage("")

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "balance id is required"


def test_getbyindicator_calls_correct_endpoint() -> None:
    """getByIndicator calls correct endpoint"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    indicator = "@World"
    currency = "USD"
    response = ledger_balance.get_by_indicator(indicator, currency)

    assert captured_request.calls == [
        (
            f"balances/indicator/{percent_encode(indicator)}"
            f"/currency/{percent_encode(currency)}",
            None,
            "GET",
            None,
        )
    ]
    assert response.status == 200


def test_getbyindicator_path_escapes_special_characters() -> None:
    """getByIndicator path-escapes special characters"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    indicator = "@user/name"
    currency = "USD/EUR"
    ledger_balance.get_by_indicator(indicator, currency)

    assert captured_request.calls == [
        (
            f"balances/indicator/{percent_encode(indicator)}"
            f"/currency/{percent_encode(currency)}",
            None,
            "GET",
            None,
        )
    ]


def test_getbyindicator_rejects_empty_indicator() -> None:
    """getByIndicator rejects empty indicator"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.get_by_indicator("", "USD")

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "indicator is required"


def test_getbyindicator_rejects_empty_currency() -> None:
    """getByIndicator rejects empty currency"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.get_by_indicator("@World", "")

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "currency is required"


def test_updateidentity_calls_put_balances_id_identity() -> None:
    """updateIdentity calls PUT /balances/{id}/identity"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    data = {"identity_id": "idt_3b63c8da-af29-4cc3-ad38-df17d87456e6"}
    response = ledger_balance.update_identity(balance_id, data)

    assert captured_request.calls == [
        (f"balances/{balance_id}/identity", data, "PUT", None)
    ]
    assert response.status == 200


def test_updateidentity_rejects_empty_balance_id() -> None:
    """updateIdentity rejects empty balance id"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.update_identity(
        "", {"identity_id": "idt_3b63c8da-af29-4cc3-ad38-df17d87456e6"}
    )

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "balance id is required"


def test_updateidentity_rejects_missing_identity_id() -> None:
    """updateIdentity rejects missing identity_id"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.update_identity("bln_123", {})

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "identity_id is required"


def test_createsnapshot_calls_post_balances_snapshots() -> None:
    """createSnapshot calls POST /balances-snapshots"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.create_snapshot()

    assert captured_request.calls == [("balances-snapshots", None, "POST", None)]
    assert response.status == 200


def test_createsnapshot_forwards_batch_size_query_param() -> None:
    """createSnapshot forwards batch_size query param"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    ledger_balance.create_snapshot({"batch_size": 500})

    assert captured_request.calls == [
        ("balances-snapshots?batch_size=500", None, "POST", None)
    ]


def test_createsnapshot_omits_query_when_batch_size_is_zero() -> None:
    """createSnapshot omits query when batch_size is zero"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    ledger_balance.create_snapshot({"batch_size": 0})

    assert captured_request.calls == [("balances-snapshots", None, "POST", None)]


def test_createsnapshot_rejects_negative_batch_size() -> None:
    """createSnapshot rejects negative batch_size"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.create_snapshot({"batch_size": -1})

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "batch_size must be positive"


def test_get_calls_get_balances_id() -> None:
    """get calls GET /balances/{id}"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    ledger_balance.get(balance_id)

    assert captured_request.calls == [(f"balances/{balance_id}", None, "GET", None)]


def test_get_forwards_from_source_query_param() -> None:
    """get forwards from_source query param"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    ledger_balance.get(balance_id, {"from_source": True})

    assert captured_request.calls == [
        (f"balances/{balance_id}?from_source=true", None, "GET", None)
    ]


def test_get_rejects_invalid_from_source() -> None:
    """get rejects invalid from_source"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.get("bln_123", {"from_source": "true"})

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "from_source must be a boolean if provided"


def test_get_forwards_with_queued_query_param() -> None:
    """get forwards with_queued query param"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    ledger_balance.get(balance_id, {"with_queued": True})

    assert captured_request.calls == [
        (f"balances/{balance_id}?with_queued=true", None, "GET", None)
    ]


def test_get_forwards_from_source_and_with_queued_query_params() -> None:
    """get forwards from_source and with_queued query params"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    ledger_balance.get(
        balance_id, {"from_source": True, "with_queued": True}
    )

    assert captured_request.calls == [
        (
            f"balances/{balance_id}?from_source=true&with_queued=true",
            None,
            "GET",
            None,
        )
    ]


def test_get_rejects_invalid_with_queued() -> None:
    """get rejects invalid with_queued"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.get("bln_123", {"with_queued": "true"})

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "with_queued must be a boolean if provided"


def test_getat_calls_get_balances_id_at() -> None:
    """getAt calls GET /balances/{id}/at"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    timestamp = "2025-02-24T08:55:26Z"
    ledger_balance.get_at(balance_id, {"timestamp": timestamp})

    assert captured_request.calls == [
        (
            f"balances/{balance_id}/at?timestamp={percent_encode(timestamp)}",
            None,
            "GET",
            None,
        )
    ]


def test_getat_forwards_from_source_query_param() -> None:
    """getAt forwards from_source query param"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    balance_id = "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    timestamp = "2025-02-24T08:55:26Z"
    ledger_balance.get_at(balance_id, {"timestamp": timestamp, "from_source": True})

    assert captured_request.calls == [
        (
            f"balances/{balance_id}/at"
            f"?timestamp={percent_encode(timestamp)}&from_source=true",
            None,
            "GET",
            None,
        )
    ]


def test_getat_rejects_empty_balance_id() -> None:
    """getAt rejects empty balance id"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.get_at("", {"timestamp": "2025-02-24T08:55:26Z"})

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "balance id is required"


def test_getat_rejects_empty_timestamp() -> None:
    """getAt rejects empty timestamp"""
    third_party_request = create_mock_blnk_request(True, None, 200)
    captured_request = CapturingRequest(third_party_request)
    ledger_balance = LedgerBalances(captured_request, MOCK_LOGGER, format_response)
    response = ledger_balance.get_at("bln_123", {"timestamp": ""})

    assert captured_request.calls == []
    assert response.status == 400
    assert response.message == "timestamp is required"
