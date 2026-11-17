"""Live Core 0.15.9 checks for the fields and options added for 0.15.9.

The monitor tests prove the partial-update contract against a real Core:
a PUT keeps every field it leaves out, an omitted `value` keeps the stored
threshold, an explicit 0 sets it, and a lone `precision` is ignored and
reported. They fail against Core before 0.15.9, which writes every column.

Requires Blnk Core 0.15.9+ at http://localhost:5001 (or BLNK_BASE_URL).
Skipped unless BLNK_E2E=1.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict

import pytest

from blnk_sdk import BlnkClientOptions, blnk_init
from blnk_sdk.types.balance_monitor import (
    MonitorConditionResp,
    MonitorDataResp,
    UpdateMonitorCondition,
    UpdateMonitorRequest,
    UpdateMonitorResp,
)
from blnk_sdk.types.ledger_balances import CreateLedgerBalanceResp
from tests.utils import BASE_URL, BLNK_API_KEY

pytestmark = pytest.mark.skipif(
    os.environ.get("BLNK_E2E") != "1",
    reason="requires live Blnk Core 0.15.9+ at http://localhost:5001/ (set BLNK_E2E=1)",
)

CLIENT = blnk_init(BLNK_API_KEY, BlnkClientOptions(base_url=BASE_URL))


def _ledger_and_balance(identity_id: str = "") -> Dict[str, str]:
    ledger = CLIENT.ledgers.create({"name": f"Python 0.15.9 {uuid.uuid4()}"})
    assert ledger.status == 201, ledger.message
    body: Dict[str, Any] = {"ledger_id": ledger.data["ledger_id"], "currency": "USD"}
    if identity_id:
        body["identity_id"] = identity_id
    balance = CLIENT.ledger_balances.create(body)
    assert balance.status == 201, balance.message
    return {"ledger_id": ledger.data["ledger_id"], "balance_id": balance.data["balance_id"]}


def _create_monitor(balance_id: str) -> str:
    created = CLIENT.balance_monitor.create({
        "balance_id": balance_id,
        "condition": {"field": "balance", "operator": "<", "value": 100, "precision": 100},
        "description": "original",
        "call_back_url": "https://example.com/hook",
        "trigger": "edge",
    })
    assert created.status == 201, created.message
    return created.data["monitor_id"]


def _monitor(monitor_id: str) -> MonitorDataResp:
    response = CLIENT.balance_monitor.get(monitor_id)
    assert response.status == 200, response.message
    monitor = MonitorDataResp.from_dict(response.data)
    monitor.condition = MonitorConditionResp.from_dict(monitor.condition)
    return monitor


def _assert_condition(monitor: MonitorDataResp, value: float, precision: float) -> None:
    condition = monitor.condition
    assert (condition.field, condition.operator) == ("balance", "<")
    assert condition.value == value
    assert condition.precision == precision
    assert condition.precise_value == round(value * precision)


def test_create_monitor_returns_trigger_and_precise_value() -> None:
    balance_id = _ledger_and_balance()["balance_id"]
    monitor = _monitor(_create_monitor(balance_id))

    assert monitor.trigger == "edge"
    assert monitor.balance_id == balance_id
    _assert_condition(monitor, 100, 100)


def test_description_only_update_keeps_balance_and_threshold() -> None:
    balance_id = _ledger_and_balance()["balance_id"]
    monitor_id = _create_monitor(balance_id)

    updated = CLIENT.balance_monitor.update_partial(
        monitor_id, UpdateMonitorRequest(description="renamed")
    )

    assert updated.status == 200, updated.message
    assert UpdateMonitorResp.from_dict(updated.data).precision_unchanged is None
    monitor = _monitor(monitor_id)
    assert monitor.description == "renamed"
    assert monitor.balance_id == balance_id
    assert monitor.trigger == "edge"
    _assert_condition(monitor, 100, 100)


def test_value_only_update_keeps_field_operator_and_precision() -> None:
    monitor_id = _create_monitor(_ledger_and_balance()["balance_id"])

    updated = CLIENT.balance_monitor.update_partial(
        monitor_id, UpdateMonitorRequest(condition=UpdateMonitorCondition(value=50))
    )

    assert updated.status == 200, updated.message
    monitor = _monitor(monitor_id)
    assert monitor.description == "original"
    _assert_condition(monitor, 50, 100)


def test_explicit_zero_value_moves_threshold_to_zero() -> None:
    monitor_id = _create_monitor(_ledger_and_balance()["balance_id"])

    updated = CLIENT.balance_monitor.update_partial(
        monitor_id, {"condition": {"value": 0}}
    )

    assert updated.status == 200, updated.message
    _assert_condition(_monitor(monitor_id), 0, 100)


def test_precision_without_value_is_ignored_and_reported() -> None:
    monitor_id = _create_monitor(_ledger_and_balance()["balance_id"])

    updated = CLIENT.balance_monitor.update_partial(
        monitor_id, {"condition": {"precision": 1000}}
    )

    assert updated.status == 200, updated.message
    assert UpdateMonitorResp.from_dict(updated.data).precision_unchanged is True
    _assert_condition(_monitor(monitor_id), 100, 100)


def test_precision_with_value_changes_both() -> None:
    monitor_id = _create_monitor(_ledger_and_balance()["balance_id"])

    updated = CLIENT.balance_monitor.update_partial(
        monitor_id, {"condition": {"value": 2.5, "precision": 1000}}
    )

    assert updated.status == 200, updated.message
    assert UpdateMonitorResp.from_dict(updated.data).precision_unchanged is None
    _assert_condition(_monitor(monitor_id), 2.5, 1000)


def test_trigger_only_update_keeps_everything_else() -> None:
    monitor_id = _create_monitor(_ledger_and_balance()["balance_id"])

    updated = CLIENT.balance_monitor.update_partial(monitor_id, {"trigger": "level"})

    assert updated.status == 200, updated.message
    monitor = _monitor(monitor_id)
    assert monitor.trigger == "level"
    assert monitor.description == "original"
    _assert_condition(monitor, 100, 100)


def test_get_balance_include_embeds_identity_and_ledger() -> None:
    identity = CLIENT.identity.create({
        "identity_type": "individual",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email_address": f"ada-{uuid.uuid4().hex[:8]}@example.com",
        "category": "customer",
    })
    assert identity.status == 201, identity.message
    ids = _ledger_and_balance(identity.data["identity_id"])

    response = CLIENT.ledger_balances.get(
        ids["balance_id"], {"include": ["identity", "ledger"]}
    )

    assert response.status == 200, response.message
    balance = CreateLedgerBalanceResp.from_dict(response.data)
    assert balance.identity["identity_id"] == identity.data["identity_id"]
    assert balance.ledger["ledger_id"] == ids["ledger_id"]

    plain = CLIENT.ledger_balances.get(ids["balance_id"])
    assert "identity" not in plain.data and "ledger" not in plain.data


def test_fractional_monitor_value_round_trips() -> None:
    balance_id = _ledger_and_balance()["balance_id"]
    created = CLIENT.balance_monitor.create({
        "balance_id": balance_id,
        "condition": {"field": "balance", "operator": "<", "value": 100.5, "precision": 100},
        "description": "fractional",
    })
    assert created.status == 201, created.message
    monitor_id = created.data["monitor_id"]

    _assert_condition(_monitor(monitor_id), 100.5, 100)

    renamed = CLIENT.balance_monitor.update_partial(monitor_id, {"description": "renamed"})
    assert renamed.status == 200, renamed.message
    _assert_condition(_monitor(monitor_id), 100.5, 100)

    moved = CLIENT.balance_monitor.update_partial(
        monitor_id, UpdateMonitorRequest(condition=UpdateMonitorCondition(value=0.75))
    )
    assert moved.status == 200, moved.message
    _assert_condition(_monitor(monitor_id), 0.75, 100)


def _debit(balance_id: str, amount: float, **extra: Any) -> Any:
    return CLIENT.transactions.create({
        "amount": amount,
        "precision": 100,
        "currency": "USD",
        "reference": f"py-0159-{uuid.uuid4()}",
        "description": "overdraft check",
        "source": balance_id,
        "destination": "@WorldUSD",
        "skip_queue": True,
        **extra,
    })


def test_overdraft_limit_allows_up_to_the_limit_and_no_further() -> None:
    balance_id = _ledger_and_balance()["balance_id"]

    within = _debit(balance_id, 80, overdraft_limit=100)
    assert within.status == 201, within.message
    assert within.data["status"] == "APPLIED"
    assert within.data["overdraft_limit"] == 100

    beyond = _debit(balance_id, 50, overdraft_limit=100)
    assert beyond.status == 400, beyond.data
    assert beyond.error.code == "TXN_VALIDATION_ERROR"
    assert "exceeds overdraft limit" in beyond.message

    balance = CLIENT.ledger_balances.get(balance_id)
    assert balance.data["balance"] == -8000


def test_inflight_commit_reference_is_idempotent() -> None:
    balance_id = _ledger_and_balance()["balance_id"]
    funded = CLIENT.transactions.create({
        "amount": 100,
        "precision": 100,
        "currency": "USD",
        "reference": f"py-0159-fund-{uuid.uuid4()}",
        "description": "fund",
        "source": "@WorldUSD",
        "destination": balance_id,
        "allow_overdraft": True,
        "skip_queue": True,
    })
    assert funded.status == 201, funded.message
    hold = CLIENT.transactions.create({
        "amount": 40,
        "precision": 100,
        "currency": "USD",
        "reference": f"py-0159-hold-{uuid.uuid4()}",
        "description": "hold",
        "source": balance_id,
        "destination": "@WorldUSD",
        "inflight": True,
        "skip_queue": True,
    })
    assert hold.status == 201, hold.message

    reference = f"py-0159-commit-{uuid.uuid4()}"
    body = {"status": "commit", "amount": 10, "reference": reference, "skip_queue": True}
    first = CLIENT.transactions.update_status(hold.data["transaction_id"], body)
    again = CLIENT.transactions.update_status(hold.data["transaction_id"], body)

    assert first.status in (200, 201), first.message
    assert again.status in (200, 201), again.message
    assert again.data["transaction_id"] == first.data["transaction_id"]

    balance = CLIENT.ledger_balances.get(balance_id)
    assert balance.data["balance"] == 9000
    assert balance.data["inflight_balance"] == -3000
