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
