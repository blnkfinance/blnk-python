"""Live coverage of Search.multi_search against Core's POST /multi-search
(in Core since v0.10.0; this SDK is aligned with 0.15.4).

Skipped unless BLNK_E2E=1 — the same env var gates the rest of the
integration suite.
"""

from __future__ import annotations

import os
import time
import uuid

import pytest

from blnk_sdk.client import BlnkClientOptions, blnk_init
from tests.utils import BASE_URL, BLNK_API_KEY, sleep_seconds

pytestmark = pytest.mark.skipif(
    os.environ.get("BLNK_E2E") != "1",
    reason="requires live Blnk Core at http://localhost:5001/ (set BLNK_E2E=1)",
)

CLIENT_OPTIONS = BlnkClientOptions(base_url=BASE_URL)
CLIENT = blnk_init(BLNK_API_KEY, CLIENT_OPTIONS)


def test_multi_search_mixed_collections() -> None:
    """multiSearch ledgers then balances; first result bucket matches first search"""
    ledger_name = f"Python MultiSearch {uuid.uuid4()}"
    created = CLIENT.ledgers.create({"name": ledger_name})
    assert created.status == 201, created.message

    deadline = time.time() + 30
    response = None
    while True:
        response = CLIENT.search.multi_search(
            {
                "searches": [
                    {
                        "collection": "ledgers",
                        "q": ledger_name,
                        "query_by": "name",
                        "per_page": 5,
                    },
                    {
                        "collection": "balances",
                        "q": "*",
                        "query_by": "currency",
                        "per_page": 1,
                    },
                ]
            }
        )
        data = response.data or {}
        results = data.get("results")
        if (
            response.status == 200
            and isinstance(results, list)
            and len(results) == 2
            and (results[0] or {}).get("found", 0) > 0
        ):
            break
        if time.time() > deadline:
            assert response.status == 200, response.message
            assert isinstance(results, list), data
            assert len(results) == 2, data
            assert (results[0] or {}).get("found", 0) > 0, (
                "expected indexed ledger in first results bucket: " + str(data)
            )
            break
        sleep_seconds(0.5)

    assert response.status == 200, response.message
    results = (response.data or {}).get("results")
    assert isinstance(results, list)
    assert len(results) == 2
    assert (results[0] or {}).get("found", 0) > 0
    assert (results[1] or {}).get("found", -1) >= 0
