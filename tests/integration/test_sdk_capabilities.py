"""Integration tests for SDK capabilities — 22 cases, each exercised
against a live Blnk Core.

Requires Blnk Core at http://localhost:5001 (docker compose up in blnk/).
Skipped unless BLNK_E2E=1 — the same env var gates the e2e suite.

Uses a real blnk_init client authenticated with BLNK_API_KEY (env override;
default "blnk-local-dev-secret-change-me"), whereas the e2e suite runs with an
empty api key.
"""

from __future__ import annotations

import os

import pytest

from blnk_sdk.client import BlnkClientOptions, blnk_init
from tests.utils import (
    BASE_URL,
    BLNK_API_KEY,
    generate_random_numbers_with_prefix,
    sleep_seconds,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("BLNK_E2E") != "1",
    reason="requires live Blnk Core at http://localhost:5001/ (set BLNK_E2E=1)",
)

CLIENT_OPTIONS = BlnkClientOptions(base_url=BASE_URL)
CLIENT = blnk_init(BLNK_API_KEY, CLIENT_OPTIONS)

BASE_TXN = {
    "precision": 100,
    "currency": "USD",
    "description": "SDK integration test",
    "allow_overdraft": True,
}


def create_ledger(name: str) -> str:
    """Creates a ledger, asserts the create returned 201, and returns its
    ledger_id."""
    response = CLIENT.ledgers.create({"name": name})
    assert response.status == 201, f"ledger create {name}: {response.status}"
    return response.data["ledger_id"]


def create_balance(ledger_id: str) -> str:
    """Creates a USD balance on the ledger, asserts 201, and returns its
    balance_id."""
    response = CLIENT.ledger_balances.create(
        {"currency": "USD", "ledger_id": ledger_id, "meta_data": {}}
    )
    assert response.status == 201, f"balance create: {response.status}"
    return response.data["balance_id"]


# System.health
def test_system_health_returns_up() -> None:
    """System.health returns UP"""
    response = CLIENT.system.health()
    assert response.status == 200
    assert (response.data or {}).get("status") == "UP"


# Transactions.create with new Core fields
def test_skip_queue_effective_date() -> None:
    """skip_queue + effective_date"""
    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 1000,
            "reference": generate_random_numbers_with_prefix("cap40-skip", 6),
            "source": "@FundingPool",
            "destination": "@Recipient",
            "skip_queue": True,
            "effective_date": "2025-02-15T10:30:00Z",
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("skip_queue") is True
    assert (response.data or {}).get("effective_date") == "2025-02-15T10:30:00Z"


def test_inflight_commit_date_scheduled_for() -> None:
    """inflight_commit_date + scheduled_for"""
    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 1000,
            "reference": generate_random_numbers_with_prefix("cap40-dates", 6),
            "source": "@FundingPool",
            "destination": "@Recipient",
            "inflight": True,
            "inflight_expiry_date": "2026-12-31T23:59:59Z",
            "inflight_commit_date": "2024-04-22T15:28:03+00:00",
            "scheduled_for": "2025-12-31T23:59:59Z",
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


def test_transactions_create_bulk_serializes_date_fields() -> None:
    """Transactions.create_bulk serializes date fields"""
    response = CLIENT.transactions.create_bulk(
        {
            "transactions": [
                {
                    **BASE_TXN,
                    "amount": 500,
                    "reference": generate_random_numbers_with_prefix(
                        "cap40-bulk-1", 6
                    ),
                    "source": "@FundingPool",
                    "destination": "@Recipient",
                    "effective_date": "2025-02-15T10:30:00Z",
                    "inflight_commit_date": "2025-06-01T12:00:00Z",
                },
                {
                    **BASE_TXN,
                    "amount": 750,
                    "reference": generate_random_numbers_with_prefix(
                        "cap40-bulk-2", 6
                    ),
                    "source": "@FundingPool",
                    "destination": "@Recipient",
                    "scheduled_for": "2025-07-01T08:00:00Z",
                },
            ]
        }
    )

    assert response.status == 201
    bulk = response.data or {}
    assert bulk.get("transaction_count") == 2, "Core accepted 2 bulk transactions"
    assert bulk.get("batch_id"), "batch_id returned from Core"
    assert isinstance(bulk.get("status"), str), "status returned from Core"


# ISO date strings + decimal distributions
def test_decimal_distribution_240_23_iso_dates() -> None:
    """decimal distribution (240.23) + ISO dates"""
    ledger_id = create_ledger("Cap41 Ledger")
    dest_a = create_balance(ledger_id)
    dest_b = create_balance(ledger_id)

    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 1000,
            "reference": generate_random_numbers_with_prefix("cap41", 6),
            "source": "@FundingPool",
            "destinations": [
                {"identifier": dest_a, "distribution": "240.23"},
                {"identifier": dest_b, "distribution": "left"},
            ],
            "effective_date": "2024-04-22T15:28:03+00:00",
            "inflight_expiry_date": "2025-08-01T08:00:00Z",
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


# split-transaction validation
def test_multiple_sources_single_destination() -> None:
    """multiple sources → single destination"""
    ledger_id = create_ledger("Cap42 Sources")
    alice = create_balance(ledger_id)
    bob = create_balance(ledger_id)
    sarah = create_balance(ledger_id)
    destination = create_balance(ledger_id)

    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 30000,
            "reference": generate_random_numbers_with_prefix("cap42-src", 6),
            "sources": [
                {"identifier": alice, "distribution": "10%"},
                {"identifier": bob, "distribution": "20000"},
                {"identifier": sarah, "distribution": "left"},
            ],
            "destination": destination,
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


def test_single_source_multiple_destinations() -> None:
    """single source → multiple destinations"""
    ledger_id = create_ledger("Cap42 Dests")
    alice = create_balance(ledger_id)
    bob = create_balance(ledger_id)
    charlie = create_balance(ledger_id)
    source = create_balance(ledger_id)

    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 30000,
            "reference": generate_random_numbers_with_prefix("cap42-dest", 6),
            "source": source,
            "destinations": [
                {"identifier": alice, "distribution": "10%"},
                {"identifier": bob, "distribution": "20000"},
                {"identifier": charlie, "distribution": "left"},
            ],
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


def test_precise_distribution_legs() -> None:
    """precise_distribution legs"""
    ledger_id = create_ledger("Cap42 Precise")
    merchant = create_balance(ledger_id)
    fee = create_balance(ledger_id)

    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 10000,
            "reference": generate_random_numbers_with_prefix("cap42-precise", 6),
            "source": "@FundingPool",
            "destinations": [
                {"identifier": merchant, "precise_distribution": "9733"},
                {"identifier": fee, "precise_distribution": "267"},
            ],
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


def test_precise_amount_only_create() -> None:
    """precise_amount-only create"""
    ledger_id = create_ledger("Cap42 PreciseAmt")
    destination = create_balance(ledger_id)

    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "precise_amount": 75000,
            "reference": generate_random_numbers_with_prefix("cap42-pamt", 6),
            "source": "@FundingPool",
            "destination": destination,
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


def test_transactions_update_status_commit() -> None:
    """Transactions.update_status commit"""
    ledger_id = create_ledger("Cap42 Inflight")
    destination = create_balance(ledger_id)

    create_resp = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 5000,
            "reference": generate_random_numbers_with_prefix("cap42-inflight", 6),
            "source": "@FundingPool",
            "destination": destination,
            "inflight": True,
            "inflight_expiry_date": "2026-12-31T23:59:59Z",
        }
    )

    assert create_resp.status == 201
    sleep_seconds(2)

    commit_resp = CLIENT.transactions.update_status(
        create_resp.data["transaction_id"], {"status": "commit"}
    )
    assert commit_resp.status == 200


# CreateTransactionResponse completeness (hash, parent_transaction, inflight)
def test_create_response_includes_hash_parent_transaction_inflight() -> None:
    """create response includes hash, parent_transaction, inflight"""
    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 1000,
            "reference": generate_random_numbers_with_prefix("cap43-resp", 6),
            "source": "@FundingPool",
            "destination": "@Recipient",
            "allow_overdraft": False,
            "inflight": False,
        }
    )

    assert response.status == 201
    data = response.data or {}
    assert data.get("hash"), "hash present"
    assert len(data["hash"]) == 64, "hash is SHA-256 hex"
    assert isinstance(data.get("parent_transaction"), str)
    assert data.get("inflight") is False
    assert isinstance(data.get("allow_overdraft"), bool)
    assert data.get("scheduled_for") == "0001-01-01T00:00:00Z"
    assert data.get("inflight_expiry_date") == "0001-01-01T00:00:00Z"
    # Core omits inflight_commit_date when inflight is false
    if "inflight_commit_date" in data:
        assert isinstance(data["inflight_commit_date"], str)


# decimal percentage distributions with precise_amount
def test_decimal_percentage_split_33_33_66_67() -> None:
    """decimal percentage split (33.33% / 66.67%)"""
    ledger_id = create_ledger("Cap43 Ledger")
    dest_a = create_balance(ledger_id)
    dest_b = create_balance(ledger_id)

    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "precise_amount": 30000,
            "reference": generate_random_numbers_with_prefix("cap43", 6),
            "source": "@FundingPool",
            "destinations": [
                {"identifier": dest_a, "distribution": "33.33%"},
                {"identifier": dest_b, "distribution": "66.67%"},
            ],
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


def test_mixed_decimal_precise_distribution_left() -> None:
    """mixed decimal % + precise_distribution + left"""
    ledger_id = create_ledger("Cap43 Mixed")
    a = create_balance(ledger_id)
    b = create_balance(ledger_id)
    c = create_balance(ledger_id)

    response = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 30000,
            "reference": generate_random_numbers_with_prefix("cap43-mix", 6),
            "source": "@FundingPool",
            "destinations": [
                {"identifier": a, "distribution": "33.33%"},
                {"identifier": b, "precise_distribution": "5000"},
                {"identifier": c, "distribution": "left"},
            ],
        }
    )

    assert response.status == 201
    assert (response.data or {}).get("transaction_id")


# BulkTransactionResponse shape + skip_queue on bulk
def test_create_bulk_skip_queue_bulk_transaction_response_shape() -> None:
    """create_bulk skip_queue + BulkTransactionResponse shape"""
    response = CLIENT.transactions.create_bulk(
        {
            "skip_queue": True,
            "transactions": [
                {
                    **BASE_TXN,
                    "amount": 500,
                    "reference": generate_random_numbers_with_prefix(
                        "cap44-bulk-1", 6
                    ),
                    "source": "@FundingPool",
                    "destination": "@Recipient",
                },
                {
                    **BASE_TXN,
                    "amount": 750,
                    "reference": generate_random_numbers_with_prefix(
                        "cap44-bulk-2", 6
                    ),
                    "source": "@FundingPool",
                    "destination": "@Recipient",
                },
            ],
        }
    )

    assert response.status == 201
    bulk = response.data or {}
    assert bulk.get("batch_id"), "batch_id present"
    assert isinstance(bulk.get("status"), str), "status present"
    assert bulk.get("transaction_count") == 2, "transaction_count matches batch size"


# partial commit with precise_amount on update_status
def test_partial_commit_with_precise_amount() -> None:
    """partial commit with precise_amount"""
    ledger_id = create_ledger("Cap45 PartialCommit")
    destination = create_balance(ledger_id)

    create_resp = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 1000,
            "reference": generate_random_numbers_with_prefix("cap45-inflight", 6),
            "source": "@FundingPool",
            "destination": destination,
            "inflight": True,
            "inflight_expiry_date": "2026-12-31T23:59:59Z",
        }
    )

    assert create_resp.status == 201
    sleep_seconds(2)

    partial_commit_resp = CLIENT.transactions.update_status(
        create_resp.data["transaction_id"],
        {"status": "commit", "precise_amount": 50000, "skip_queue": True},
    )
    assert partial_commit_resp.status == 200
    assert (partial_commit_resp.data or {}).get("status") == "APPLIED"


# queued default + skip_queue on inflight commit/void
def test_update_status_queued_by_default() -> None:
    """update_status queued by default"""
    ledger_id = create_ledger("Cap117 QueuedCommit")
    destination = create_balance(ledger_id)

    create_resp = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 5000,
            "reference": generate_random_numbers_with_prefix("cap117-queued", 6),
            "source": "@FundingPool",
            "destination": destination,
            "inflight": True,
            "inflight_expiry_date": "2026-12-31T23:59:59Z",
        }
    )

    assert create_resp.status == 201
    sleep_seconds(2)

    commit_resp = CLIENT.transactions.update_status(
        create_resp.data["transaction_id"], {"status": "commit"}
    )
    assert commit_resp.status == 200
    assert (commit_resp.data or {}).get("queued") is True


def test_update_status_skip_queue_synchronous_commit() -> None:
    """update_status skip_queue synchronous commit"""
    ledger_id = create_ledger("Cap117 SyncCommit")
    destination = create_balance(ledger_id)

    create_resp = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 5000,
            "reference": generate_random_numbers_with_prefix("cap117-sync", 6),
            "source": "@FundingPool",
            "destination": destination,
            "inflight": True,
            "inflight_expiry_date": "2026-12-31T23:59:59Z",
        }
    )

    assert create_resp.status == 201
    sleep_seconds(2)

    commit_resp = CLIENT.transactions.update_status(
        create_resp.data["transaction_id"], {"status": "commit", "skip_queue": True}
    )
    assert commit_resp.status == 200
    assert (commit_resp.data or {}).get("status") == "APPLIED"


def test_bulk_commit_inflight_queued_vs_skip_queue() -> None:
    """bulk_commit_inflight queued vs skip_queue"""
    ledger_id = create_ledger("Cap117 BulkCommit")
    destination = create_balance(ledger_id)

    def create_inflight(ref_prefix: str) -> str:
        create_resp = CLIENT.transactions.create(
            {
                **BASE_TXN,
                "amount": 1000,
                "reference": generate_random_numbers_with_prefix(ref_prefix, 6),
                "source": "@FundingPool",
                "destination": destination,
                "inflight": True,
                "inflight_expiry_date": "2026-12-31T23:59:59Z",
            }
        )
        assert create_resp.status == 201
        return create_resp.data["transaction_id"]

    txn_queued = create_inflight("cap117-bulk-q")
    txn_sync = create_inflight("cap117-bulk-s")
    sleep_seconds(2)

    queued_resp = CLIENT.transactions.bulk_commit_inflight(
        {"transactions": [{"transaction_id": txn_queued}]}
    )
    assert queued_resp.status == 200
    assert (queued_resp.data or {}).get("results")[0].get("status") == "queued"

    sync_resp = CLIENT.transactions.bulk_commit_inflight(
        {"skip_queue": True, "transactions": [{"transaction_id": txn_sync}]}
    )
    assert sync_resp.status == 200
    assert (sync_resp.data or {}).get("results")[0].get("status") == "succeeded"


def test_bulk_void_inflight_queued_vs_skip_queue() -> None:
    """bulk_void_inflight queued vs skip_queue"""
    ledger_id = create_ledger("Cap117 BulkVoid")
    destination = create_balance(ledger_id)

    def create_inflight(ref_prefix: str) -> str:
        create_resp = CLIENT.transactions.create(
            {
                **BASE_TXN,
                "amount": 1000,
                "reference": generate_random_numbers_with_prefix(ref_prefix, 6),
                "source": "@FundingPool",
                "destination": destination,
                "inflight": True,
                "inflight_expiry_date": "2026-12-31T23:59:59Z",
            }
        )
        assert create_resp.status == 201
        return create_resp.data["transaction_id"]

    txn_queued = create_inflight("cap117-bulk-void-q")
    txn_sync = create_inflight("cap117-bulk-void-s")
    sleep_seconds(2)

    queued_resp = CLIENT.transactions.bulk_void_inflight(
        {"transaction_ids": [txn_queued]}
    )
    assert queued_resp.status == 200
    assert (queued_resp.data or {}).get("results")[0].get("status") == "queued"

    sync_resp = CLIENT.transactions.bulk_void_inflight(
        {"skip_queue": True, "transaction_ids": [txn_sync]}
    )
    assert sync_resp.status == 200
    assert (sync_resp.data or {}).get("results")[0].get("status") == "succeeded"


# get transaction by id
def test_get_returns_created_transaction() -> None:
    """get returns created transaction"""
    reference = generate_random_numbers_with_prefix("cap12-ref", 6)
    create_resp = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 500,
            "reference": reference,
            "source": "@FundingPool",
            "destination": "@Recipient",
        }
    )

    assert create_resp.status == 201
    transaction_id = create_resp.data["transaction_id"]
    assert transaction_id

    get_resp = CLIENT.transactions.get(transaction_id)
    assert get_resp.status == 200
    assert (get_resp.data or {}).get("transaction_id") == transaction_id
    assert (get_resp.data or {}).get("reference") == reference
    assert (get_resp.data or {}).get("currency") == "USD"
    amount = (get_resp.data or {}).get("amount")
    assert isinstance(amount, (int, float)) and not isinstance(amount, bool)


# get transaction by reference
def test_get_by_reference_returns_created_transaction() -> None:
    """get_by_reference returns created transaction"""
    reference = generate_random_numbers_with_prefix("cap14-ref", 6)
    create_resp = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 500,
            "reference": reference,
            "source": "@FundingPool",
            "destination": "@Recipient",
        }
    )

    assert create_resp.status == 201
    assert (create_resp.data or {}).get("transaction_id")

    get_resp = CLIENT.transactions.get_by_reference(reference)
    assert get_resp.status == 200
    assert (get_resp.data or {}).get("transaction_id") == create_resp.data.get(
        "transaction_id"
    )
    assert (get_resp.data or {}).get("reference") == reference
    assert (get_resp.data or {}).get("currency") == "USD"


# refund with optional skip_queue body
def test_refund_queued_vs_synchronous_skip_queue() -> None:
    """refund queued vs synchronous skip_queue"""
    ledger_id = create_ledger("Cap46 Refund")
    destination = create_balance(ledger_id)

    create_resp = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 500,
            "reference": generate_random_numbers_with_prefix("cap46-refund-src", 6),
            "source": "@FundingPool",
            "destination": destination,
            "skip_queue": True,
        }
    )

    assert create_resp.status == 201
    assert (create_resp.data or {}).get("status") == "APPLIED"
    original_txn_id = create_resp.data["transaction_id"]

    queued_refund_resp = CLIENT.transactions.refund(original_txn_id)
    assert queued_refund_resp.status == 201
    assert (queued_refund_resp.data or {}).get("transaction_id")
    assert (queued_refund_resp.data or {}).get("parent_transaction") == original_txn_id

    create_resp2 = CLIENT.transactions.create(
        {
            **BASE_TXN,
            "amount": 500,
            "reference": generate_random_numbers_with_prefix("cap46-refund-sync", 6),
            "source": "@FundingPool",
            "destination": destination,
            "skip_queue": True,
        }
    )

    assert create_resp2.status == 201
    original_txn_id2 = create_resp2.data["transaction_id"]

    sync_refund_resp = CLIENT.transactions.refund(
        original_txn_id2, {"skip_queue": True}
    )
    assert sync_refund_resp.status == 201
    assert (sync_refund_resp.data or {}).get("status") == "APPLIED"
    assert (sync_refund_resp.data or {}).get("parent_transaction") == original_txn_id2
