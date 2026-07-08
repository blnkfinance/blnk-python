"""Typed-usage helpers for the Search service and its response types.

These functions spell out representative typed usages of `Search.search`
results across collections and of the unparameterized `SearchResponse` shape.
The test suite deliberately only references them (asserting they are
callable) rather than executing them; running them against a mocked `Search`
service would also succeed.
"""

from __future__ import annotations

from typing import Any

from blnk_sdk.types.search import (
    SearchBalanceDocument,
    SearchHit,
    SearchRequestParams,
    SearchResponse,
)


def assert_search_search_types(search: Any) -> None:
    """Exercises typed access to `Search.search` results per collection."""
    params = {"q": "*"}

    transactions_response = search.search(params, "transactions")
    data = transactions_response.data
    hits = getattr(data, "hits", None) if data is not None else None
    transaction_hit = hits[0] if hits else None
    if transaction_hit:
        status = transaction_hit.document.status  # str | None
        transaction_id = transaction_hit.document.transaction_id  # str
        del status, transaction_id
        # `balance` is indexed on balance documents only, so it is
        # intentionally never read off a transaction hit here.

    def dynamic_search(service: str) -> None:
        """The union-typed SearchCollection variable is accepted and
        `document.id` reads as a string."""
        response = search.search(params, service)
        response_data = response.data
        response_hits = (
            getattr(response_data, "hits", None) if response_data is not None else None
        )
        hit = response_hits[0] if response_hits else None
        if hit:
            document_id = hit.document.id  # str
            del document_id

    del dynamic_search


def assert_legacy_search_response_usage() -> None:
    """Ensures unparameterized `SearchResponse` usage (defaulting to the
    balance document shape) still constructs (SDK compat)."""
    response = SearchResponse(
        found=1,
        out_of=45,
        page=1,
        request_params=SearchRequestParams(collection_name="balances", q="*"),
        search_time_ms=1,
        hits=[
            SearchHit(
                document=SearchBalanceDocument(
                    id="bln_15168eb4-bdb1-4e46-9331-f58a6a16b254",
                    balance_id="bln_15168eb4-bdb1-4e46-9331-f58a6a16b254",
                    balance="0",
                    credit_balance="0",
                    debit_balance="0",
                    currency="USD",
                    ledger_id="ldg_0921bd99-ff7c-4a06-b6d7-319f0bb12f87",
                    created_at=1781222909,
                )
            )
        ],
    )

    balance_id = response.hits[0].document.balance_id  # str
    del balance_id
