"""Request/response types for the ledger balances service.

Field names are the wire names (snake_case), declared in wire order.
`kw_only=True` is used where a required field follows an optional one so
declaration order can match the wire order exactly. Response date/time
fields (`created_at`, `timestamp`) stay plain strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Union

from .base import DTO

# Allocation strategy: "FIFO", "LIFO" or "PROPORTIONAL". Modeled as a plain
# str (not an enum) so invalid values stay representable and are rejected by
# the validator rather than at construction.
AllocationStrategy = str


@dataclass(kw_only=True)
class CreateLedgerBalance(DTO):
    """Request body for `POST balances`."""

    ledger_id: str
    identity_id: Optional[str] = None
    currency: str
    # Enables fund lineage tracking. Requires identity_id.
    track_fund_lineage: Optional[bool] = None
    # How tagged provider funds are allocated when spending. Defaults to FIFO.
    allocation_strategy: Optional[AllocationStrategy] = None
    meta_data: Optional[Any] = None


@dataclass(kw_only=True)
class CreateLedgerBalanceResp(DTO):
    """Response from `POST balances` / `GET balances/...`."""

    balance: Optional[Union[int, float]] = None
    version: Optional[Union[int, float]] = None
    inflight_balance: Optional[Union[int, float]] = None
    credit_balance: Optional[Union[int, float]] = None
    inflight_credit_balance: Optional[Union[int, float]] = None
    debit_balance: Optional[Union[int, float]] = None
    inflight_debit_balance: Optional[Union[int, float]] = None
    # Removed from Core 0.15.0 balance responses — kept optional.
    currency_multiplier: Optional[Union[int, float]] = None
    ledger_id: Optional[str] = None
    identity_id: Optional[str] = None
    balance_id: Optional[str] = None
    indicator: Optional[str] = None
    currency: Optional[str] = None
    created_at: Optional[str] = None  # plain string, never parsed
    queued_credit_balance: Optional[Union[int, float]] = None
    queued_debit_balance: Optional[Union[int, float]] = None
    track_fund_lineage: Optional[bool] = None
    allocation_strategy: Optional[AllocationStrategy] = None
    meta_data: Optional[Any] = None


@dataclass
class LineageProviderBreakdown(DTO):
    """Per-provider fund breakdown in `BalanceLineageResponse.providers`."""

    provider: str
    # Amounts in minor units; the Core API may send strings or numbers.
    amount: Union[str, int, float]
    available: Union[str, int, float]
    spent: Union[str, int, float]
    shadow_balance_id: str


@dataclass
class BalanceLineageResponse(DTO):
    """Response from `GET balances/{balance_id}/lineage`."""

    balance_id: str
    aggregate_balance_id: str
    total_with_lineage: Union[str, int, float]
    providers: List[LineageProviderBreakdown]


@dataclass
class UpdateBalanceIdentity(DTO):
    """Request body for `PUT balances/{id}/identity`."""

    identity_id: str


@dataclass
class UpdateBalanceIdentityResponse(DTO):
    """Response from `PUT balances/{id}/identity`."""

    message: str


@dataclass
class CreateBalanceSnapshotRequest(DTO):
    """Optional request for `POST balances-snapshots`.

    batch_size: balances processed per batch; omit or zero uses the server
    default (1000). Note: the validator performs no runtime type check on
    this value.
    """

    batch_size: Optional[Union[int, float]] = None


@dataclass
class CreateBalanceSnapshotResponse(DTO):
    """Response from `POST balances-snapshots`."""

    message: str


@dataclass
class HistoricalBalanceDetails(DTO):
    """Balance amounts in `GetBalanceAtResponse.balance`."""

    balance: Union[str, int, float]
    balance_id: str
    credit_balance: Union[str, int, float]
    currency: str
    debit_balance: Union[str, int, float]


@dataclass
class GetBalanceRequest(DTO):
    """Options for `GET balances/{balance_id}`."""

    # Reconstruct balance from transactions instead of snapshots when True.
    # Loosely typed: any value is accepted (e.g. the string "true").
    from_source: Optional[Any] = None
    # Include queued credit/debit balances when True.
    with_queued: Optional[Any] = None


@dataclass
class GetBalanceAtRequest(DTO):
    """Options for `GET balances/{balance_id}/at`."""

    # ISO 8601 timestamp (RFC3339), e.g. `2025-02-24T08:55:26Z` — a plain
    # string, URL-encoded verbatim (never parsed).
    timestamp: str
    # NOT checked by validate_get_balance_at — any truthy value appends
    # `&from_source=true` to the query string.
    from_source: Optional[Any] = None


@dataclass
class GetBalanceAtResponse(DTO):
    """Response from `GET balances/{balance_id}/at`."""

    balance: HistoricalBalanceDetails
    timestamp: str
    from_source: bool
