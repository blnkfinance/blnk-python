"""Unit tests for the ledger validators (5 cases).

Group 1: `ValidateUpdateLedger` (4 cases); group 2 is the single
case `ValidateCreateLedger still accepts valid create payloads`.
"""

from __future__ import annotations

from blnk_sdk.validators.ledger_validators import (
    validate_create_ledger,
    validate_update_ledger,
)

# --- ValidateUpdateLedger ---


def test_accepts_a_valid_name() -> None:
    """accepts a valid name"""
    data = {"name": "Updated Customer Savings Account"}
    assert validate_update_ledger(data) is None


def test_rejects_missing_name() -> None:
    """rejects missing name"""
    assert validate_update_ledger({}) == "name field must be a valid string"


def test_rejects_empty_name() -> None:
    """rejects empty name"""
    assert validate_update_ledger({"name": ""}) == "name field is required"


def test_rejects_whitespace_only_name() -> None:
    """rejects whitespace-only name"""
    assert validate_update_ledger({"name": "   "}) == "name field is required"


# --- top-level group 2 ---


def test_validate_create_ledger_still_accepts_valid_create_payloads() -> None:
    """ValidateCreateLedger still accepts valid create payloads"""
    data = {"name": "My Ledger"}
    assert validate_create_ledger(data) is None
