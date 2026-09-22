"""Live coverage of GET list routes against Core.

Skipped unless BLNK_E2E=1 — the same env var gates the rest of the
integration suite. Core has served these GET lists since ~0.14; this SDK
is aligned with 0.15.4.
"""

from __future__ import annotations

import os
import uuid

import pytest

from blnk_sdk.client import BlnkClientOptions, blnk_init
from tests.utils import BASE_URL, BLNK_API_KEY, generate_random_numbers_with_prefix

pytestmark = pytest.mark.skipif(
    os.environ.get("BLNK_E2E") != "1",
    reason="requires live Blnk Core at http://localhost:5001/ (set BLNK_E2E=1)",
)

CLIENT_OPTIONS = BlnkClientOptions(base_url=BASE_URL)
CLIENT = blnk_init(BLNK_API_KEY, CLIENT_OPTIONS)


def test_list_ledgers_finds_uniquely_named_ledger() -> None:
    """create a uniquely named ledger, list ledgers, find it"""
    ledger_name = f"Python List {uuid.uuid4()}"
    created = CLIENT.ledgers.create({"name": ledger_name})
    assert created.status == 201, created.message
    ledger_id = created.data["ledger_id"]

    found = None
    offset = 0
    limit = 50
    while True:
        response = CLIENT.ledgers.list({"limit": limit, "offset": offset})
        assert response.status == 200, response.message
        assert isinstance(response.data, list)
        for row in response.data:
            if row.get("ledger_id") == ledger_id or row.get("name") == ledger_name:
                found = row
                break
        if found is not None or len(response.data) < limit:
            break
        offset += limit

    assert found is not None, f"created ledger {ledger_id!r} missing from list"
    assert found["name"] == ledger_name


def test_list_balances_transactions_and_monitors_by_balance() -> None:
    """optionally list balances, transactions, and monitors for a new balance"""
    ledger = CLIENT.ledgers.create({"name": f"Python List Nested {uuid.uuid4()}"})
    assert ledger.status == 201, ledger.message
    ledger_id = ledger.data["ledger_id"]

    balance = CLIENT.ledger_balances.create(
        {"ledger_id": ledger_id, "currency": "USD"}
    )
    assert balance.status == 201, balance.message
    balance_id = balance.data["balance_id"]

    balances = CLIENT.ledger_balances.list({"limit": 50})
    assert balances.status == 200, balances.message
    assert isinstance(balances.data, list)
    assert any(row.get("balance_id") == balance_id for row in balances.data)

    txn = CLIENT.transactions.create(
        {
            "amount": 100,
            "precision": 100,
            "currency": "USD",
            "reference": generate_random_numbers_with_prefix("list", 8),
            "description": "list resources coverage",
            "source": "@WorldUSD",
            "destination": balance_id,
            "allow_overdraft": True,
        }
    )
    assert txn.status in (200, 201), txn.message

    transactions = CLIENT.transactions.list({"limit": 50})
    assert transactions.status == 200, transactions.message
    assert isinstance(transactions.data, list)

    monitor = CLIENT.balance_monitor.create(
        {
            "balance_id": balance_id,
            "condition": {
                "field": "credit_balance",
                "operator": ">=",
                "precision": 100,
                "value": 1,
            },
            "description": "list-by-balance coverage",
        }
    )
    assert monitor.status == 201, monitor.message

    by_balance = CLIENT.balance_monitor.list_by_balance_id(balance_id)
    assert by_balance.status == 200, by_balance.message
    assert isinstance(by_balance.data, list)
    assert any(row.get("monitor_id") == monitor.data["monitor_id"] for row in by_balance.data)

    all_monitors = CLIENT.balance_monitor.list()
    assert all_monitors.status == 200, all_monitors.message
    assert isinstance(all_monitors.data, list)
