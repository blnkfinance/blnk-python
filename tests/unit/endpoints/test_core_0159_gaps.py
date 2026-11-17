"""Core 0.15.9 parity: the fields and options added to close the SDK gaps.

Every case runs through the real client (`Blnk` with the default services
map) and a recording transport, so the assertions cover the URL and JSON
body that actually go out, and responses are decoded from Core-shaped JSON.
"""

from __future__ import annotations

import json
from typing import Any, List, Tuple

import pytest

from blnk_sdk.client import Blnk
from blnk_sdk.http_client import format_response
from blnk_sdk.services import default_services_map
from blnk_sdk.types.balance_monitor import (
    MONITOR_TRIGGER_LEVEL,
    MonitorCondition,
    MonitorConditionResp,
    MonitorData,
    MonitorDataResp,
    UpdateMonitorCondition,
    UpdateMonitorRequest,
    UpdateMonitorResp,
)
from blnk_sdk.types.ledger_balances import (
    BALANCE_INCLUDE_IDENTITY,
    BALANCE_INCLUDE_LEDGER,
    CreateLedgerBalanceResp,
    GetBalanceRequest,
)
from blnk_sdk.types.transactions import CreateTransactions, UpdateTransactionStatus
from tests.mocks.blnk_client_mocks import create_mock_blnk_client_options
from tests.mocks.transport_mock import make_response

BASE = "http://mock-api.com/"


class RecordingTransport:
    """Records (method, url, decoded JSON body) and replies with `reply`."""

    def __init__(self, reply: Any = None, status: int = 200) -> None:
        self.reply = {} if reply is None else reply
        self.status = status
        self.calls: List[Tuple[str, str, Any]] = []

    def __call__(self, url: str, init: Any) -> Any:
        body = json.loads(init.body) if init.body else None
        self.calls.append((init.method, url, body))
        return make_response(
            ok=200 <= self.status < 300,
            status=self.status,
            status_text="OK",
            json_body=self.reply,
            headers={"content-type": "application/json"},
            url=url,
        )


def _client(transport: RecordingTransport) -> Blnk:
    return Blnk(
        "key",
        create_mock_blnk_client_options(),
        default_services_map(),
        format_response,
        transport,
    )


_CONDITION = {"field": "balance", "operator": "<", "value": 100, "precision": 100}


# --------------------------------------------------------------------------- #
# Gap 1: monitor trigger on create, condition_state and precise_value


def test_create_monitor_sends_trigger() -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    response = blnk.balance_monitor.create(
        MonitorData(
            balance_id="bln_1",
            condition=MonitorCondition(**_CONDITION),
            trigger=MONITOR_TRIGGER_LEVEL,
        )
    )

    assert response.status == 201
    assert transport.calls == [
        (
            "POST",
            BASE + "balance-monitors",
            {"condition": _CONDITION, "balance_id": "bln_1", "trigger": "level"},
        )
    ]


def test_create_monitor_without_trigger_omits_it() -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    blnk.balance_monitor.create(
        MonitorData(balance_id="bln_1", condition=MonitorCondition(**_CONDITION))
    )

    assert "trigger" not in transport.calls[0][2]


@pytest.mark.parametrize("trigger", ["edge", "level"])
def test_create_monitor_accepts_core_triggers(trigger: str) -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    response = blnk.balance_monitor.create(
        {"balance_id": "bln_1", "condition": _CONDITION, "trigger": trigger}
    )

    assert response.status == 201
    assert transport.calls[0][2]["trigger"] == trigger


@pytest.mark.parametrize("trigger", ["", "EDGE", "always", None, 1])
def test_create_monitor_rejects_invalid_trigger(trigger: Any) -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    response = blnk.balance_monitor.create(
        {"balance_id": "bln_1", "condition": _CONDITION, "trigger": trigger}
    )

    assert response.status == 400
    assert response.message == 'trigger must be "edge" or "level" if provided'
    assert transport.calls == []


def test_monitor_response_decodes_state_and_precise_value() -> None:
    core_monitor = {
        "monitor_id": "mon_1",
        "balance_id": "bln_1",
        "description": "low",
        "created_at": "2026-11-17T10:00:00Z",
        "condition": {
            "value": 100,
            "precision": 100,
            "precise_value": 10000,
            "field": "balance",
            "operator": "<",
        },
        "trigger": "edge",
        "condition_state": True,
    }
    transport = RecordingTransport(reply=core_monitor)
    blnk = _client(transport)

    response = blnk.balance_monitor.get("mon_1")
    monitor = MonitorDataResp.from_dict(response.data)
    condition = MonitorConditionResp.from_dict(monitor.condition)

    assert monitor.trigger == "edge"
    assert monitor.condition_state is True
    assert condition.precise_value == 10000


# --------------------------------------------------------------------------- #
# Gap 2: partial monitor update


def test_update_partial_sends_only_description() -> None:
    transport = RecordingTransport(
        reply={"message": "BalanceMonitor updated successfully"}
    )
    blnk = _client(transport)

    response = blnk.balance_monitor.update_partial(
        "mon_1", UpdateMonitorRequest(description="renamed")
    )

    assert transport.calls == [
        ("PUT", BASE + "balance-monitors/mon_1", {"description": "renamed"})
    ]
    resp = UpdateMonitorResp.from_dict(response.data)
    assert resp.message == "BalanceMonitor updated successfully"
    assert resp.precision_unchanged is None


def test_update_partial_sends_explicit_zero_value_without_field_or_operator() -> None:
    transport = RecordingTransport(reply={"message": "ok"})
    blnk = _client(transport)

    blnk.balance_monitor.update_partial(
        "mon_1", UpdateMonitorRequest(condition=UpdateMonitorCondition(value=0))
    )

    # Core reads {"condition": {"value": 0}} with field/operator absent as
    # "move the threshold to zero".
    assert transport.calls[0][2] == {"condition": {"value": 0}}


def test_update_partial_can_clear_description_and_change_trigger() -> None:
    transport = RecordingTransport(reply={"message": "ok"})
    blnk = _client(transport)

    blnk.balance_monitor.update_partial(
        "mon_1", {"description": "", "trigger": "level"}
    )

    assert transport.calls[0][2] == {"description": "", "trigger": "level"}


def test_update_partial_decodes_precision_unchanged() -> None:
    transport = RecordingTransport(
        reply={
            "message": "BalanceMonitor updated successfully. precision was left "
            "unchanged because value was not sent with it.",
            "precision_unchanged": True,
        }
    )
    blnk = _client(transport)

    response = blnk.balance_monitor.update_partial(
        "mon_1", {"condition": {"precision": 1000}}
    )

    assert transport.calls[0][2] == {"condition": {"precision": 1000}}
    assert UpdateMonitorResp.from_dict(response.data).precision_unchanged is True


@pytest.mark.parametrize(
    "data, message",
    [
        ({}, "at least one field must be set to update a monitor"),
        (UpdateMonitorRequest(), "at least one field must be set to update a monitor"),
        (
            {"call_back_url": "https://example.com"},
            "call_back_url cannot be changed on update; Core ignores it",
        ),
        ({"name": "x"}, "unsupported update field: name"),
        ({"trigger": "sometimes"}, 'trigger must be "edge" or "level" if provided'),
        ({"trigger": ""}, 'trigger must be "edge" or "level" if provided'),
        ({"balance_id": ""}, "balance_id must be a non-empty string if provided"),
        ({"description": None}, "description must be a valid string if provided"),
        ({"condition": {}}, "condition must set at least one field if provided"),
        ({"condition": []}, "condition must be a valid UpdateMonitorCondition object"),
        (
            {"condition": {"field": "", "operator": "", "value": 0}},
            "condition.field must be a non-empty string if provided",
        ),
        (
            {"condition": {"operator": "=="}},
            "condition.operator must be one of >, <, =, !=, >=, <= if provided",
        ),
        ({"condition": {"value": "10"}}, "condition.value must be a number if provided"),
        (
            {"condition": {"precision": True}},
            "condition.precision must be a number if provided",
        ),
        ({"condition": {"amount": 1}}, "unsupported condition field: amount"),
        ("not an object", "Data must be a valid object of type UpdateMonitorRequest"),
    ],
)
def test_update_partial_rejects_invalid_bodies(data: Any, message: str) -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    response = blnk.balance_monitor.update_partial("mon_1", data)

    assert response.status == 400
    assert response.message == message
    assert transport.calls == []


def test_update_still_accepts_full_monitor_data_with_trigger() -> None:
    transport = RecordingTransport(reply={"message": "ok"})
    blnk = _client(transport)

    response = blnk.balance_monitor.update(
        "mon_1",
        {"balance_id": "bln_1", "condition": _CONDITION, "trigger": "edge"},
    )

    assert response.status == 200
    assert transport.calls[0][2] == {
        "balance_id": "bln_1",
        "condition": _CONDITION,
        "trigger": "edge",
    }


# --------------------------------------------------------------------------- #
# Gap 3: reference on inflight commit/void


def test_update_status_sends_reference() -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    blnk.transactions.update_status(
        "txn_1",
        UpdateTransactionStatus(status="commit", amount=50, reference="commit_1"),
    )

    assert transport.calls == [
        (
            "PUT",
            BASE + "transactions/inflight/txn_1",
            {"status": "commit", "amount": 50, "reference": "commit_1"},
        )
    ]


def test_update_status_without_reference_omits_it() -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    blnk.transactions.update_status("txn_1", UpdateTransactionStatus(status="void"))

    assert transport.calls[0][2] == {"status": "void"}


@pytest.mark.parametrize("status", ["commit", "void"])
def test_update_status_sends_reference_for_commit_and_void(status: str) -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    response = blnk.transactions.update_status(
        "txn_1", {"status": status, "reference": f"{status}_ref_1"}
    )

    assert response.status == 200
    assert transport.calls[0][2] == {"status": status, "reference": f"{status}_ref_1"}


@pytest.mark.parametrize("status", ["commit", "void"])
@pytest.mark.parametrize("reference", ["", " ", "\t\n", 7, None])
def test_update_status_rejects_blank_or_non_string_reference(
    status: str, reference: Any
) -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    response = blnk.transactions.update_status(
        "txn_1", {"status": status, "reference": reference}
    )

    assert response.status == 400
    assert response.message == "reference must be a non-empty string if provided."
    assert transport.calls == []


@pytest.mark.parametrize("status", ["commit", "void"])
@pytest.mark.parametrize("reference", ["ref ", " ref", "\tref", "ref\n", " ref "])
def test_update_status_rejects_padded_reference(status: str, reference: str) -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    response = blnk.transactions.update_status(
        "txn_1", {"status": status, "reference": reference}
    )

    assert response.status == 400
    assert (
        response.message == "reference must not have leading or trailing whitespace."
    )
    assert transport.calls == []


def test_update_status_keeps_inner_whitespace_in_reference() -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    response = blnk.transactions.update_status(
        "txn_1", {"status": "commit", "reference": "order 42 commit"}
    )

    assert response.status == 200
    assert transport.calls[0][2]["reference"] == "order 42 commit"


# --------------------------------------------------------------------------- #
# Gap 4: overdraft_limit on create transaction


def _transaction(**extra: Any) -> CreateTransactions:
    fields: dict = {
        "amount": 750,
        "precision": 100,
        "reference": "ref_1",
        "description": "deposit",
        "currency": "USD",
        "source": "bln_src",
        "destination": "bln_dst",
    }
    fields.update(extra)
    return CreateTransactions(**fields)


def test_create_transaction_sends_overdraft_limit() -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    blnk.transactions.create(_transaction(allow_overdraft=True, overdraft_limit=500))

    method, url, body = transport.calls[0]
    assert (method, url) == ("POST", BASE + "transactions")
    assert body["allow_overdraft"] is True
    assert body["overdraft_limit"] == 500


def test_create_transaction_without_overdraft_limit_omits_it() -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    blnk.transactions.create(_transaction())

    assert "overdraft_limit" not in transport.calls[0][2]


@pytest.mark.parametrize("limit", [0, 500, 0.5])
def test_create_transaction_accepts_zero_and_positive_overdraft_limit(limit: Any) -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    response = blnk.transactions.create(
        _transaction(allow_overdraft=True, overdraft_limit=limit)
    )

    assert response.status == 201
    assert transport.calls[0][2]["overdraft_limit"] == limit


@pytest.mark.parametrize(
    "limit, message",
    [
        (-1, "overdraft_limit must be 0 or greater if provided."),
        (-0.01, "overdraft_limit must be 0 or greater if provided."),
        (float("nan"), "overdraft_limit must be a finite number if provided."),
        (float("inf"), "overdraft_limit must be a finite number if provided."),
        (float("-inf"), "overdraft_limit must be a finite number if provided."),
        ("500", "overdraft_limit must be a finite number if provided."),
        (True, "overdraft_limit must be a finite number if provided."),
        (None, "overdraft_limit must be a finite number if provided."),
    ],
)
def test_create_transaction_rejects_invalid_overdraft_limit(
    limit: Any, message: str
) -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    payload = _transaction().to_dict()
    payload["overdraft_limit"] = limit
    response = blnk.transactions.create(payload)

    assert response.status == 400
    assert response.message == message
    assert transport.calls == []


def test_bulk_create_sends_valid_overdraft_limit_per_item() -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    response = blnk.transactions.create_bulk({
        "transactions": [
            _transaction(reference="ref_a", overdraft_limit=0).to_dict(),
            _transaction(reference="ref_b", overdraft_limit=250).to_dict(),
        ]
    })

    assert response.status == 201
    items = transport.calls[0][2]["transactions"]
    assert [item["overdraft_limit"] for item in items] == [0, 250]


@pytest.mark.parametrize(
    "limit, message",
    [
        (-1, "overdraft_limit must be 0 or greater if provided."),
        (float("nan"), "overdraft_limit must be a finite number if provided."),
        (float("inf"), "overdraft_limit must be a finite number if provided."),
    ],
)
def test_bulk_create_rejects_invalid_overdraft_limit(limit: Any, message: str) -> None:
    transport = RecordingTransport(status=201)
    blnk = _client(transport)

    bad = _transaction(reference="ref_b").to_dict()
    bad["overdraft_limit"] = limit
    response = blnk.transactions.create_bulk({
        "transactions": [_transaction(reference="ref_a").to_dict(), bad]
    })

    assert response.status == 400
    assert response.message == f"Transaction at index 1: {message}"
    assert transport.calls == []


# --------------------------------------------------------------------------- #
# Gap 5: include on get balance


def test_get_balance_sends_repeated_include_params() -> None:
    core_balance = {
        "balance_id": "bln_1",
        "ledger_id": "ldg_1",
        "identity_id": "idt_1",
        "currency": "USD",
        "balance": 0,
        "identity": {"identity_id": "idt_1", "first_name": "Ada"},
        "ledger": {"ledger_id": "ldg_1", "name": "Savings"},
    }
    transport = RecordingTransport(reply=core_balance)
    blnk = _client(transport)

    response = blnk.ledger_balances.get(
        "bln_1",
        GetBalanceRequest(
            with_queued=True,
            include=[BALANCE_INCLUDE_IDENTITY, BALANCE_INCLUDE_LEDGER],
        ),
    )

    assert transport.calls == [
        (
            "GET",
            BASE + "balances/bln_1?with_queued=true&include=identity&include=ledger",
            None,
        )
    ]
    balance = CreateLedgerBalanceResp.from_dict(response.data)
    assert balance.identity["first_name"] == "Ada"
    assert balance.ledger["name"] == "Savings"


def test_get_balance_with_dict_include() -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    blnk.ledger_balances.get("bln_1", {"include": ["ledger"]})

    assert transport.calls[0][1] == BASE + "balances/bln_1?include=ledger"


def test_get_balance_without_options_sends_no_query() -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    blnk.ledger_balances.get("bln_1")

    assert transport.calls[0][1] == BASE + "balances/bln_1"


@pytest.mark.parametrize(
    "include, message",
    [
        ("identity", "include must be a list if provided"),
        (["account"], 'include values must be "identity" or "ledger"'),
        ([None], 'include values must be "identity" or "ledger"'),
    ],
)
def test_get_balance_rejects_invalid_include(include: Any, message: str) -> None:
    transport = RecordingTransport()
    blnk = _client(transport)

    response = blnk.ledger_balances.get("bln_1", {"include": include})

    assert response.status == 400
    assert response.message == message
    assert transport.calls == []
