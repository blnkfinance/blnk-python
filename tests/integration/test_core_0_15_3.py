"""Live Core 0.15.3 checks for the Python SDK.

Requires Blnk Core at http://localhost:5001 (or BLNK_BASE_URL).
Skipped unless BLNK_E2E=1.
"""

from __future__ import annotations

import os
import time

import pytest

from blnk_sdk import BlnkErrorCode, BlnkClientOptions, blnk_init
from blnk_sdk.types.transactions import (
    BulkTransactionPreview,
    TransactionPreview,
    is_bulk_transaction_preview,
    is_transaction_preview,
)
from tests.utils import (
    BASE_URL,
    BLNK_API_KEY,
    generate_random_numbers_with_prefix,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("BLNK_E2E") != "1",
    reason="requires live Blnk Core at http://localhost:5001/ (set BLNK_E2E=1)",
)

CLIENT = blnk_init(BLNK_API_KEY, BlnkClientOptions(base_url=BASE_URL))


def test_core_0_15_3_sdk_patch() -> None:
    health = CLIENT.system.health()
    assert health.status == 200
    assert (health.data or {}).get("status") == "UP"

    indicator = f"@SdkPy{int(time.time() * 1000)}"
    gl = CLIENT.ledger_balances.create(
        {
            "ledger_id": "general_ledger_id",
            "currency": "USD",
            "indicator": indicator,
        }
    )
    assert gl.status == 201, f"GL create: {gl.message}"
    assert (gl.data or {}).get("indicator") == indicator
    assert (gl.data or {}).get("ledger_id") == "general_ledger_id"

    dest = f"@SdkPyDest{int(time.time() * 1000)}"
    preview = CLIENT.transactions.create(
        {
            "amount": 25,
            "precision": 100,
            "reference": generate_random_numbers_with_prefix("dryrun", 8),
            "description": "SDK dry-run",
            "currency": "USD",
            "source": indicator,
            "destination": dest,
            "allow_overdraft": True,
            "dry_run": True,
        }
    )
    assert preview.status == 200, f"dry-run status: {preview.status}"
    assert is_transaction_preview(preview.data)
    typed_preview = TransactionPreview.from_dict(preview.data)
    assert typed_preview.dry_run is True
    assert typed_preview.would_apply is True
    assert typed_preview.balances
    assert "transaction_id" not in (preview.data or {})

    # Reusing the same reference after a dry-run must still post.
    reuse_reference = generate_random_numbers_with_prefix("reuse", 8)
    reuse_preview = CLIENT.transactions.create(
        {
            "amount": 5,
            "precision": 100,
            "reference": reuse_reference,
            "description": "reuse after dry-run",
            "currency": "USD",
            "source": indicator,
            "destination": dest,
            "allow_overdraft": True,
            "dry_run": True,
        }
    )
    assert reuse_preview.status == 200
    posted_reuse = CLIENT.transactions.create(
        {
            "amount": 5,
            "precision": 100,
            "reference": reuse_reference,
            "description": "reuse after dry-run",
            "currency": "USD",
            "source": indicator,
            "destination": dest,
            "allow_overdraft": True,
            "skip_queue": True,
        }
    )
    assert posted_reuse.status == 201, f"reuse post: {posted_reuse.message}"

    bulk_preview = CLIENT.transactions.create_bulk(
        {
            "dry_run": True,
            "transactions": [
                {
                    "amount": 10,
                    "precision": 100,
                    "reference": generate_random_numbers_with_prefix("bulk-a", 8),
                    "description": "bulk preview 1",
                    "currency": "USD",
                    "source": indicator,
                    "destination": dest,
                    "allow_overdraft": True,
                },
                {
                    "amount": 15,
                    "precision": 100,
                    "reference": generate_random_numbers_with_prefix("bulk-b", 8),
                    "description": "bulk preview 2",
                    "currency": "USD",
                    "source": indicator,
                    "destination": dest,
                    "allow_overdraft": True,
                },
            ],
        }
    )
    assert bulk_preview.status == 200, f"bulk dry-run: {bulk_preview.message}"
    assert is_bulk_transaction_preview(bulk_preview.data)
    typed_bulk = BulkTransactionPreview.from_dict(bulk_preview.data)
    assert typed_bulk.dry_run is True
    assert typed_bulk.would_apply is True

    posted = CLIENT.transactions.create(
        {
            "amount": 20,
            "precision": 100,
            "reference": generate_random_numbers_with_prefix("posted", 8),
            "description": "SDK posted for refund",
            "currency": "USD",
            "source": indicator,
            "destination": dest,
            "allow_overdraft": True,
            "skip_queue": True,
        }
    )
    assert posted.status == 201, f"posted create: {posted.message}"
    posted_id = (posted.data or {}).get("transaction_id")
    assert posted_id

    refund_preview = CLIENT.transactions.refund(posted_id, {"dry_run": True})
    assert refund_preview.status == 200, f"refund dry-run: {refund_preview.message}"
    assert (refund_preview.data or {}).get("dry_run") is True

    refunded = CLIENT.transactions.refund(
        posted_id,
        {
            "skip_queue": True,
            "description": "SDK refund narration",
            "meta_data": {"channel": "sdk-test"},
        },
    )
    assert refunded.status == 201, f"refund: {refunded.message}"
    assert (refunded.data or {}).get("description") == "SDK refund narration"

    hold = CLIENT.transactions.create(
        {
            "amount": 30,
            "precision": 100,
            "reference": generate_random_numbers_with_prefix("hold", 8),
            "description": "SDK inflight hold",
            "currency": "USD",
            "source": indicator,
            "destination": dest,
            "allow_overdraft": True,
            "inflight": True,
            "skip_queue": True,
        }
    )
    assert hold.status == 201, f"inflight create: {hold.message}"
    hold_id = (hold.data or {}).get("transaction_id")
    assert hold_id

    inflight_preview = CLIENT.transactions.update_status(
        hold_id, {"status": "commit", "dry_run": True}
    )
    assert inflight_preview.status == 200, f"inflight dry-run: {inflight_preview.message}"
    assert (inflight_preview.data or {}).get("dry_run") is True
    assert (inflight_preview.data or {}).get("operation") == "commit"

    after_inflight_preview = CLIENT.transactions.get(hold_id)
    assert (after_inflight_preview.data or {}).get("status") == "INFLIGHT"

    commit_preview = CLIENT.transactions.bulk_commit_inflight(
        {
            "dry_run": True,
            "skip_queue": True,
            "transactions": [{"transaction_id": hold_id}],
        }
    )
    assert commit_preview.status == 200, f"bulk commit dry-run: {commit_preview.message}"
    assert (commit_preview.data or {}).get("dry_run") is True
    assert (commit_preview.data or {}).get("would_apply") is True
    assert (commit_preview.data or {}).get("cumulative") is False

    after_commit_preview = CLIENT.transactions.get(hold_id)
    assert (after_commit_preview.data or {}).get("status") == "INFLIGHT"

    void_preview = CLIENT.transactions.bulk_void_inflight(
        {
            "dry_run": True,
            "skip_queue": True,
            "transaction_ids": [hold_id],
        }
    )
    assert void_preview.status == 200, f"bulk void dry-run: {void_preview.message}"
    assert (void_preview.data or {}).get("dry_run") is True

    after_void_preview = CLIENT.transactions.get(hold_id)
    assert (after_void_preview.data or {}).get("status") == "INFLIGHT"

    hooks = CLIENT.hooks.list()
    assert hooks.status in (200, 403), f"hooks list: {hooks.status}"

    negative = CLIENT.transactions.create(
        {
            "amount": -1,
            "precision": 100,
            "reference": generate_random_numbers_with_prefix("neg", 8),
            "description": "invalid amount",
            "currency": "USD",
            "source": indicator,
            "destination": dest,
            "allow_overdraft": True,
            "skip_queue": True,
        }
    )
    assert negative.status != 201
    assert negative.error is not None
    assert negative.error.code == BlnkErrorCode.TXN_VALIDATION_ERROR

    same_balance = CLIENT.transactions.create(
        {
            "amount": 10,
            "precision": 100,
            "reference": generate_random_numbers_with_prefix("same", 8),
            "description": "same source dest",
            "currency": "USD",
            "source": indicator,
            "destination": indicator,
            "allow_overdraft": True,
            "skip_queue": True,
        }
    )
    assert same_balance.status != 201
    assert same_balance.error is not None
    assert same_balance.error.code

    duplicate = CLIENT.ledger_balances.create(
        {
            "ledger_id": "general_ledger_id",
            "currency": "USD",
            "indicator": indicator,
        }
    )
    assert duplicate.status == 409
    assert duplicate.error is not None
    assert duplicate.error.code == BlnkErrorCode.GEN_CONFLICT
