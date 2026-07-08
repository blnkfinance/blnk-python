"""End-to-end tests covering the core Blnk resources — ledgers, identities,
balances, transactions, balance monitors, and reconciliation (6 groups, 23
cases). Requires a live Blnk Core at http://localhost:5001/; skipped unless
BLNK_E2E=1 (the same env var gates the integration suite).

The groups share module-level mutable ids (ledger_id, identity_id, ...) and
must run sequentially, so the whole suite lives in one ordered module: each
group is a class and each case a method, and pytest executes them
top-to-bottom in source order. Duplicate case names across groups ("It should
return 400" / "it should return 400") are disambiguated by their class.

Behavioral notes the assertions depend on:
- Every group builds its client with an empty api key, so no X-Blnk-Key
  header is sent.
- The identity category is the literal string `cutomer`; the misspelling is
  intentional and must stay byte-exact.
- `upload("no path", ...)` expects the 404 the SDK synthesizes for a missing
  local file; the successful live upload returns 200 (the unit-test mock
  returns 201).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

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

# Module-level mutable state shared across the ordered test classes.
STATE: Dict[str, str] = {
    "ledger_id": "",
    "ledger_balance_id": "",
    "transaction_id": "",
    "identity_id": "",
    "balance_monitor_id": "",
    "upload_id": "",
    "matching_rule_id": "",
}

LEDGER_BALANCE_FIELDS = [
    "balance",
    "version",
    "inflight_balance",
    "credit_balance",
    "debit_balance",
    "inflight_debit_balance",
    "inflight_credit_balance",
    "ledger_id",
    "identity_id",
    "balance_id",
    "currency",
    "created_at",
    "inflight_expires_at",
]
TRANSACTION_FIELDS = [
    "transaction_id",
    "amount",
    "currency",
    "source",
    "destination",
    "reference",
    "status",
    "created_at",
    "precision",
]


def _has_props(data: Dict[str, Any], props: Iterable[str]) -> None:
    """Asserts every listed key is present in the mapping."""
    for prop in props:
        assert prop in data, f"missing prop: {prop}"


def _make_client():
    """Each test class builds its own client with a fresh options object,
    authenticated with the configured API key (empty for unsecured local
    instances)."""
    return blnk_init(BLNK_API_KEY, BlnkClientOptions(base_url=BASE_URL))


class TestLedgersEndToEndTest:
    """Ledgers end to end test."""

    client = _make_client()

    def test_create_a_ledger(self) -> None:
        """create a ledger"""
        ledger_data = {"name": "Test Ledger"}

        response = self.client.ledgers.create(ledger_data)

        assert response, "response is successful"
        assert response.status == 201
        assert isinstance(response.data, dict)
        _has_props(response.data, ["ledger_id", "name", "created_at"])
        assert isinstance(response.data.get("created_at"), str)
        assert isinstance(response.data.get("ledger_id"), str)
        STATE["ledger_id"] = response.data["ledger_id"]

    def test_create_a_ledger_fail(self) -> None:
        """create a ledger fail"""
        ledger_data: Dict[str, Any] = {}
        # this should fail, since we pass an empty object to the create method
        response = self.client.ledgers.create(ledger_data)
        assert response, "response is returned"
        assert response.status == 400

    def test_it_should_retrieve_a_ledger_created(self) -> None:
        """It should retrieve a ledger created"""
        response = self.client.ledgers.get(STATE["ledger_id"])

        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)
        _has_props(response.data, ["ledger_id", "name", "created_at"])

    def test_it_should_reject_an_unknown_ledger_id(self) -> None:
        """It should reject an unknown ledger id."""
        response = self.client.ledgers.get("123456789")
        assert response, "response is returned"
        # Blnk Core returns 400 on older versions and 404 on newer ones.
        assert response.status in (400, 404), f"expected 400 or 404, got {response.status}"


class TestIdentity:
    """Identity end to end test."""

    client = _make_client()

    def test_create_an_individual_identity(self) -> None:
        """create an individual identity"""
        identity_data = {
            "category": "cutomer",  # intentional misspelling — keep byte-exact
            "city": "Ikeja",
            "country": "NG",
            "first_name": "Test",
            "email_address": "test@test.com",
            "identity_type": "individual",
            "phone_number": "+2348012345678",
            "post_code": "100001",
            "state": "Lagos",
            "street": "123 Test Street",
            "dob": datetime(1996, 2, 25, tzinfo=timezone.utc),
            "gender": "male",
            "last_name": "Test",
            "nationality": "Nigerian",
        }

        response = self.client.identity.create(identity_data)

        assert response, "identity is created"
        assert response.status == 201
        assert isinstance(response.data, dict)
        _has_props(response.data, ["identity_id", "created_at", "identity_type"])
        STATE["identity_id"] = response.data["identity_id"]

    def test_list_all_identities(self) -> None:
        """list all identities"""
        response = self.client.identity.list()
        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, list)

    def test_get_identity_by_id(self) -> None:
        """get identity by id"""
        response = self.client.identity.get(STATE["identity_id"])
        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)
        _has_props(response.data, ["identity_id", "created_at", "identity_type"])

    def test_update_identity_to_organization(self) -> None:
        """update identity to organization"""
        identity_data = {
            "category": "cutomer",  # intentional misspelling — keep byte-exact
            "city": "Ikeja",
            "country": "NG",
            "email_address": "test@test.com",
            "identity_type": "organization",
            "organization_name": "Test Organization",
            "phone_number": "+2348012345678",
            "post_code": "100001",
            "state": "Lagos",
            "street": "123 Test Street",
            "dob": datetime(1996, 2, 25, tzinfo=timezone.utc),
            "gender": "male",
        }
        response = self.client.identity.update(STATE["identity_id"], identity_data)
        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)


class TestLedgerBalances:
    """Ledger balances end to end test."""

    client = _make_client()

    def test_it_should_create_a_balance(self) -> None:
        """It should create a balance"""
        balance_data = {
            "currency": "USD",
            "ledger_id": STATE["ledger_id"],
            "identity_id": STATE["identity_id"],
            "meta_data": {},
        }
        response = self.client.ledger_balances.create(balance_data)

        assert response, "response is returned"
        assert response.status == 201
        assert isinstance(response.data, dict)
        _has_props(response.data, LEDGER_BALANCE_FIELDS)
        STATE["ledger_balance_id"] = response.data["balance_id"]

    def test_get_ledger_balances(self) -> None:
        """get ledger balances"""
        response = self.client.ledger_balances.get(STATE["ledger_balance_id"])
        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)
        _has_props(response.data, LEDGER_BALANCE_FIELDS)

    def test_it_should_reject_an_unknown_balance_id(self) -> None:
        """it should reject an unknown balance id."""
        response = self.client.ledger_balances.get("123456789")
        assert response, "response is returned"
        # Blnk Core returns 400 on older versions and 404 on newer ones.
        assert response.status in (400, 404), f"expected 400 or 404, got {response.status}"


class TestLedgerBalanceTransactions:
    """Ledger balance transactions end to end test."""

    client = _make_client()

    def test_it_should_create_a_transaction_on_a_balance(self) -> None:
        """It should create a transaction on a balance"""
        transaction_data = {
            "amount": 1000,
            "currency": "USD",
            "description": "Test transaction",
            "precision": 100,
            "reference": generate_random_numbers_with_prefix("test", 4),
            "source": "@bank-account",
            "destination": STATE["ledger_balance_id"],
            "inflight": True,
            "allow_overdraft": True,  # Enable overdraft for the first deposit
            "meta_data": {},
        }

        response = self.client.transactions.create(transaction_data)
        assert response, "response is returned"
        assert response.status == 201
        assert isinstance(response.data, dict)
        _has_props(response.data, [*TRANSACTION_FIELDS, "precise_amount"])
        STATE["transaction_id"] = response.data["transaction_id"]

    def test_it_should_commit_the_transaction(self) -> None:
        """it should commit the transaction"""
        # we sleep a bit so the transaction enqueues
        sleep_seconds(2)
        response = self.client.transactions.update_status(
            STATE["transaction_id"], {"status": "commit"}
        )

        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)
        _has_props(response.data, [*TRANSACTION_FIELDS, "precise_amount"])

    def test_it_should_void_the_transaction(self) -> None:
        """it should void the transaction"""
        # we sleep a bit so the transaction enqueues
        sleep_seconds(2)
        response = self.client.transactions.update_status(
            STATE["transaction_id"], {"status": "void"}
        )
        assert response, "response is returned"

        assert response.status == 200
        assert isinstance(response.data, dict)
        _has_props(response.data, TRANSACTION_FIELDS)


class TestBalanceMonitors:
    """Balance monitors end to end test."""

    client = _make_client()

    def test_it_should_create_a_balance_monitor(self) -> None:
        """It should create a balance monitor"""
        monitor_data = {
            "balance_id": STATE["ledger_balance_id"],
            "condition": {
                "field": "credit_balance",
                "operator": ">=",
                "precision": 100,
                "value": 1000,
            },
            "description": "Tier 1 account",
        }

        response = self.client.balance_monitor.create(monitor_data)
        assert response, "response is returned"
        assert response.status == 201
        assert isinstance(response.data, dict)
        _has_props(response.data, ["monitor_id", "balance_id"])
        STATE["balance_monitor_id"] = response.data["monitor_id"]

    def test_it_should_list_all_balance_monitors(self) -> None:
        """It should list all balance monitors"""
        response = self.client.balance_monitor.list()
        assert response, "response is returned"
        assert response.status == 200
        # The broad container check is intentionally kept alongside the
        # stricter list check.
        assert isinstance(response.data, (dict, list))
        assert isinstance(response.data, list)

    def test_it_should_fail_to_get_the_balance_monitor(self) -> None:
        """It should fail to get the balance monitor."""
        response = self.client.balance_monitor.get("123456789")
        assert response, "response is returned"
        # Blnk Core returns 400 on older versions and 404 on newer ones.
        assert response.status in (400, 404), f"expected 400 or 404, got {response.status}"

    def test_it_should_get_a_balance_monitor(self) -> None:
        """It should get a balance monitor"""
        response = self.client.balance_monitor.get(STATE["balance_monitor_id"])
        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)

    def test_it_should_update_a_balance_monitor(self) -> None:
        """It should update a balance monitor"""
        monitor_data = {
            "balance_id": STATE["ledger_balance_id"],
            "condition": {
                "field": "credit_balance",
                "operator": ">=",
                "precision": 100,
                "value": 1000,
            },
            "description": "Tier 1 account",
        }
        response = self.client.balance_monitor.update(
            STATE["balance_monitor_id"], monitor_data
        )
        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)


class TestReconciliation:
    """Reconciliation end to end test — uses the file.csv fixture at the
    package root."""

    client = _make_client()
    file_path = str(Path(__file__).resolve().parents[2] / "file.csv")

    def test_it_should_create_a_matching_rule(self) -> None:
        """It should create a matching rule"""
        matching_rule_data = {
            "description": "Test matching rule",
            "criteria": [
                {"field": "amount", "operator": "equals", "allowable_drift": 0.01}
            ],
            "name": "Test matching rule",
        }
        response = self.client.reconciliation.create_matching_rule(matching_rule_data)
        assert response, "response is returned"
        assert response.status == 201
        STATE["matching_rule_id"] = response.data["rule_id"]

    def test_it_should_fail_to_upload_a_reconciliation_file(self) -> None:
        """it should fail to upload a reconciliation file"""
        # The 404 is synthesized by the SDK for a missing local file
        # ("File does not exist at path: no path") — no request reaches Core.
        response = self.client.reconciliation.upload("no path", "Stripe")
        assert response, "response is returned"
        assert response.status == 404

    def test_it_should_upload_a_reconciliation_file(self) -> None:
        """it should upload a reconciliation file"""
        response = self.client.reconciliation.upload(self.file_path, "Stripe")
        assert response, "response is returned"
        assert response.status == 200  # live Core returns 200 (the unit-test mock returns 201)
        assert isinstance(response.data, dict)

        _has_props(response.data, ["upload_id"])
        STATE["upload_id"] = response.data["upload_id"]

    def test_run_reconciliation(self) -> None:
        """Run Reconciliation"""
        data = {
            "dry_run": True,
            "grouping_criteria": "amount",
            "matching_rule_ids": [STATE["matching_rule_id"]],
            "strategy": "one_to_many",
            "upload_id": STATE["upload_id"],
        }
        response = self.client.reconciliation.run(data)
        assert response, "response is returned"
        assert response.status == 200
        assert isinstance(response.data, dict)

        _has_props(response.data, ["reconciliation_id"])
