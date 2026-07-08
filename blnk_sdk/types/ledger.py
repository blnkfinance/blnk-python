"""Request/response types for the Ledgers service.

Response date/time fields (`created_at`) stay plain strings — never parsed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import DTO


@dataclass
class CreateLedger(DTO):
    """Request body for `POST ledgers`. `meta_data` is optional; when None
    the key is omitted from the wire body entirely."""

    name: str
    meta_data: Optional[Dict[str, Any]] = None


@dataclass
class UpdateLedger(DTO):
    """Request body for `PUT /ledgers/{id}`."""

    name: str


@dataclass
class CreateLedgerResp(DTO):
    """Response shape for create/get/update. `created_at` is a server-provided
    ISO-8601 string passed through verbatim."""

    ledger_id: str
    name: str
    created_at: str
    meta_data: Optional[Dict[str, Any]] = None
