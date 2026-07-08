"""Unit tests for the transaction serialization helpers
(4 cases under `transaction serialization`)."""

from __future__ import annotations

from datetime import datetime, timezone

from blnk_sdk.transaction_serialization import (
    is_valid_transaction_date_input,
    serialize_create_transaction,
    serialize_transaction_date,
)


def test_serializes_date_fields_to_iso_strings():
    """transaction serialization > serializes datetime fields to ISO strings"""
    effective_date = datetime(2025, 2, 15, 10, 30, tzinfo=timezone.utc)
    data = {
        "amount": 1000,
        "precision": 100,
        "reference": "ref_001",
        "description": "Backdated transaction",
        "currency": "USD",
        "source": "@FundingPool",
        "destination": "@Recipient",
        "effective_date": effective_date,
        "inflight_commit_date": datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
        "scheduled_for": datetime(2025, 7, 1, 8, 0, tzinfo=timezone.utc),
        "inflight_expiry_date": datetime(2025, 8, 1, 8, 0, tzinfo=timezone.utc),
    }

    serialized = serialize_create_transaction(data)

    assert serialized["effective_date"] == "2025-02-15T10:30:00Z"
    assert serialized["inflight_commit_date"] == "2025-06-01T12:00:00Z"
    assert serialized["scheduled_for"] == "2025-07-01T08:00:00Z"
    assert serialized["inflight_expiry_date"] == "2025-08-01T08:00:00Z"


def test_passes_through_iso_date_strings_unchanged():
    """transaction serialization > passes through ISO date strings unchanged"""
    data = {
        "amount": 1000,
        "precision": 100,
        "reference": "ref_002",
        "description": "Backdated transaction",
        "currency": "USD",
        "source": "@FundingPool",
        "destination": "@Recipient",
        "effective_date": "2025-02-15T10:30:00Z",
        "inflight_commit_date": "2025-06-01T12:00:00Z",
    }

    serialized = serialize_create_transaction(data)

    assert serialized["effective_date"] == "2025-02-15T10:30:00Z"
    assert serialized["inflight_commit_date"] == "2025-06-01T12:00:00Z"


def test_serializetransactiondate_returns_none_for_none_input():
    """transaction serialization > serialize_transaction_date returns None for None input"""
    assert serialize_transaction_date(None) is None


def test_accepts_core_example_datetime_formats():
    """transaction serialization > accepts Core example datetime formats"""
    # Core model_test inflight_commit_date example
    assert is_valid_transaction_date_input("2024-04-22T15:28:03+00:00")
    # Core time.Parse offset without colon
    assert is_valid_transaction_date_input("2024-04-22T15:28:03+0000")
    # fractional seconds rejected for string date fields
    assert not is_valid_transaction_date_input("2024-04-22T15:28:03.000Z")
