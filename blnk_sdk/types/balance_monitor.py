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
class MonitorData(DTO):
    """Request body for `POST balance-monitors` / `PUT balance-monitors/{id}`.

    Note: unlike most request bodies, monitors intentionally carry no
    `meta_data` field.
    """

    condition: Union[MonitorCondition, dict]
    description: Optional[str] = None
    balance_id: str
    call_back_url: Optional[str] = None


@dataclass(kw_only=True)
class MonitorDataResp(MonitorData):
    """Response shape for create/get/list/update."""

    monitor_id: str
    created_at: str  # ISO date string produced by the server — never parsed


@dataclass
class DeleteBalanceMonitorResp(DTO):
    """Response from `DELETE balance-monitors/{id}`."""

    message: str
