"""Request/response types for the balance monitors service.

Field names are the wire names (snake_case), declared in wire order.
`kw_only=True` is used where a required field follows an optional one so
declaration order can match the wire order exactly. Response date/time
fields (`created_at`) stay plain strings — never parsed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from .base import DTO

# Comparison operator for monitor conditions: ">", "<", "=", "!=", ">=" or
# "<=". Modeled as a plain str (not an enum) so invalid values like "==" stay
# representable and are rejected by the validator rather than at construction.
MonitorConditionOperators = str

# How often a monitor fires (Core 0.15.7+): "edge" or "level". Modeled as a
# plain str so invalid values stay representable and are rejected by the
# validator rather than at construction.
MonitorTrigger = str

# Fires once when the condition becomes true, and again only after it has
# gone false and become true again. Core's default when trigger is omitted.
MONITOR_TRIGGER_EDGE: MonitorTrigger = "edge"
# Fires on every balance update while the condition holds.
MONITOR_TRIGGER_LEVEL: MonitorTrigger = "level"


@dataclass
class MonitorCondition(DTO):
    """Condition evaluated against a balance field."""

    field: str
    operator: MonitorConditionOperators
    # Note: the validator only checks that this is numeric, so NaN and
    # ±Infinity are accepted.
    value: Union[int, float]
    precision: Union[int, float]


@dataclass(kw_only=True)
class MonitorConditionResp(MonitorCondition):
    """Condition as Core returns it on create/get/list."""

    # Threshold in minor units (value × precision). Core computes it; it is
    # never sent on requests.
    precise_value: Optional[int] = None


@dataclass(kw_only=True)
class MonitorData(DTO):
    """Request body for `POST balance-monitors` / `PUT balance-monitors/{id}`.

    Note: unlike most request bodies, monitors intentionally carry no
    `meta_data` field.
    """

    condition: Union[MonitorCondition, dict]
    description: Optional[str] = None
    balance_id: str
    call_back_url: Optional[str] = None
    # MONITOR_TRIGGER_EDGE or MONITOR_TRIGGER_LEVEL. Omit for Core's default
    # (edge).
    trigger: Optional[MonitorTrigger] = None


@dataclass(kw_only=True)
class MonitorDataResp(MonitorData):
    """Response shape for create/get/list.

    `update` and `update_partial` do not return a monitor; see
    UpdateMonitorResp.
    """

    condition: Union[MonitorConditionResp, dict]
    monitor_id: str
    created_at: str  # ISO date string produced by the server — never parsed
    # Last observed truth value of an edge-triggered monitor's condition.
    # None until Core has evaluated it.
    condition_state: Optional[bool] = None


@dataclass
class UpdateMonitorCondition(DTO):
    """Condition fields to change in `update_partial`. Unset (None) fields
    are omitted and Core keeps the stored value.

    `value=0` moves the threshold to zero. Core ignores a `precision`
    change unless `value` is sent with it, and then replies with
    `precision_unchanged: true`.
    """

    field: Optional[str] = None
    operator: Optional[MonitorConditionOperators] = None
    value: Optional[Union[int, float]] = None
    precision: Optional[Union[int, float]] = None


@dataclass
class UpdateMonitorRequest(DTO):
    """Body for `BalanceMonitor.update_partial` (`PUT balance-monitors/{id}`).

    Core 0.15.9 keeps every field a PUT leaves out, so set only what should
    change. Older Core writes every column, so do not send a partial body
    to Core before 0.15.9. `description=""` clears the description. There is no
    `call_back_url`: Core ignores it on update.
    """

    balance_id: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[Union[UpdateMonitorCondition, dict]] = None
    trigger: Optional[MonitorTrigger] = None


@dataclass
class UpdateMonitorResp(DTO):
    """Response from `PUT balance-monitors/{id}`."""

    message: str
    # True when `precision` was sent without `value`, so Core kept the
    # stored precision.
    precision_unchanged: Optional[bool] = None


@dataclass
class DeleteBalanceMonitorResp(DTO):
    """Response from `DELETE balance-monitors/{id}`."""

    message: str
