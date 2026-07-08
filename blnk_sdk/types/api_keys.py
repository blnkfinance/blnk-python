"""Request/response types for the API keys service.

Field names are the wire names (snake_case), declared in wire order.
Timestamp fields (`expires_at`, `created_at`, `last_used_at`, `revoked_at`)
stay plain strings passed through verbatim — never parsed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .base import DTO


@dataclass
class CreateApiKeyData(DTO):
    """Request body for `POST api-keys`. All fields are required.

    `expires_at` is a caller-supplied ISO 8601 string (e.g.
    `2026-03-11T00:00:00Z`) — validated, then sent VERBATIM (never converted
    to/from a datetime, never reformatted)."""

    name: str
    owner: str
    scopes: List[str]
    expires_at: str


@dataclass
class ListApiKeysOptions(DTO):
    """Options for `GET api-keys` (optional `?owner=` filter)."""

    owner: Optional[str] = None


@dataclass
class DeleteApiKeyOptions(DTO):
    """Options for `DELETE api-keys/{id}` (optional `?owner=` filter)."""

    owner: Optional[str] = None


@dataclass
class ApiKeyResp(DTO):
    """Response shape for create/list. `ApiKeys.delete` returns no body, so
    its response data is always None."""

    api_key_id: str
    key: str
    name: str
    owner_id: str
    scopes: List[str]
    expires_at: str
    created_at: str
    last_used_at: str
    is_revoked: bool
    revoked_at: Optional[str] = None
