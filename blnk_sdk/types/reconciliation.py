"""Request/response types for the Reconciliation service.

Enum-ish unions stay plain `str` so invalid values remain representable and
are rejected by the validators rather than at construction:
  CriteriaField = "amount" | "currency" | "reference" | "description" | "date"
  Operator      = "equals" | "greater_than" | "less_than" | "contains"
  Strategy      = "one_to_one" | "one_to_many" | "many_to_one"

Request DTOs: to_dict() omits None-valued optionals from the wire body
entirely — Criteria.allowable_drift, RunInstantReconData.dry_run and
.grouping_criteria. Note the intentional asymmetry: RunReconData fields are
all required while RunInstantReconData's dry_run/grouping_criteria are
optional.

Response timestamp fields (created_at / updated_at / started_at /
completed_at) and ExternalTransaction.date stay plain strings — never parsed
(server values may carry sub-millisecond precision, e.g.
"2026-06-12T04:31:55.715443261Z"); completed_at may be JSON null.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from .base import DTO


@dataclass
class ReconciliationUploadResp(DTO):
    upload_id: str
    record_count: int
    source: str


@dataclass
class Criteria(DTO):
    field: str
    operator: str
    allowable_drift: Optional[float] = None


@dataclass
class Matcher(DTO):
    name: str
    description: str
    criteria: List[Any]


@dataclass
class RunReconData(DTO):
    upload_id: str
    strategy: str
    dry_run: bool
    grouping_criteria: str
    matching_rule_ids: List[str]


@dataclass
class RunReconResp(DTO):
    """Response from `POST /reconciliation/start`."""

    reconciliation_id: str


@dataclass
class MatchingRuleResp(DTO):
    """Matching-rule response: echoes the Matcher fields (name / description /
    criteria) plus rule_id / created_at / updated_at."""

    name: str
    description: str
    criteria: List[Any]
    rule_id: str
    created_at: str
    updated_at: str


@dataclass
class ExternalTransaction(DTO):
    id: str
    amount: float
    reference: str
    currency: str
    description: str
    date: str
    source: str


@dataclass
class RunInstantReconData(DTO):
    """Request body for `POST /reconciliation/start-instant`. The optional
    fields (`dry_run`, `grouping_criteria`) are declared last per Python
    default-argument rules."""

    external_transactions: List[Any]
    strategy: str
    matching_rule_ids: List[str]
    dry_run: Optional[bool] = None
    grouping_criteria: Optional[str] = None


@dataclass
class RunInstantReconResp(DTO):
    reconciliation_id: str


@dataclass
class DeleteMatchingRuleResp(DTO):
    message: str


@dataclass
class ReconciliationResp(DTO):
    reconciliation_id: str
    upload_id: str
    status: str
    matched_transactions: int
    unmatched_transactions: int
    is_dry_run: bool
    started_at: str
    completed_at: Optional[str] = None
