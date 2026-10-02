"""Percent-encoding for URL path segments and query values (used by the
transactions/balance-monitor/ledger-balances/identity/api-keys services when
building endpoint paths, and by the client when appending instance_id)."""

from __future__ import annotations

from urllib.parse import quote

# Every character is percent-encoded except the unreserved set:
# A-Z a-z 0-9 - _ . ! ~ * ' ( )
_SAFE = "-_.!~*'()"


def percent_encode(value: str) -> str:
    return quote(str(value), safe=_SAFE)


def append_query_param(endpoint: str, name: str, value: str) -> str:
    """Append one encoded query pair to an endpoint that may already have a
    query string. Uses `&` when `?` is already present, otherwise `?`."""
    pair = f"{percent_encode(name)}={percent_encode(value)}"
    separator = "&" if "?" in endpoint else "?"
    return f"{endpoint}{separator}{pair}"
