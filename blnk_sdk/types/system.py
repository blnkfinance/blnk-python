"""Response types for system endpoints (health check)."""

from __future__ import annotations

from dataclasses import dataclass

from .base import DTO


@dataclass
class HealthResponse(DTO):
    """Response from `GET health` — Core returns `{"status": "UP"}`.

    The server may send extra keys; parsing is lenient — service methods
    return the raw parsed dict on ApiResponse.data.
    """

    status: str
