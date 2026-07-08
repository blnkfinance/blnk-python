"""Request/response types for the Identity service.

`IdentityDateInput` is `str | datetime`. Tokenizable field names are plain
`str` (not an enum); the seven Core names ship as module constants so
invalid/empty strings remain representable and flow through to the
validators.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .base import DTO

IdentityDateInput = Union[str, datetime]

# Core tokenization field names (PascalCase Go struct fields, NOT the
# snake_case IdentityData JSON keys). Note: the validators do NOT restrict to
# this list — any non-empty string passes.
TOKENIZABLE_IDENTITY_FIELDS = (
    "FirstName",
    "LastName",
    "OtherNames",
    "EmailAddress",
    "PhoneNumber",
    "Street",
    "PostCode",
)


@dataclass
class IdentityData(DTO):
    """Request DTO. `identity_type` is required ("individual" | "organization")
    but defaults to None so invalid payloads stay representable for the
    validator (which enforces requiredness). `dob` is str | datetime — the
    identity serializer converts datetimes before the request."""

    identity_id: Optional[str] = None
    identity_type: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    other_names: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[IdentityDateInput] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    nationality: Optional[str] = None
    organization_name: Optional[str] = None
    category: Optional[str] = None
    street: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    post_code: Optional[str] = None
    city: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


@dataclass
class IdentityDataResponse(DTO):
    """Response DTO: all IdentityData fields with `dob` re-typed as an ISO
    STRING (never parsed into datetime), plus required `created_at` and
    `identity_id`. `created_at` may carry nanosecond precision — kept verbatim."""

    identity_id: Optional[str] = None
    identity_type: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    other_names: Optional[str] = None
    gender: Optional[str] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    nationality: Optional[str] = None
    organization_name: Optional[str] = None
    category: Optional[str] = None
    street: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    post_code: Optional[str] = None
    city: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    dob: Optional[str] = None


@dataclass
class TokenizeIdentityData(DTO):
    """`fields` must contain >= 1 PascalCase struct name (validator-enforced)."""

    fields: Optional[List[str]] = None


@dataclass
class TokenizeIdentityResp(DTO):
    message: Optional[str] = None


@dataclass
class TokenizeIdentityFieldResp(DTO):
    message: Optional[str] = None


@dataclass
class GetTokenizedFieldsResp(DTO):
    tokenized_fields: Optional[List[str]] = None


@dataclass
class DetokenizeIdentityData(DTO):
    """An EMPTY `fields` list is allowed (detokenize all tokenized fields)."""

    fields: Optional[List[str]] = None


@dataclass
class DetokenizeIdentityResp(DTO):
    """Original field values keyed by PascalCase field name."""

    fields: Optional[Dict[str, str]] = None


@dataclass
class DetokenizeIdentityFieldResp(DTO):
    field: Optional[str] = None
    value: Optional[str] = None


@dataclass
class DeleteIdentityResp(DTO):
    message: Optional[str] = None
