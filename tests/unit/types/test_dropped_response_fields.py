"""Unit tests for response fields dropped in Core 0.15.0
(4 cases under `Core 0.15.0 dropped response fields`).

Covers `CreateTransactionResponse`, `CreateLedgerBalanceResp`, and the
search documents: a dropped field either parses to None or is absent from
the dataclass entirely.
"""

from __future__ import annotations

from blnk_sdk.types.ledger_balances import CreateLedgerBalanceResp
from blnk_sdk.types.search import SearchBalanceDocument, SearchTransactionDocument
from blnk_sdk.types.transactions import CreateTransactionResponse


def test_createtransactionresponse_accepts_response_without_rate():
    """Core 0.15.0 dropped response fields > CreateTransactionResponse accepts response without rate"""
    response = CreateTransactionResponse.from_dict(
        {
            "transaction_id": "txn_test_123",
            "amount": 10,
            "precision": 100,
            "precise_amount": 1000,
            "reference": "ref_001",
            "description": "test",
            "currency": "USD",
            "status": "QUEUED",
            "hash": "0b9c25fb5b00d6c71cb4ca87026bf6dc316e63353d3330deb588bd0b3d74dcc0",
            "parent_transaction": "",
            "allow_overdraft": False,
            "inflight": False,
            "created_at": "2026-06-24T00:00:00Z",
            "scheduled_for": "0001-01-01T00:00:00Z",
            "inflight_expiry_date": "0001-01-01T00:00:00Z",
            "inflight_commit_date": "0001-01-01T00:00:00Z",
        }
    )
    assert response.rate is None


def test_createledgerbalanceresp_accepts_response_without_currency_multiplier():
    """Core 0.15.0 dropped response fields > CreateLedgerBalanceResp accepts response without currency_multiplier"""
    response = CreateLedgerBalanceResp.from_dict(
        {
            "balance": 0,
            "version": 0,
            "inflight_balance": 0,
            "credit_balance": 0,
            "inflight_credit_balance": 0,
            "debit_balance": 0,
            "inflight_debit_balance": 0,
            "ledger_id": "ldg_test",
            "identity_id": "",
            "balance_id": "bln_test",
            "indicator": "",
            "currency": "USD",
            "created_at": "2026-06-24T00:00:00Z",
        }
    )
    assert response.currency_multiplier is None


def test_searchtransactiondocument_omits_rate():
    """Core 0.15.0 dropped response fields > SearchTransactionDocument omits rate"""
    document = SearchTransactionDocument.from_dict(
        {
            "id": "txn_test",
            "transaction_id": "txn_test",
            "status": "APPLIED",
            "created_at": 1781028226,
        }
    )
    assert not hasattr(document, "rate")


def test_searchbalancedocument_omits_currency_multiplier():
    """Core 0.15.0 dropped response fields > SearchBalanceDocument omits currency_multiplier"""
    document = SearchBalanceDocument.from_dict(
        {
            "id": "bln_test",
            "balance_id": "bln_test",
            "balance": "0",
            "created_at": 1781222909,
        }
    )
    assert not hasattr(document, "currency_multiplier")
