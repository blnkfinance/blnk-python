"""Unit tests for `validate_run_instant_recon_data` (5 cases,
root `ValidateRunInstantReconData`).

VALID_DATA deliberately omits `dry_run`: an absent key is treated as
"not provided", so the dry_run check is skipped entirely.
"""

from __future__ import annotations

import re

from blnk_sdk.validators.reconciliation_validator import (
    validate_run_instant_recon_data,
)

VALID_DATA = {
    "external_transactions": [
        {
            "id": "txn_1",
            "amount": 5.49,
            "reference": "INV-2023-002",
            "currency": "GBP",
            "description": "Card payment",
            "date": "2024-11-15T14:25:30Z",
            "source": "bank-api",
        },
    ],
    "strategy": "one_to_one",
    "matching_rule_ids": ["rule_abc123"],
}


def test_accepts_valid_payload() -> None:
    """accepts valid payload"""
    assert validate_run_instant_recon_data(VALID_DATA) is None


def test_rejects_empty_external_transactions() -> None:
    """rejects empty external_transactions"""
    result = validate_run_instant_recon_data(
        {**VALID_DATA, "external_transactions": []}
    )
    # actual: `external_transactions must be a non-empty array`
    assert re.search(r"external_transactions", result)


def test_rejects_too_many_external_transactions() -> None:
    """rejects too many external_transactions"""
    txns = [
        {
            "id": f"txn_{i}",
            "amount": 1,
            "reference": f"ref_{i}",
            "currency": "USD",
            "description": "desc",
            "date": "2024-11-15T14:25:30Z",
            "source": "bank-api",
        }
        for i in range(10001)
    ]
    result = validate_run_instant_recon_data(
        {**VALID_DATA, "external_transactions": txns}
    )
    # actual: `too many external_transactions; max is 10000`
    assert re.search(r"too many external_transactions", result)


def test_rejects_invalid_strategy() -> None:
    """rejects invalid strategy"""
    result = validate_run_instant_recon_data({**VALID_DATA, "strategy": "invalid"})
    # actual: `strategy must be one of: one_to_one, one_to_many, many_to_one`
    assert re.search(r"strategy", result)


def test_rejects_empty_matching_rule_ids() -> None:
    """rejects empty matching_rule_ids"""
    result = validate_run_instant_recon_data(
        {**VALID_DATA, "matching_rule_ids": []}
    )
    # actual: `matching_rule_ids must be a non-empty array`
    assert re.search(r"matching_rule_ids", result)
