"""Request/response types for the Search service.

Wire conventions:
- All Typesense timestamps are Unix-seconds NUMBERS (`created_at`, `dob`,
  `scheduled_for`, `inflight_expiry_date`, `effective_date`,
  `inflight_expires_at`); `dob` can be negative. Never parse into datetimes.
- Balance monetary fields (`balance`, `credit_balance`, ...) and transaction
  `precise_amount` are STRINGS (minor-unit values); transaction `amount` is a
  number.
- `ReindexProgress.started_at`/`completed_at` are raw server strings passed
  through verbatim (values may carry up to eight fractional digits).
- Response dataclasses use `kw_only=True` so the wire field order is
  preserved even where a required field follows optional ones (construction
  is keyword-only).
- Document shapes are not enforced per collection at runtime: `document`
  and filter records are dynamically typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union

from .base import DTO

# Collection names supported by `Search.search`. Runtime representation is a
# plain str (NOT an enum, so invalid collection names stay representable and
# the invalid-collection validation path stays reachable); the Literal is a
# type-hint only.
SearchCollection = Literal["ledgers", "transactions", "balances", "identities"]

# Filter operators supported by `POST {collection}/filter` (hints only).
FilterOperator = Literal[
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "between",
    "like",
    "ilike",
    "isnull",
    "isnotnull",
]
FilterLogicalOperator = Literal["and", "or"]
FilterSortOrder = Literal["asc", "desc"]


@dataclass
class SearchParams(DTO):
    """Request body for `POST search/{collection}`. Optional fields are
    omitted from the wire body entirely when None."""

    q: str
    query_by: Optional[str] = None
    filter_by: Optional[str] = None
    sort_by: Optional[str] = None
    page: Optional[Union[int, float]] = None
    per_page: Optional[Union[int, float]] = None


@dataclass
class SearchRequestParams(SearchParams):
    """Request params echoed by Typesense (may include `collection_name`)."""

    collection_name: Optional[str] = None


@dataclass
class MultiSearchCollectionParams(DTO):
    """One entry in a `POST multi-search` body: a normal search plus
    `collection`. Optional fields are omitted when None."""

    collection: str
    q: str
    query_by: Optional[str] = None
    filter_by: Optional[str] = None
    sort_by: Optional[str] = None
    page: Optional[Union[int, float]] = None
    per_page: Optional[Union[int, float]] = None


@dataclass
class MultiSearchParams(DTO):
    """Request body for `POST multi-search`: several single-collection
    searches in one round trip. Wire shape is Typesense's
    `{"searches":[{"collection":..., "q":..., ...}]}`; results come back in
    the same order. `add()` appends an entry the same way Java's builder
    does; a plain dict with a `searches` list is also accepted by
    `Search.multi_search`."""

    searches: List[Any] = field(default_factory=list)

    def add(self, collection: str, params: Any = None) -> "MultiSearchParams":
        """Appends one search against `collection`; `params` fields are
        copied in beside it (dict or `SearchParams.to_dict()`)."""
        entry: Dict[str, Any] = {"collection": collection}
        if params is not None:
            if isinstance(params, dict):
                serialized = params
            else:
                to_dict = getattr(params, "to_dict", None)
                serialized = to_dict() if callable(to_dict) else params
            if isinstance(serialized, dict):
                entry.update(serialized)
        self.searches.append(entry)
        return self


@dataclass(kw_only=True)
class SearchHit(DTO):
    """Single Typesense hit; `document` shape depends on the collection."""

    document: Any
    highlights: Optional[List[Any]] = None
    highlight: Optional[Dict[str, Any]] = None
    text_match: Optional[Union[int, float]] = None


@dataclass(kw_only=True)
class SearchGroupedHit(DTO):
    group_key: Optional[List[str]] = None
    hits: List[SearchHit]


@dataclass(kw_only=True)
class SearchResponse(DTO):
    """Generic Typesense search response. The document shape is not enforced
    at runtime — `hits[i].document` carries whatever the server provided,
    depending on the collection searched."""

    found: Union[int, float]
    out_of: Union[int, float]
    page: Union[int, float]
    request_params: Any
    search_time_ms: Union[int, float]
    facet_counts: Optional[List[Any]] = None
    search_cutoff: Optional[bool] = None
    hits: List[SearchHit]
    grouped_hits: Optional[List[SearchGroupedHit]] = None


@dataclass(kw_only=True)
class SearchLedgerDocument(DTO):
    """Ledger document shape returned by `POST search/ledgers`."""

    id: str
    ledger_id: str
    name: str
    created_at: int  # Unix timestamp seconds — NOT a date object
    meta_data: Optional[Dict[str, Any]] = None


@dataclass(kw_only=True)
class SearchBalanceDocument(DTO):
    """Balance document shape returned by `POST search/balances`. Monetary
    fields are minor-unit STRINGS."""

    id: str
    balance_id: str
    balance: str
    credit_balance: Optional[str] = None
    debit_balance: Optional[str] = None
    inflight_balance: Optional[str] = None
    inflight_credit_balance: Optional[str] = None
    inflight_debit_balance: Optional[str] = None
    currency: Optional[str] = None
    precision: Optional[Union[int, float]] = None
    ledger_id: Optional[str] = None
    identity_id: Optional[str] = None
    indicator: Optional[str] = None
    version: Optional[Union[int, float]] = None
    allocation_strategy: Optional[str] = None
    track_fund_lineage: Optional[bool] = None
    inflight_expires_at: Optional[int] = None  # Unix timestamp seconds
    created_at: int  # Unix timestamp seconds
    meta_data: Optional[Dict[str, Any]] = None


@dataclass(kw_only=True)
class SearchTransactionDocument(DTO):
    """Transaction document shape returned by `POST search/transactions`.
    `precise_amount` is a string; `amount` is a number."""

    id: str
    transaction_id: str
    amount: Optional[Union[int, float]] = None
    amount_string: Optional[str] = None
    precise_amount: Optional[str] = None
    precision: Optional[Union[int, float]] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    hash: Optional[str] = None
    parent_transaction: Optional[str] = None
    atomic: Optional[bool] = None
    inflight: Optional[bool] = None
    allow_overdraft: Optional[bool] = None
    overdraft_limit: Optional[Union[int, float]] = None
    skip_queue: Optional[bool] = None
    created_at: int  # Unix timestamp seconds
    scheduled_for: Optional[int] = None  # Unix timestamp seconds
    inflight_expiry_date: Optional[int] = None  # Unix timestamp seconds
    effective_date: Optional[int] = None  # Unix timestamp seconds
    meta_data: Optional[Dict[str, Any]] = None


@dataclass(kw_only=True)
class SearchIdentityDocument(DTO):
    """Identity document shape returned by `POST search/identities`. `dob` is
    Unix seconds and can be NEGATIVE for dates before 1970 (the zero date
    0001-01-01 arrives as -62135596800)."""

    id: str
    identity_id: str
    identity_type: str
    organization_name: Optional[str] = None
    category: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    other_names: Optional[str] = None
    gender: Optional[str] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    nationality: Optional[str] = None
    street: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    post_code: Optional[str] = None
    city: Optional[str] = None
    dob: Optional[int] = None  # Unix timestamp seconds (may be negative)
    created_at: int  # Unix timestamp seconds
    meta_data: Optional[Dict[str, Any]] = None


# Collection-specific aliases of the generic search types.
SearchIdentityHit = SearchHit
SearchIdentityResponse = SearchResponse
SearchLedgerResponse = SearchResponse
SearchBalanceResponse = SearchResponse
SearchTransactionResponse = SearchResponse


@dataclass
class FilterCondition(DTO):
    """Single filter condition in a DB filter request.

    A None `value` reads as ABSENT via `to_dict()`: an unset value and an
    explicit None serialize identically, and both fail the validator's
    value check for scalar operators.
    """

    field: str
    operator: str
    value: Any = None
    values: Optional[List[Any]] = None


@dataclass
class FilterParams(DTO):
    """Request body for `POST {collection}/filter` (Search via DB).
    `filters` may be EMPTY — no minimum-length rule is enforced."""

    filters: List[Any]
    logical_operator: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    include_count: Optional[bool] = None
    limit: Optional[Union[int, float]] = None
    offset: Optional[Union[int, float]] = None


@dataclass
class FilterResponse(DTO):
    """Response from `POST {collection}/filter`. Records are dynamic parsed
    objects; `total_count` stays optional."""

    data: List[Any]
    total_count: Optional[int] = None


@dataclass
class StartReindexRequest(DTO):
    """Optional body for `POST search/reindex`."""

    batch_size: Optional[Union[int, float]] = None


@dataclass
class ReindexProgress(DTO):
    """Progress snapshot returned by reindex endpoints. `started_at` and
    `completed_at` are raw server strings, passed through verbatim (never
    reformatted — values may carry up to eight fractional digits)."""

    status: str
    phase: str
    total_records: Union[int, float]
    processed_records: Union[int, float]
    started_at: str
    completed_at: Optional[str] = None
    errors: Optional[List[str]] = None


@dataclass
class StartReindexResponse(DTO):
    """Response from `POST search/reindex`."""

    message: str
    progress: Any


# Response from `GET search/reindex`.
GetReindexStatusResponse = ReindexProgress
