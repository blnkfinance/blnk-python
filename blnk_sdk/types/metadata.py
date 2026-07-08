"""Request/response types for entity metadata updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .base import DTO


@dataclass
class UpdateMetadataData(DTO):
    """Request body for `POST {id}/metadata`."""

    meta_data: Dict[str, Any]


@dataclass
class UpdateMetadataResp(DTO):
    """Response from `POST {id}/metadata`."""

    meta_data: Dict[str, Any]
