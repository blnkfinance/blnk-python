"""Request/response types for the Hooks service.

Field names are the wire names (snake_case), declared in wire order. Response
date/time fields (`created_at`, `last_run`) stay plain strings passed through
verbatim — never parsed or reformatted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from .base import DTO

# Hook type: "PRE_TRANSACTION" or "POST_TRANSACTION". Modeled as a plain str
# (not an enum) so invalid values remain representable and the validator's
# invalid-value branch (`type must be PRE_TRANSACTION or POST_TRANSACTION`)
# stays reachable; the two literals are exposed as module constants.
HookType = str

PRE_TRANSACTION = "PRE_TRANSACTION"
POST_TRANSACTION = "POST_TRANSACTION"


@dataclass
class CreateHookData(DTO):
    """Request body for `POST hooks` / `PUT hooks/{id}`. All fields are
    required — a well-formed payload always has all 6 fields on the wire."""

    name: str
    url: str
    type: HookType
    active: bool
    timeout: Union[int, float]
    retry_count: Union[int, float]


# Update requests use the same shape as create requests.
UpdateHookData = CreateHookData


@dataclass
class ListHooksOptions(DTO):
    """Options for `GET hooks` (optional `?type=` filter).

    Omit ``type`` (or call ``hooks.list()`` with no options) to list PRE
    and POST hooks together. Core 0.15.3+ returns both when the filter is
    absent.
    """

    type: Optional[HookType] = None


@dataclass
class HookResp(DTO):
    """Response shape for create/list/get/update."""

    id: str
    name: str
    url: str
    type: HookType
    active: bool
    timeout: Union[int, float]
    retry_count: Union[int, float]
    created_at: str  # server timestamp string — never parsed
    last_run: str  # server timestamp string (e.g. "0001-01-01T00:00:00Z")
    last_success: bool


@dataclass
class DeleteHookResp(DTO):
    """Response from `DELETE hooks/{id}`."""

    message: str
