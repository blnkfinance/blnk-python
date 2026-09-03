"""Unit tests for the Transactions service: create, status updates,
lookups by id/reference, lineage, refunds, queue recovery, and bulk
operations (create, commit-inflight, void-inflight).

Tests are grouped into blocks by operation; each docstring names the
case with its block. The two colliding `rejects missing transaction_id`
case names are disambiguated with their block's operation name
(`test_bulkcommitinflight_...` / `test_bulkvoidinflight_...`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.transactions import Transactions
from blnk_sdk.types.transactions import (
    MAX_BULK_CREATE_ITEMS,
    MAX_BULK_INFLIGHT_ITEMS,
    CreateTransactionResponse,
)
from tests.fixtures.core_create_transaction_response import (
    core_create_transaction_reference_response,
)
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger
from tests.mocks.capture import CapturingRequest


def _make(status=200, success=True, throw_error=None):
    """Build a Transactions service backed by a capturing mock request."""
    captured = CapturingRequest(create_mock_blnk_request(success, throw_error, status))
    service = Transactions(captured, create_mock_logger(), format_response)
    return service, captured


def _args(captured):
    """Return the (endpoint, data, method) triple of each captured request."""
    return [call[:3] for call in captured.calls]


# ---------------------------------------------------------------------------
# Block: Creates a transaction (mock success=True, status=201)
# ---------------------------------------------------------------------------


def test_creates_a_transaction_with_valid_data():
    """Creates a transaction > Creates a transaction with valid data"""
    service, captured = _make(201)
    data = {
        "amount": 10000,
        "currency": "USD",
        "description": "Test transaction",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "1234567890",
    }
    transaction = service.create(data)
    assert _args(captured) == [("transactions", data, "POST")]
    assert transaction.data["amount"] == data["amount"]
    assert transaction.data["currency"] == data["currency"]
    assert transaction.data["description"] == data["description"]


def test_creates_a_transaction_with_precise_amount_only():
    """Creates a transaction > Creates a transaction with precise_amount only"""
    service, captured = _make(201)
    data = {
        "precise_amount": 75000,
        "currency": "USD",
        "description": "Precise amount transaction",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "precise_ref_001",
        "source": "@FundingPool",
        "destination": "bln_recipient",
    }
    transaction = service.create(data)
    assert _args(captured) == [("transactions", data, "POST")]
    assert transaction.status == 201


def test_creates_a_transaction_with_iso_date_strings_unchanged():
    """Creates a transaction > Creates a transaction with ISO date strings unchanged"""
    service, captured = _make(201)
    data = {
        "amount": 10000,
        "currency": "USD",
        "description": "Scheduled inflight transaction",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "cap_41_ref_001",
        "source": "@FundingPool",
        "destination": "bln_recipient",
        "inflight": True,
        "scheduled_for": "2025-12-31T23:59:59Z",
        "inflight_expiry_date": "2025-08-01T08:00:00Z",
    }
    transaction = service.create(data)
    assert _args(captured) == [("transactions", data, "POST")]
    assert transaction.status == 201


def test_creates_a_transaction_with_decimal_distribution_split():
    """Creates a transaction > Creates a transaction with decimal distribution split"""
    service, captured = _make(201)
    data = {
        "amount": 1000,
        "currency": "USD",
        "description": "Decimal distribution split",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "cap_41_ref_002",
        "source": "@FundingPool",
        "destinations": [
            {"identifier": "bln_fee", "distribution": "240.23"},
            {"identifier": "bln_recipient", "distribution": "left"},
        ],
    }
    transaction = service.create(data)
    assert _args(captured) == [("transactions", data, "POST")]
    assert transaction.status == 201


def test_forwards_atomic_on_split_transaction_create():
    """Creates a transaction > forwards atomic on split transaction create"""
    service, captured = _make(201)
    data = {
        "amount": 1000,
        "currency": "USD",
        "description": "Atomic split transaction",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "cap_5_atomic_split",
        "source": "@FundingPool",
        "destinations": [
            {"identifier": "bln_fee", "distribution": "240.23"},
            {"identifier": "bln_recipient", "distribution": "left"},
        ],
        "atomic": True,
        "skip_queue": True,
    }
    transaction = service.create(data)
    assert _args(captured) == [("transactions", data, "POST")]
    assert transaction.status == 201


def test_rejects_invalid_atomic_on_create():
    """Creates a transaction > rejects invalid atomic on create"""
    service, captured = _make(201)
    data = {
        "amount": 1000,
        "currency": "USD",
        "description": "Invalid atomic",
        "precision": 100,
        "reference": "cap_5_bad_atomic",
        "source": "@FundingPool",
        "destinations": [
            {"identifier": "bln_fee", "distribution": "50%"},
            {"identifier": "bln_recipient", "distribution": "left"},
        ],
        "atomic": "true",
    }
    response = service.create(data)
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "atomic must be a boolean if provided."


def test_creates_a_transaction_with_dry_run():
    """Creates a transaction > forwards dry_run on create"""
    service, captured = _make(200)
    data = {
        "amount": 10000,
        "currency": "USD",
        "description": "Dry-run preview",
        "precision": 100,
        "reference": "dry_run_ref_001",
        "source": "@FundingPool",
        "destination": "bln_recipient",
        "dry_run": True,
    }
    transaction = service.create(data)
    assert _args(captured) == [("transactions", data, "POST")]
    assert transaction.status == 200


def test_returns_core_create_response_fields():
    """Creates a transaction > returns Core create response fields"""
    core_response = core_create_transaction_reference_response

    def response_returning_request(endpoint, data, method, header_options=None):
        return ApiResponse(status=201, message="Success", data=core_response)

    service = Transactions(
        response_returning_request, create_mock_logger(), format_response
    )
    data = {
        "amount": 1250.34,
        "currency": "USD",
        "description": "Card payment on Stripe",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "ref_2ye281ewiu-1e17-dh17-eh18728hd245",
        "source": "@WorldUSD",
        "destination": "@MyBalance",
        "allow_overdraft": False,
        "inflight": False,
    }
    transaction = service.create(data)
    assert transaction.status == 201
    assert transaction.data["hash"] == core_response["hash"]
    assert transaction.data["parent_transaction"] == core_response["parent_transaction"]
    assert transaction.data["allow_overdraft"] == core_response["allow_overdraft"]
    assert transaction.data["inflight"] == core_response["inflight"]
    assert transaction.data["scheduled_for"] == core_response["scheduled_for"]
    assert (
        transaction.data["inflight_expiry_date"]
        == core_response["inflight_expiry_date"]
    )
    assert (
        transaction.data["inflight_commit_date"]
        == core_response["inflight_commit_date"]
    )


def test_createtransactionresponse_type_includes_gap_fields():
    """Creates a transaction > CreateTransactionResponse type includes gap fields"""
    sample = CreateTransactionResponse.from_dict(
        {
            **core_create_transaction_reference_response,
            "meta_data": {"company_name": "Test Company"},
        }
    )
    assert sample.hash
    assert isinstance(sample.parent_transaction, str)
    assert isinstance(sample.allow_overdraft, bool)
    assert sample.inflight_expiry_date
    assert sample.inflight_commit_date
    assert sample.scheduled_for


def test_creates_a_transaction_with_newer_core_fields_and_serializes_dates():
    """Creates a transaction > Creates a transaction with the newer Core fields and serializes dates"""
    service, captured = _make(201)
    effective_date = datetime(2025, 2, 15, 10, 30, tzinfo=timezone.utc)
    data = {
        "amount": 10000,
        "currency": "USD",
        "description": "Backdated skip-queue transaction",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "cap_40_ref_001",
        "source": "@FundingPool",
        "destination": "bln_recipient",
        "skip_queue": True,
        "effective_date": effective_date,
        "inflight_commit_date": "2025-06-01T12:00:00Z",
    }
    transaction = service.create(data)
    assert _args(captured) == [
        (
            "transactions",
            {**data, "effective_date": "2025-02-15T10:30:00Z"},
            "POST",
        )
    ]
    assert transaction.status == 201


def test_it_should_handle_missing_required_fields():
    """Creates a transaction > It should handle missing required fields"""
    service, captured = _make(201)
    data = {
        "currency": "USD",
        "description": "Test transaction",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "amount": 10000,
    }
    response = service.create(data)
    assert _args(captured) == []
    assert response.data is None
    assert response.status == 400


def test_it_should_handle_thrown_errors_during_creation():
    """Creates a transaction > it should handle thrown errors during creation"""
    service, captured = _make(success=False, throw_error="Something went wrong")
    data = {
        "amount": 10000,
        "currency": "USD",
        "description": "Test transaction",
        "meta_data": {"company_name": "Test Company"},
        "precision": 100,
        "reference": "1234567890",
    }
    response = service.create(data)
    assert _args(captured) == [("transactions", data, "POST")]
    assert response.data is None
    assert response.status == 500
    assert response.message == "Something went wrong"


def test_it_should_handle_meta_data_if_it_is_not_an_object():
    """Creates a transaction > it should handle meta_data if it is not an object"""
    service, captured = _make(success=False, throw_error="Something went wrong")
    data = {
        "amount": 10000,
        "currency": "USD",
        "description": "Test transaction",
        "meta_data": "Test Company",
        "precision": 100,
        "reference": "1234567890",
    }
    response = service.create(data)
    assert _args(captured) == []
    assert response.data is None
    assert response.status == 400
    assert response.message == "meta_data must be a valid object if provided"


# ---------------------------------------------------------------------------
# Block: Updates a transaction (mock success=True, status=200; id = "1234")
# ---------------------------------------------------------------------------


def test_updates_a_transaction_status_with_valid_data():
    """Updates a transaction > Updates a transaction status with valid data"""
    service, captured = _make(200)
    data = {"status": "commit"}
    transaction = service.update_status("1234", data)
    assert _args(captured) == [("transactions/inflight/1234", data, "PUT")]
    assert transaction.status == 200


def test_partial_commit_forwards_precise_amount():
    """Updates a transaction > Partial commit forwards precise_amount"""
    service, captured = _make(200)
    data = {"status": "commit", "precise_amount": 50000}
    transaction = service.update_status("1234", data)
    assert _args(captured) == [("transactions/inflight/1234", data, "PUT")]
    assert transaction.status == 200


def test_updates_fails_for_a_transaction_status_with_invalid_data():
    """Updates a transaction > Updates fails for a transaction status with invalid data"""
    service, captured = _make(200)
    data = {"status": "commit", "meta_data": "Test Company"}
    transaction = service.update_status("1234", data)
    assert _args(captured) == []
    assert transaction.data is None
    assert transaction.status == 400


def test_updatestatus_forwards_skip_queue_on_request():
    """Updates a transaction > updateStatus forwards skip_queue on request"""
    service, captured = _make(200)
    data = {"status": "commit", "skip_queue": True}
    transaction = service.update_status("1234", data)
    assert _args(captured) == [("transactions/inflight/1234", data, "PUT")]
    assert transaction.status == 200


def test_updatestatus_rejects_invalid_skip_queue():
    """Updates a transaction > updateStatus rejects invalid skip_queue"""
    service, captured = _make(200)
    data = {"status": "commit", "skip_queue": "true"}
    transaction = service.update_status("1234", data)
    assert _args(captured) == []
    assert transaction.status == 400
    assert "skip_queue must be a boolean if provided" in transaction.message


def test_updatestatus_forwards_dry_run_on_request():
    """Updates a transaction > updateStatus forwards dry_run on request"""
    service, captured = _make(200)
    data = {"status": "commit", "dry_run": True}
    transaction = service.update_status("1234", data)
    assert _args(captured) == [("transactions/inflight/1234", data, "PUT")]
    assert transaction.status == 200


# ---------------------------------------------------------------------------
# Block: GET transaction by id (mock success=True, status=200)
# ---------------------------------------------------------------------------


def test_get_calls_correct_endpoint():
    """GET transaction by id > get calls correct endpoint"""
    service, captured = _make(200)
    transaction_id = "txn_cap12_abc123"
    response = service.get(transaction_id)
    assert _args(captured) == [(f"transactions/{transaction_id}", None, "GET")]
    assert response.status == 200


def test_get_rejects_empty_transaction_id():
    """GET transaction by id > get rejects empty transaction id"""
    service, captured = _make(200)
    response = service.get("")
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "transaction id is required"


# ---------------------------------------------------------------------------
# Block: GET transaction lineage (mock success=True, status=200)
# ---------------------------------------------------------------------------


def test_getlineage_calls_correct_endpoint():
    """GET transaction lineage > getLineage calls correct endpoint"""
    service, captured = _make(200)
    transaction_id = "txn_cap13_abc123"
    response = service.get_lineage(transaction_id)
    assert _args(captured) == [(f"transactions/{transaction_id}/lineage", None, "GET")]
    assert response.status == 200


def test_getlineage_rejects_empty_transaction_id():
    """GET transaction lineage > getLineage rejects empty transaction id"""
    service, captured = _make(200)
    response = service.get_lineage("")
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "transaction id is required"


# ---------------------------------------------------------------------------
# Block: POST recover queued transactions (mock success=True, status=200)
# ---------------------------------------------------------------------------


def test_recoverqueue_calls_default_endpoint():
    """POST recover queued transactions > recoverQueue calls default endpoint"""
    service, captured = _make(200)
    response = service.recover_queue()
    assert _args(captured) == [("transactions/recover", None, "POST")]
    assert response.status == 200


def test_recoverqueue_forwards_threshold_query_param():
    """POST recover queued transactions > recoverQueue forwards threshold query param"""
    service, captured = _make(200)
    response = service.recover_queue({"threshold": "5m"})
    assert _args(captured) == [("transactions/recover?threshold=5m", None, "POST")]
    assert response.status == 200


def test_recoverqueue_rejects_invalid_threshold_before_request():
    """POST recover queued transactions > recoverQueue rejects invalid threshold before request"""
    service, captured = _make(200)
    response = service.recover_queue({"threshold": "bogus"})
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "threshold must be a valid duration string (e.g. 5m, 1h)."


# ---------------------------------------------------------------------------
# Block: GET transaction by reference (mock success=True, status=200)
# ---------------------------------------------------------------------------


def test_getbyreference_calls_correct_endpoint():
    """GET transaction by reference > getByReference calls correct endpoint"""
    service, captured = _make(200)
    reference = "ref_cap14_abc123"
    response = service.get_by_reference(reference)
    assert _args(captured) == [
        (f"transactions/reference/{reference}", None, "GET")
    ]
    assert response.status == 200


def test_getbyreference_path_escapes_special_characters():
    """GET transaction by reference > getByReference path-escapes special characters"""
    service, captured = _make(200)
    reference = "ref/with space?query#hash%25"
    service.get_by_reference(reference)
    assert _args(captured) == [
        (
            "transactions/reference/ref%2Fwith%20space%3Fquery%23hash%2525",
            None,
            "GET",
        )
    ]


def test_getbyreference_rejects_empty_reference():
    """GET transaction by reference > getByReference rejects empty reference"""
    service, captured = _make(200)
    response = service.get_by_reference("")
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "reference is required"


# ---------------------------------------------------------------------------
# Block: Refunds a transaction (mock success=True, status=201; id below)
# ---------------------------------------------------------------------------


def test_refund_without_body_keeps_backward_compatible_call():
    """Refunds a transaction > refund without body keeps backward-compatible call"""
    service, captured = _make(201)
    refund_response = service.refund("txn_refund_1234")
    assert _args(captured) == [("refund-transaction/txn_refund_1234", None, "POST")]
    assert refund_response.status == 201


def test_refund_forwards_skip_queue_on_request_body():
    """Refunds a transaction > refund forwards skip_queue on request body"""
    service, captured = _make(201)
    options = {"skip_queue": True}
    refund_response = service.refund("txn_refund_1234", options)
    assert _args(captured) == [
        ("refund-transaction/txn_refund_1234", options, "POST")
    ]
    assert refund_response.status == 201


def test_refund_rejects_invalid_skip_queue():
    """Refunds a transaction > refund rejects invalid skip_queue"""
    service, captured = _make(201)
    refund_response = service.refund("txn_refund_1234", {"skip_queue": "true"})
    assert _args(captured) == []
    assert refund_response.status == 400
    assert refund_response.message == "skip_queue must be a boolean if provided."


def test_refund_forwards_description_meta_data_and_dry_run():
    """Refunds a transaction > refund forwards description, meta_data, and dry_run"""
    service, captured = _make(200)
    options = {
        "description": "Card refund",
        "meta_data": {"reason": "chargeback"},
        "dry_run": True,
    }
    refund_response = service.refund("txn_refund_1234", options)
    assert _args(captured) == [
        ("refund-transaction/txn_refund_1234", options, "POST")
    ]
    assert refund_response.status == 200


# ---------------------------------------------------------------------------
# Block: Creates bulk transactions (mock success=True, status=201)
# ---------------------------------------------------------------------------


def test_creates_bulk_transactions_with_valid_data():
    """Creates bulk transactions > Creates bulk transactions with valid data"""
    service, captured = _make(201)
    data = {
        "atomic": True,
        "inflight": False,
        "run_async": False,
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": "Test transaction 1",
                "meta_data": {"department": "sales", "project": "Q4_campaign"},
                "precision": 100,
                "reference": "bulk_txn_001",
                "source": "@source_account_1",
                "destination": "@destination_account_1",
            },
            {
                "amount": 2000,
                "currency": "USD",
                "description": "Test transaction 2",
                "meta_data": {"department": "marketing", "project": "Q4_campaign"},
                "precision": 100,
                "reference": "bulk_txn_002",
                "source": "@source_account_2",
                "destination": "@destination_account_2",
            },
        ],
    }
    bulk_response = service.create_bulk(data)
    assert _args(captured) == [("transactions/bulk", data, "POST")]
    assert bulk_response.status == 201


def test_createbulk_serializes_date_fields_on_each_transaction():
    """Creates bulk transactions > createBulk serializes date fields on each transaction"""
    service, captured = _make(201)
    effective_date = datetime(2025, 2, 15, 10, 30, tzinfo=timezone.utc)
    scheduled_date = datetime(2025, 7, 1, 8, 0, tzinfo=timezone.utc)
    data = {
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": "Bulk txn with effective_date",
                "meta_data": {"department": "sales", "project": "Q4_campaign"},
                "precision": 100,
                "reference": "bulk_txn_date_001",
                "source": "@source_account_1",
                "destination": "@destination_account_1",
                "effective_date": effective_date,
                "inflight_commit_date": "2025-06-01T12:00:00Z",
            },
            {
                "amount": 2000,
                "currency": "USD",
                "description": "Bulk txn with scheduled_for",
                "meta_data": {"department": "marketing", "project": "Q4_campaign"},
                "precision": 100,
                "reference": "bulk_txn_date_002",
                "source": "@source_account_2",
                "destination": "@destination_account_2",
                "scheduled_for": scheduled_date,
                "skip_queue": True,
            },
        ],
    }
    bulk_response = service.create_bulk(data)
    assert _args(captured) == [
        (
            "transactions/bulk",
            {
                "transactions": [
                    {
                        **data["transactions"][0],
                        "effective_date": "2025-02-15T10:30:00Z",
                    },
                    {
                        **data["transactions"][1],
                        "scheduled_for": "2025-07-01T08:00:00Z",
                    },
                ],
            },
            "POST",
        )
    ]
    assert bulk_response.status == 201


def test_creates_basic_bulk_transactions_without_optional_flags():
    """Creates bulk transactions > Creates basic bulk transactions without optional flags"""
    service, captured = _make(201)
    data = {
        "transactions": [
            {
                "amount": 1500,
                "currency": "USD",
                "description": "Basic bulk transaction",
                "precision": 100,
                "reference": "basic_bulk_txn_001",
                "source": "@source_account",
                "destination": "@destination_account",
            },
        ],
    }
    bulk_response = service.create_bulk(data)
    assert _args(captured) == [("transactions/bulk", data, "POST")]
    assert bulk_response.status == 201


def test_should_handle_empty_transactions_array():
    """Creates bulk transactions > Should handle empty transactions array"""
    service, captured = _make(201)
    data = {"atomic": True, "transactions": []}
    response = service.create_bulk(data)
    assert _args(captured) == []
    assert response.data is None
    assert response.status == 400
    assert "Transactions array cannot be empty" in response.message


def test_should_handle_invalid_transaction_data_in_bulk():
    """Creates bulk transactions > Should handle invalid transaction data in bulk"""
    service, captured = _make(201)
    data = {
        "atomic": True,
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": "Valid transaction",
                "precision": 100,
                "reference": "valid_txn_001",
                "source": "@source_account",
                "destination": "@destination_account",
            },
            {
                # Missing required fields
                "amount": 2000,
                "currency": "USD",
                # missing description
                "precision": 100,
                "reference": "invalid_txn_002",
            },
        ],
    }
    response = service.create_bulk(data)
    assert _args(captured) == []
    assert response.data is None
    assert response.status == 400
    assert "Transaction at index 1:" in response.message


def test_should_handle_duplicate_references_in_bulk():
    """Creates bulk transactions > Should handle duplicate references in bulk"""
    service, captured = _make(201)
    data = {
        "atomic": True,
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": "Transaction 1",
                "precision": 100,
                "reference": "duplicate_ref",
                "source": "@source_account_1",
                "destination": "@destination_account_1",
            },
            {
                "amount": 2000,
                "currency": "USD",
                "description": "Transaction 2",
                "precision": 100,
                "reference": "duplicate_ref",  # Same reference as above
                "source": "@source_account_2",
                "destination": "@destination_account_2",
            },
        ],
    }
    response = service.create_bulk(data)
    assert _args(captured) == []
    assert response.data is None
    assert response.status == 400
    assert "All transactions must have unique references" in response.message


def test_should_handle_invalid_boolean_flags():
    """Creates bulk transactions > Should handle invalid boolean flags"""
    service, captured = _make(201)
    data = {
        "atomic": "true",  # Should be boolean, not string
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": "Test transaction",
                "precision": 100,
                "reference": "test_txn_001",
                "source": "@source_account",
                "destination": "@destination_account",
            },
        ],
    }
    response = service.create_bulk(data)
    assert _args(captured) == []
    assert response.data is None
    assert response.status == 400
    assert "Atomic must be a boolean if provided" in response.message


def test_should_handle_thrown_errors_during_bulk_creation():
    """Creates bulk transactions > Should handle thrown errors during bulk creation"""
    service, captured = _make(success=False, throw_error="Network error occurred")
    data = {
        "atomic": True,
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": "Test transaction",
                "precision": 100,
                "reference": "test_txn_001",
                "source": "@source_account",
                "destination": "@destination_account",
            },
        ],
    }
    response = service.create_bulk(data)
    assert _args(captured) == [("transactions/bulk", data, "POST")]
    assert response.data is None
    assert response.status == 500
    assert response.message == "Network error occurred"


def test_should_handle_bulk_transactions_with_multiple_sources():
    """Creates bulk transactions > Should handle bulk transactions with multiple sources"""
    service, captured = _make(201)
    data = {
        "atomic": False,
        "transactions": [
            {
                "amount": 10000,
                "currency": "USD",
                "description": "Multi-source transaction",
                "precision": 100,
                "reference": "multi_source_txn_001",
                "sources": [
                    {
                        "identifier": "@source_account_1",
                        "distribution": "60%",
                        "narration": "Primary source",
                    },
                    {
                        "identifier": "@source_account_2",
                        "distribution": "40%",
                        "narration": "Secondary source",
                    },
                ],
                "destination": "@destination_account",
            },
        ],
    }
    bulk_response = service.create_bulk(data)
    assert _args(captured) == [("transactions/bulk", data, "POST")]
    assert bulk_response.status == 201


def test_createbulk_forwards_dry_run_on_bulk_request():
    """Creates bulk transactions > createBulk forwards dry_run on bulk request"""
    service, captured = _make(200)
    data = {
        "dry_run": True,
        "transactions": [
            {
                "amount": 100,
                "currency": "USD",
                "description": "Bulk dry-run",
                "precision": 100,
                "reference": "bulk_dry_001",
                "source": "@FundingPool",
                "destination": "@Recipient",
            }
        ],
    }
    response = service.create_bulk(data)
    assert _args(captured) == [("transactions/bulk", data, "POST")]
    assert response.status == 200


def test_createbulk_forwards_skip_queue_on_bulk_request():
    """Creates bulk transactions > createBulk forwards skip_queue on bulk request"""
    service, captured = _make(201)
    data = {
        "skip_queue": True,
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": "Bulk txn with skip_queue",
                "meta_data": {"department": "sales", "project": "Q4_campaign"},
                "precision": 100,
                "reference": "bulk_skip_queue_001",
                "source": "@source_account_1",
                "destination": "@destination_account_1",
            },
            {
                "amount": 2000,
                "currency": "USD",
                "description": "Bulk txn 2",
                "meta_data": {"department": "marketing", "project": "Q4_campaign"},
                "precision": 100,
                "reference": "bulk_skip_queue_002",
                "source": "@source_account_2",
                "destination": "@destination_account_2",
            },
        ],
    }
    bulk_response = service.create_bulk(data)
    assert _args(captured) == [("transactions/bulk", data, "POST")]
    assert bulk_response.status == 201


def test_createbulk_rejects_oversized_transactions_array():
    """Creates bulk transactions > createBulk rejects oversized transactions array"""
    service, captured = _make(201)
    data = {
        "transactions": [
            {
                "amount": 1000,
                "currency": "USD",
                "description": f"Bulk txn {i}",
                "precision": 100,
                "reference": f"bulk_max_ref_{i}",
                "source": "@source_account",
                "destination": "@destination_account",
            }
            for i in range(MAX_BULK_CREATE_ITEMS + 1)
        ],
    }
    response = service.create_bulk(data)
    assert _args(captured) == []
    assert response.data is None
    assert response.status == 400
    assert f"Too many transactions; max is {MAX_BULK_CREATE_ITEMS}." in response.message


# ---------------------------------------------------------------------------
# Block: bulkCommitInflight (mock success=True, status=200)
# ---------------------------------------------------------------------------


def test_commits_inflight_transactions_with_valid_data():
    """bulkCommitInflight > commits inflight transactions with valid data"""
    service, captured = _make(200)
    data = {
        "transactions": [
            {"transaction_id": "txn_11111111-1111-4111-8111-111111111111"},
            {
                "transaction_id": "txn_22222222-2222-4222-8222-222222222222",
                "amount": 40,
            },
            {
                "transaction_id": "txn_33333333-3333-4333-8333-333333333333",
                "precise_amount": 125034,
            },
        ],
    }
    response = service.bulk_commit_inflight(data)
    assert _args(captured) == [("transactions/inflight/bulk/commit", data, "POST")]
    assert response.status == 200


def test_rejects_empty_transactions_array():
    """bulkCommitInflight > rejects empty transactions array"""
    service, captured = _make(200)
    response = service.bulk_commit_inflight({"transactions": []})
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "Transactions array cannot be empty."


def test_rejects_too_many_transactions():
    """bulkCommitInflight > rejects too many transactions"""
    service, captured = _make(200)
    items = [{"transaction_id": "txn_test"} for _ in range(MAX_BULK_INFLIGHT_ITEMS + 1)]
    response = service.bulk_commit_inflight({"transactions": items})
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == f"Too many transactions; max is {MAX_BULK_INFLIGHT_ITEMS}."


def test_bulkcommitinflight_rejects_missing_transaction_id():
    """bulkCommitInflight > rejects missing transaction_id"""
    service, captured = _make(200)
    response = service.bulk_commit_inflight({"transactions": [{"transaction_id": ""}]})
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "transaction_id is required at index 0."


def test_bulkcommitinflight_forwards_dry_run_on_request():
    """bulkCommitInflight > bulkCommitInflight forwards dry_run on request"""
    service, captured = _make(200)
    data = {
        "dry_run": True,
        "transactions": [
            {"transaction_id": "txn_11111111-1111-4111-8111-111111111111"},
        ],
    }
    response = service.bulk_commit_inflight(data)
    assert _args(captured) == [("transactions/inflight/bulk/commit", data, "POST")]
    assert response.status == 200


def test_bulkcommitinflight_forwards_skip_queue_on_request():
    """bulkCommitInflight > bulkCommitInflight forwards skip_queue on request"""
    service, captured = _make(200)
    data = {
        "skip_queue": True,
        "transactions": [
            {"transaction_id": "txn_11111111-1111-4111-8111-111111111111"},
        ],
    }
    response = service.bulk_commit_inflight(data)
    assert _args(captured) == [("transactions/inflight/bulk/commit", data, "POST")]
    assert response.status == 200


# ---------------------------------------------------------------------------
# Block: bulkVoidInflight (mock success=True, status=200)
# ---------------------------------------------------------------------------


def test_voids_inflight_transactions_with_valid_data():
    """bulkVoidInflight > voids inflight transactions with valid data"""
    service, captured = _make(200)
    data = {
        "transaction_ids": [
            "txn_11111111-1111-4111-8111-111111111111",
            "txn_22222222-2222-4222-8222-222222222222",
        ],
    }
    response = service.bulk_void_inflight(data)
    assert _args(captured) == [("transactions/inflight/bulk/void", data, "POST")]
    assert response.status == 200


def test_rejects_empty_transaction_ids_array():
    """bulkVoidInflight > rejects empty transaction_ids array"""
    service, captured = _make(200)
    response = service.bulk_void_inflight({"transaction_ids": []})
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "transaction_ids array cannot be empty."


def test_rejects_too_many_transaction_ids():
    """bulkVoidInflight > rejects too many transaction_ids"""
    service, captured = _make(200)
    transaction_ids = ["txn_test" for _ in range(MAX_BULK_INFLIGHT_ITEMS + 1)]
    response = service.bulk_void_inflight({"transaction_ids": transaction_ids})
    assert _args(captured) == []
    assert response.status == 400
    assert (
        response.message == f"Too many transaction_ids; max is {MAX_BULK_INFLIGHT_ITEMS}."
    )


def test_bulkvoidinflight_rejects_missing_transaction_id():
    """bulkVoidInflight > rejects missing transaction_id"""
    service, captured = _make(200)
    response = service.bulk_void_inflight({"transaction_ids": [""]})
    assert _args(captured) == []
    assert response.status == 400
    assert response.message == "transaction_id is required at index 0."


def test_bulkvoidinflight_forwards_dry_run_on_request():
    """bulkVoidInflight > bulkVoidInflight forwards dry_run on request"""
    service, captured = _make(200)
    data = {
        "dry_run": True,
        "transaction_ids": ["txn_11111111-1111-4111-8111-111111111111"],
    }
    response = service.bulk_void_inflight(data)
    assert _args(captured) == [("transactions/inflight/bulk/void", data, "POST")]
    assert response.status == 200


def test_bulkvoidinflight_forwards_skip_queue_on_request():
    """bulkVoidInflight > bulkVoidInflight forwards skip_queue on request"""
    service, captured = _make(200)
    data = {
        "skip_queue": True,
        "transaction_ids": ["txn_11111111-1111-4111-8111-111111111111"],
    }
    response = service.bulk_void_inflight(data)
    assert _args(captured) == [("transactions/inflight/bulk/void", data, "POST")]
    assert response.status == 200
