"""Transaction request/response types.

Dataclasses use the DTO mixin (to_dict omits None-valued fields entirely;
from_dict is tolerant of unknown/missing keys). Field names are the WIRE
names (snake_case) in wire order. Response date/time fields stay plain
strings — never parsed into datetime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Canonical home is blnk_sdk.constants; re-exported here for convenience.
from ..constants import (  # noqa: F401 — re-exports
    MAX_BULK_CREATE_ITEMS,
    MAX_BULK_INFLIGHT_ITEMS,
)
from .base import DTO

# Transaction datetime input. Prefer a datetime so the SDK serializes it;
# string values must match Blnk Core `time.Parse("2006-01-02T15:04:05Z07:00")`.
TransactionDateInput = Union[datetime, str]

# Enum-ish unions stay plain strings so invalid values remain representable
# and are rejected by the validators rather than at construction.
PryTransactionStatus = str  # "QUEUED"|"APPLIED"|"REJECTED"|"COMMIT"|"VOID"|"INFLIGHT"|"EXPIRED"
InflightStatus = str  # "commit" | "void"
StatusType = PryTransactionStatus

PercentageDistribution = str  # e.g. "20%"
LeftDistribution = str  # "left"
FixedAmountDistribution = str  # e.g. "240.23"
Distribution = str  # percentage | "left" | fixed amount

BulkTransactionStatus = str  # "applied" | "inflight" | "queued"
BulkInflightResultStatus = str  # "succeeded" | "failed" | "queued"

# One provider entry in TransactionLineageResponse.fund_allocation.
TransactionLineageFundAllocation = Dict[str, Union[str, int, float, bool, None]]

# Shadow transaction created for fund lineage tracking. The server may send
# arbitrary extra keys, so this is a plain dict.
TransactionLineageShadowTransaction = Dict[str, Any]


@dataclass(kw_only=True)
class MultipleSourcesT(DTO):
    identifier: str
    distribution: Optional[Distribution] = None
    precise_distribution: Optional[Union[str, int, float]] = None
    narration: Optional[str] = None


@dataclass(kw_only=True)
class CreateTransactions(DTO):
    """Request body for POST /transactions. `meta_data` accepts any
    JSON-serializable value."""

    amount: Optional[Union[int, float]] = None
    precise_amount: Optional[Union[int, float, str]] = None
    precision: Union[int, float]
    reference: str
    description: str
    currency: str
    rate: Optional[Union[int, float]] = None
    source: Optional[str] = None
    sources: Optional[List[MultipleSourcesT]] = None
    destinations: Optional[List[MultipleSourcesT]] = None
    destination: Optional[str] = None
    inflight: Optional[bool] = None
    inflight_expiry_date: Optional[TransactionDateInput] = None
    inflight_commit_date: Optional[TransactionDateInput] = None
    scheduled_for: Optional[TransactionDateInput] = None
    effective_date: Optional[TransactionDateInput] = None
    skip_queue: Optional[bool] = None
    atomic: Optional[bool] = None
    allow_overdraft: Optional[bool] = None
    meta_data: Optional[Any] = None


@dataclass(kw_only=True)
class CreateTransactionResponse(DTO):
    """Response from POST /transactions and related transaction mutations.

    `rate` was removed from Core 0.15.0 responses — optional for legacy
    payloads. Zero-value dates arrive as "0001-01-01T00:00:00Z".
    """

    transaction_id: str
    amount: Union[int, float]
    precision: Union[int, float]
    precise_amount: Union[int, float, str]
    reference: str
    description: str
    rate: Optional[Union[int, float]] = None
    currency: str
    status: StatusType
    hash: str  # SHA-256 hash of the transaction details.
    parent_transaction: str  # empty string when none
    source: Optional[str] = None
    destination: Optional[str] = None
    sources: Optional[List[MultipleSourcesT]] = None
    destinations: Optional[List[MultipleSourcesT]] = None
    allow_overdraft: bool
    skip_queue: Optional[bool] = None
    inflight: bool
    queued: Optional[bool] = None
    atomic: Optional[bool] = None
    overdraft_limit: Optional[Union[int, float]] = None
    created_at: Union[datetime, str]
    scheduled_for: Union[datetime, str]
    inflight_expiry_date: Union[datetime, str]
    inflight_commit_date: Union[datetime, str]
    effective_date: Optional[Union[datetime, str]] = None
    meta_data: Optional[Any] = None


@dataclass(kw_only=True)
class UpdateTransactionStatus(DTO):
    """Body for PUT /transactions/inflight/{id} (commit or void)."""

    status: InflightStatus
    amount: Optional[Union[int, float]] = None
    precise_amount: Optional[Union[int, float, str]] = None
    meta_data: Optional[Any] = None
    skip_queue: Optional[bool] = None


@dataclass(kw_only=True)
class RefundTransactionRequest(DTO):
    """Optional body for POST /refund-transaction/{transaction_id}."""

    skip_queue: Optional[bool] = None


@dataclass(kw_only=True)
class BulkTransactions(DTO):
    """Request body for POST /transactions/bulk."""

    atomic: Optional[bool] = None
    inflight: Optional[bool] = None
    run_async: Optional[bool] = None
    skip_queue: Optional[bool] = None
    transactions: List[CreateTransactions] = field(default_factory=list)


@dataclass(kw_only=True)
class BulkTransactionResponse(DTO):
    """Response from POST /transactions/bulk."""

    batch_id: str
    status: str  # BulkTransactionStatus | str
    transaction_count: Optional[Union[int, float]] = None  # sync success only
    message: Optional[str] = None  # async only


@dataclass(kw_only=True)
class BulkCommitInflightItem(DTO):
    """One transaction in POST /transactions/inflight/bulk/commit."""

    transaction_id: str
    amount: Optional[Union[int, float]] = None
    precise_amount: Optional[Union[int, float, str]] = None


@dataclass(kw_only=True)
class BulkCommitInflightRequest(DTO):
    """Request body for POST /transactions/inflight/bulk/commit."""

    skip_queue: Optional[bool] = None
    transactions: List[BulkCommitInflightItem] = field(default_factory=list)


@dataclass(kw_only=True)
class BulkCommitInflightResult(DTO):
    """Per-item outcome in BulkCommitInflightResponse."""

    transaction_id: str
    status: str  # BulkInflightResultStatus | str
    code: Optional[str] = None
    message: Optional[str] = None


@dataclass(kw_only=True)
class BulkCommitInflightResponse(DTO):
    """Response from POST /transactions/inflight/bulk/commit."""

    succeeded: Union[int, float]
    failed: Union[int, float]
    results: List[BulkCommitInflightResult] = field(default_factory=list)


@dataclass(kw_only=True)
class BulkVoidInflightRequest(DTO):
    """Request body for POST /transactions/inflight/bulk/void."""

    skip_queue: Optional[bool] = None
    transaction_ids: List[str] = field(default_factory=list)


@dataclass(kw_only=True)
class BulkVoidInflightResult(DTO):
    """Per-item outcome in BulkVoidInflightResponse."""

    transaction_id: str
    status: str  # BulkInflightResultStatus | str
    code: Optional[str] = None
    message: Optional[str] = None


@dataclass(kw_only=True)
class BulkVoidInflightResponse(DTO):
    """Response from POST /transactions/inflight/bulk/void."""

    succeeded: Union[int, float]
    failed: Union[int, float]
    results: List[BulkVoidInflightResult] = field(default_factory=list)


@dataclass(kw_only=True)
class TransactionLineageResponse(DTO):
    """Response from GET /transactions/{transaction_id}/lineage."""

    transaction_id: str
    fund_allocation: Optional[List[TransactionLineageFundAllocation]] = None
    # Empty when no shadow transactions exist; Core may return null.
    shadow_transactions: Optional[List[TransactionLineageShadowTransaction]] = None


@dataclass(kw_only=True)
class RecoverQueueRequest(DTO):
    """Optional query options for POST /transactions/recover."""

    threshold: Optional[str] = None  # Go duration string, e.g. "5m"


@dataclass(kw_only=True)
class RecoverQueueResponse(DTO):
    """Response from POST /transactions/recover."""

    recovered: Union[int, float]
    threshold: str  # e.g. "5m0s"
