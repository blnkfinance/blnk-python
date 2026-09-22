"""Pagination for Core GET list routes.

`limit` and `offset` travel as query parameters. Unset fields are omitted
from the query string so Core can apply its per-route defaults (`limit=10`
for ledgers and balances, `limit=20` for transactions; `offset=0` on all
three).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .base import DTO

_LIST_QUERY_KEYS = ("limit", "offset")


def list_options_query_string(data: Any) -> str:
    """`?limit=20&offset=40` in dict insertion order, or `""` when empty.

    Only `limit` and `offset` are forwarded. Values are interpolated as-is
    (no URL-encoding), matching the Java SDK's ListOptions.toQueryString.
    """
    if not isinstance(data, dict):
        return ""
    parts: list[str] = []
    for key, value in data.items():
        if key in _LIST_QUERY_KEYS:
            parts.append(f"{key}={value}")
    if not parts:
        return ""
    return "?" + "&".join(parts)


def list_endpoint(path: str, options: Any = None) -> tuple[Optional[str], str]:
    """Validate optional list options and append their query string.

    `options is None` means "not provided": no validation, no query.
    Returns `(error_message, endpoint)`; the endpoint is unchanged when
    validation fails so callers can skip the request.
    """
    from ..validators.list_validators import validate_list_options

    if options is None:
        return None, path

    if isinstance(options, dict):
        view: Any = options
    else:
        to_dict = getattr(options, "to_dict", None)
        view = to_dict() if callable(to_dict) else options

    error = validate_list_options(view)
    if error:
        return error, path
    return None, path + list_options_query_string(view)


@dataclass
class ListOptions(DTO):
    """Optional pagination for `ledgers.list`, `ledger_balances.list`, and
    `transactions.list`. None-valued fields are omitted from the wire."""

    limit: Optional[int] = None
    offset: Optional[int] = None

    def to_query_string(self) -> str:
        return list_options_query_string(self.to_dict())
