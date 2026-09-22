"""Validators for GET list pagination (`ListOptions`).

Same rules Core applies on ledgers and balances (`limit >= 1`,
`offset >= 0`), checked before the request is sent. Transactions Core
silently defaults invalid pagination; the SDK still rejects it here so
caller mistakes stay visible.
"""

from __future__ import annotations

from typing import Any, Optional

from ..types import DTO

__all__ = ["validate_list_options"]


def validate_list_options(data: Any) -> Optional[str]:
    """Returns None when valid, otherwise the failure message.

    Limit is checked before offset. An absent key is skipped; a key
    present with a non-int (including None and bool) fails.
    """
    if isinstance(data, DTO):
        data = data.to_dict()

    if not isinstance(data, dict):
        return "Data must be a valid object of type ListOptions"

    if "limit" in data:
        limit = data["limit"]
        if not isinstance(limit, int) or isinstance(limit, bool):
            return "limit must be an integer if provided"
        if limit < 1:
            return "limit must be at least 1"

    if "offset" in data:
        offset = data["offset"]
        if not isinstance(offset, int) or isinstance(offset, bool):
            return "offset must be an integer if provided"
        if offset < 0:
            return "offset must be at least 0"

    return None
