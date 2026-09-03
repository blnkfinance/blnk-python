"""Unit tests for Core 0.15.3 dry-run preview types."""

from __future__ import annotations

from blnk_sdk.types.transactions import (
    BulkTransactionPreview,
    TransactionPreview,
    is_bulk_transaction_preview,
    is_transaction_preview,
)


def test_accepts_a_create_dry_run_preview():
    preview = TransactionPreview.from_dict(
        {
            "dry_run": True,
            "would_apply": True,
            "status": "APPLIED",
            "reference": "ref_card_settle_4821",
            "currency": "USD",
            "amount": 120,
            "precise_amount": "12000",
            "precision": 100,
            "balances": [
                {
                    "balance_id": "bln_source",
                    "role": "source",
                    "currency": "USD",
                    "current_balance": "50000",
                    "resulting_balance": "38000",
                    "virtual": False,
                },
                {
                    "balance_id": "bln_dest",
                    "role": "destination",
                    "currency": "USD",
                    "current_balance": "0",
                    "resulting_balance": "12000",
                },
            ],
        }
    )

    assert preview.dry_run is True
    assert preview.would_apply is True
    assert preview.balances[0].resulting_balance == "38000"
    assert preview.balances[0].virtual is False
    assert is_transaction_preview(preview)
    assert not is_bulk_transaction_preview(preview)


def test_accepts_a_rejected_preview():
    preview = TransactionPreview.from_dict(
        {
            "dry_run": True,
            "would_apply": False,
            "rejection": {
                "code": "TXN_INSUFFICIENT_FUNDS",
                "reason": "insufficient_funds",
                "message": "insufficient funds in source balance",
            },
            "currency": "USD",
            "amount": 120,
            "precise_amount": "12000",
            "precision": 100,
            "balances": [],
        }
    )

    assert preview.would_apply is False
    assert preview.rejection is not None
    assert preview.rejection.code == "TXN_INSUFFICIENT_FUNDS"
    assert preview.status is None


def test_accepts_an_inflight_preview_with_operation():
    preview = TransactionPreview.from_dict(
        {
            "dry_run": True,
            "would_apply": True,
            "operation": "commit",
            "status": "APPLIED",
            "currency": "USD",
            "amount": 50,
            "precise_amount": "5000",
            "precision": 100,
            "balances": [],
        }
    )

    assert preview.operation == "commit"


def test_accepts_a_bulk_dry_run_preview():
    preview = BulkTransactionPreview.from_dict(
        {
            "dry_run": True,
            "would_apply": True,
            "cumulative": False,
            "atomic": False,
            "results": [
                {
                    "dry_run": True,
                    "would_apply": True,
                    "operation": "commit",
                    "currency": "USD",
                    "amount": 50,
                    "precise_amount": "5000",
                    "precision": 100,
                    "balances": [],
                }
            ],
        }
    )

    assert preview.dry_run is True
    assert preview.cumulative is False
    assert preview.results[0].operation == "commit"
    assert is_bulk_transaction_preview(preview)
    assert is_bulk_transaction_preview(preview.to_dict())
    assert not is_transaction_preview(preview.to_dict())


def test_discriminators_treat_posted_transaction_as_not_a_preview():
    posted = {
        "transaction_id": "txn_123",
        "reference": "ref_001",
        "status": "APPLIED",
    }
    assert not is_transaction_preview(posted)
    assert not is_bulk_transaction_preview(posted)
