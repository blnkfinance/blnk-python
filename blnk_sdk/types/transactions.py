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
    # Preview the post without writing. Default: False. When True, Core
    # returns HTTP 200 and a TransactionPreview — not a posted transaction.
    dry_run: Optional[bool] = None
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
    # Preview commit/void without settling the hold. Default: False.
    dry_run: Optional[bool] = None


@dataclass(kw_only=True)
class RefundTransactionRequest(DTO):
    """Optional body for POST /refund-transaction/{transaction_id}."""

    skip_queue: Optional[bool] = None
    # Replaces the reversal description. Empty/omitted inherits the original.
    description: Optional[str] = None
    # Merged onto metadata inherited from the original transaction.
    meta_data: Optional[Any] = None
    # Preview the refund without writing. Default: False.
    dry_run: Optional[bool] = None


@dataclass(kw_only=True)
class BulkTransactions(DTO):
    """Request body for POST /transactions/bulk."""

    atomic: Optional[bool] = None
    inflight: Optional[bool] = None
    run_async: Optional[bool] = None
    skip_queue: Optional[bool] = None
    # Preview the batch without writing. Default: False. run_async is
    # ignored on a bulk dry run.
    dry_run: Optional[bool] = None
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
    # Preview the batch without committing. Default: False.
    dry_run: Optional[bool] = None
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
    # Preview the batch without voiding. Default: False.
    dry_run: Optional[bool] = None
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


@dataclass(kw_only=True)
class PreviewRejection(DTO):
    """Why a dry-run projection would not apply."""

    code: str
    reason: str
    message: str


@dataclass(kw_only=True)
class BalanceProjection(DTO):
    """One balance's current and projected state in a dry-run.

    Amounts are minor-unit strings.
    """

    balance_id: str
    role: str
    currency: str
    virtual: Optional[bool] = None
    current_balance: str
    current_available: Optional[str] = None
    current_credit_balance: Optional[str] = None
    current_debit_balance: Optional[str] = None
    current_inflight_debit_balance: Optional[str] = None
    current_inflight_credit_balance: Optional[str] = None
    resulting_balance: str
    resulting_available: Optional[str] = None
    resulting_credit_balance: Optional[str] = None
    resulting_debit_balance: Optional[str] = None
    resulting_inflight_debit_balance: Optional[str] = None
    resulting_inflight_credit_balance: Optional[str] = None


@dataclass(kw_only=True)
class LegProjection(DTO):
    """One split leg in a multi-source or multi-destination dry-run."""

    identifier: str
    role: str
    precise_amount: str
    amount: Union[int, float]


def _as_nested_dto(cls: Any, value: Any) -> Any:
    if isinstance(value, dict):
        return cls.from_dict(value)
    return value


def _as_nested_dto_list(cls: Any, values: Any) -> Any:
    if not isinstance(values, list):
        return values
    return [_as_nested_dto(cls, item) for item in values]


@dataclass(kw_only=True)
class TransactionPreview(DTO):
    """Response from a dry-run create, refund, or inflight update (HTTP 200).

    This is a projection, not a recorded transaction — there is no
    ``transaction_id`` and ``reference`` is not consumed.

    See https://docs.blnkfinance.com/transactions/dry-run
    """

    dry_run: bool
    would_apply: bool
    rejection: Optional[PreviewRejection] = None
    operation: Optional[str] = None  # "commit" | "void" on inflight previews
    status: Optional[StatusType] = None
    reference: Optional[str] = None
    currency: str
    amount: Union[int, float]
    precise_amount: str
    precision: Union[int, float]
    balances: List[BalanceProjection] = field(default_factory=list)
    legs: Optional[List[LegProjection]] = None
    notes: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Any):
        obj = super().from_dict(data)
        obj.rejection = _as_nested_dto(PreviewRejection, obj.rejection)
        obj.balances = _as_nested_dto_list(BalanceProjection, obj.balances) or []
        obj.legs = _as_nested_dto_list(LegProjection, obj.legs)
        return obj


@dataclass(kw_only=True)
class BulkTransactionPreview(DTO):
    """Response from a dry-run bulk create / bulk inflight (HTTP 200).

    See https://docs.blnkfinance.com/transactions/dry-run
    """

    dry_run: bool
    would_apply: bool
    cumulative: bool
    atomic: Optional[bool] = None
    results: List[TransactionPreview] = field(default_factory=list)
    balances: Optional[List[BalanceProjection]] = None
    notes: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Any):
        obj = super().from_dict(data)
        obj.results = _as_nested_dto_list(TransactionPreview, obj.results) or []
        obj.balances = _as_nested_dto_list(BalanceProjection, obj.balances)
        return obj


def is_transaction_preview(data: Any) -> bool:
    """True when a response body is a single-transaction dry-run preview."""
    if isinstance(data, TransactionPreview):
        return True
    return (
        isinstance(data, dict)
        and data.get("dry_run") is True
        and "would_apply" in data
        and "results" not in data
    )


def is_bulk_transaction_preview(data: Any) -> bool:
    """True when a response body is a bulk dry-run preview."""
    if isinstance(data, BulkTransactionPreview):
        return True
    return (
        isinstance(data, dict)
        and data.get("dry_run") is True
        and isinstance(data.get("results"), list)
    )
