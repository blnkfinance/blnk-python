"""Unit tests for the ledger-balance validators
(20 cases, direct validator calls).

Groups run in the order listed below.
Function names are prefixed with the group's validator name because case
names repeat across groups (e.g. `accepts from_source flag`).
"""

from __future__ import annotations

from blnk_sdk.validators.ledger_balance import (
    validate_create_balance_snapshot,
    validate_create_ledger_balance,
    validate_get_balance,
    validate_get_balance_at,
    validate_get_by_indicator,
    validate_update_balance_identity,
)

# --- ValidateGetByIndicator ------------------------------------


def test_get_by_indicator_accepts_valid_indicator_and_currency() -> None:
    """ValidateGetByIndicator > accepts valid indicator and currency"""
    assert validate_get_by_indicator("@World", "USD") is None


def test_get_by_indicator_rejects_empty_indicator() -> None:
    """ValidateGetByIndicator > rejects empty indicator"""
    assert validate_get_by_indicator("", "USD") == "indicator is required"


def test_get_by_indicator_rejects_empty_currency() -> None:
    """ValidateGetByIndicator > rejects empty currency"""
    assert validate_get_by_indicator("@World", "") == "currency is required"


# --- ValidateUpdateBalanceIdentity ------------------------------


def test_update_balance_identity_accepts_valid_identity_id() -> None:
    """ValidateUpdateBalanceIdentity > accepts valid identity_id"""
    assert (
        validate_update_balance_identity(
            {"identity_id": "idt_3b63c8da-af29-4cc3-ad38-df17d87456e6"}
        )
        is None
    )


def test_update_balance_identity_rejects_missing_identity_id() -> None:
    """ValidateUpdateBalanceIdentity > rejects missing identity_id"""
    assert validate_update_balance_identity({}) == "identity_id is required"


def test_update_balance_identity_rejects_empty_identity_id() -> None:
    """ValidateUpdateBalanceIdentity > rejects empty identity_id"""
    assert (
        validate_update_balance_identity({"identity_id": ""})
        == "identity_id is required"
    )


# --- ValidateCreateBalanceSnapshot ------------------------------


def test_create_balance_snapshot_accepts_empty_options() -> None:
    """ValidateCreateBalanceSnapshot > accepts empty options"""
    # Options omitted entirely are passed as None.
    assert validate_create_balance_snapshot(None) is None


def test_create_balance_snapshot_accepts_positive_batch_size() -> None:
    """ValidateCreateBalanceSnapshot > accepts positive batch_size"""
    assert validate_create_balance_snapshot({"batch_size": 500}) is None


def test_create_balance_snapshot_accepts_zero_batch_size() -> None:
    """ValidateCreateBalanceSnapshot > accepts zero batch_size"""
    assert validate_create_balance_snapshot({"batch_size": 0}) is None


def test_create_balance_snapshot_rejects_negative_batch_size() -> None:
    """ValidateCreateBalanceSnapshot > rejects negative batch_size"""
    assert (
        validate_create_balance_snapshot({"batch_size": -1})
        == "batch_size must be positive"
    )


# --- ValidateCreateLedgerBalance lineage fields -----------------


def test_create_ledger_balance_accepts_track_fund_lineage_and_allocation_strategy() -> None:
    """ValidateCreateLedgerBalance lineage fields > accepts
    track_fund_lineage and allocation_strategy"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "ldg_123",
                "currency": "USD",
                "identity_id": "idt_123",
                "track_fund_lineage": True,
                "allocation_strategy": "LIFO",
            }
        )
        is None
    )


def test_create_ledger_balance_accepts_request_without_lineage_fields() -> None:
    """ValidateCreateLedgerBalance lineage fields > accepts request
    without lineage fields"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "ldg_123",
                "currency": "USD",
            }
        )
        is None
    )


def test_create_ledger_balance_rejects_non_boolean_track_fund_lineage() -> None:
    """ValidateCreateLedgerBalance lineage fields > rejects
    non-boolean track_fund_lineage"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "ldg_123",
                "currency": "USD",
                "track_fund_lineage": "true",
            }
        )
        == "track_fund_lineage must be a boolean if provided"
    )


def test_create_ledger_balance_accepts_general_ledger_indicator() -> None:
    """ValidateCreateLedgerBalance > accepts indicator on general_ledger_id"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "general_ledger_id",
                "currency": "USD",
                "indicator": "@Revenue",
            }
        )
        is None
    )


def test_create_ledger_balance_rejects_indicator_without_at() -> None:
    """ValidateCreateLedgerBalance > rejects indicator that does not start with @"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "general_ledger_id",
                "currency": "USD",
                "indicator": "Revenue",
            }
        )
        == "indicator must start with @"
    )


def test_create_ledger_balance_rejects_indicator_with_spaces() -> None:
    """ValidateCreateLedgerBalance > rejects indicator with spaces"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "general_ledger_id",
                "currency": "USD",
                "indicator": "@Rev enue",
            }
        )
        == "indicator must not contain spaces"
    )


def test_create_ledger_balance_rejects_indicator_on_non_gl_ledger() -> None:
    """ValidateCreateLedgerBalance > rejects indicator unless ledger_id is general_ledger_id"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "ldg_123",
                "currency": "USD",
                "indicator": "@Revenue",
            }
        )
        == "indicator is only valid when ledger_id is general_ledger_id"
    )


def test_create_ledger_balance_rejects_empty_indicator() -> None:
    """ValidateCreateLedgerBalance > rejects empty indicator"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "general_ledger_id",
                "currency": "USD",
                "indicator": "",
            }
        )
        == "indicator must be a non-empty string if provided"
    )


def test_create_ledger_balance_rejects_invalid_allocation_strategy() -> None:
    """ValidateCreateLedgerBalance lineage fields > rejects invalid
    allocation_strategy"""
    assert (
        validate_create_ledger_balance(
            {
                "ledger_id": "ldg_123",
                "currency": "USD",
                "allocation_strategy": "INVALID",
            }
        )
        == "allocation_strategy must be one of FIFO, LIFO, or PROPORTIONAL"
    )


# --- ValidateGetBalance -----------------------------------------


def test_get_balance_accepts_from_source_flag() -> None:
    """ValidateGetBalance > accepts from_source flag"""
    assert validate_get_balance({"from_source": True}) is None


def test_get_balance_accepts_empty_options_object() -> None:
    """ValidateGetBalance > accepts empty options object"""
    assert validate_get_balance({}) is None


def test_get_balance_rejects_non_boolean_from_source() -> None:
    """ValidateGetBalance > rejects non-boolean from_source"""
    assert (
        validate_get_balance({"from_source": "true"})
        == "from_source must be a boolean if provided"
    )


def test_get_balance_accepts_with_queued_flag() -> None:
    """ValidateGetBalance > accepts with_queued flag"""
    assert validate_get_balance({"with_queued": True}) is None


def test_get_balance_rejects_non_boolean_with_queued() -> None:
    """ValidateGetBalance > rejects non-boolean with_queued"""
    assert (
        validate_get_balance({"with_queued": "true"})
        == "with_queued must be a boolean if provided"
    )


# --- ValidateGetBalanceAt ----------------------------------------


def test_get_balance_at_accepts_valid_timestamp() -> None:
    """ValidateGetBalanceAt > accepts valid timestamp"""
    assert validate_get_balance_at({"timestamp": "2025-02-24T08:55:26Z"}) is None


def test_get_balance_at_accepts_from_source_flag() -> None:
    """ValidateGetBalanceAt > accepts from_source flag"""
    assert (
        validate_get_balance_at(
            {
                "timestamp": "2025-02-24T08:55:26Z",
                "from_source": True,
            }
        )
        is None
    )


def test_get_balance_at_rejects_empty_timestamp() -> None:
    """ValidateGetBalanceAt > rejects empty timestamp"""
    assert validate_get_balance_at({"timestamp": ""}) == "timestamp is required"
