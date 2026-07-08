"""Percent-encoding for URL path segments and query values (used by the
transactions/balance-monitor/ledger-balances/identity/api-keys services when
building endpoint paths)."""

from __future__ import annotations

from urllib.parse import quote

# Every character is percent-encoded except the unreserved set:
# A-Z a-z 0-9 - _ . ! ~ * ' ( )
_SAFE = "-_.!~*'()"


def percent_encode(value: str) -> str:
    return quote(str(value), safe=_SAFE)
