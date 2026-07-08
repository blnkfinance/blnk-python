"""Unit tests for `CreateTransactionResponse`
(7 cases under `CreateTransactionResponse API shape`)."""

from __future__ import annotations

from blnk_sdk.types.transactions import CreateTransactionResponse
from tests.fixtures.core_create_transaction_response import (
    core_create_transaction_reference_response,
)


def test_accepts_core_0_15_0_create_response_without_rate():
    """CreateTransactionResponse API shape > accepts Core 0.15.0 create response without rate"""
    response = CreateTransactionResponse.from_dict(
        {**core_create_transaction_reference_response}
    )
    assert response.rate is None


def test_accepts_core_api_reference_create_response():
    """CreateTransactionResponse API shape > accepts Core API reference create response"""
    response = CreateTransactionResponse.from_dict(
        core_create_transaction_reference_response
    )
    assert len(response.hash) == 64
    assert response.parent_transaction == ""
    assert response.allow_overdraft is False
    assert response.inflight is False
    assert response.scheduled_for == "0001-01-01T00:00:00Z"
    assert response.inflight_expiry_date == "0001-01-01T00:00:00Z"
    assert response.inflight_commit_date == "0001-01-01T00:00:00Z"


def test_hash_field_is_present_on_reference_response():
    """CreateTransactionResponse API shape > hash field is present on reference response"""
    response = CreateTransactionResponse.from_dict(
        core_create_transaction_reference_response
    )
    assert response.hash


def test_parent_transaction_field_is_present_on_reference_response():
    """CreateTransactionResponse API shape > parent_transaction field is present on reference response"""
    response = CreateTransactionResponse.from_dict(
        core_create_transaction_reference_response
    )
    assert isinstance(response.parent_transaction, str)


def test_allow_overdraft_field_is_present_on_reference_response():
    """CreateTransactionResponse API shape > allow_overdraft field is present on reference response"""
    response = CreateTransactionResponse.from_dict(
        core_create_transaction_reference_response
    )
    assert isinstance(response.allow_overdraft, bool)


def test_inflight_date_fields_use_iso_strings_on_reference_response():
    """CreateTransactionResponse API shape > inflight date fields use ISO strings on reference response"""
    response = CreateTransactionResponse.from_dict(
        core_create_transaction_reference_response
    )
    assert response.inflight_expiry_date == "0001-01-01T00:00:00Z"
    assert response.inflight_commit_date == "0001-01-01T00:00:00Z"
    assert response.scheduled_for == "0001-01-01T00:00:00Z"


def test_accepts_inflight_create_response_with_custom_dates():
    """CreateTransactionResponse API shape > accepts inflight create response with custom dates"""
    inflight_response = CreateTransactionResponse.from_dict(
        {
            **core_create_transaction_reference_response,
            "status": "INFLIGHT",
            "inflight": True,
            "inflight_expiry_date": "2026-12-31T23:59:59Z",
            "inflight_commit_date": "2024-04-22T15:28:03+00:00",
            "scheduled_for": "2025-12-31T23:59:59Z",
            "effective_date": "2025-02-15T10:30:00Z",
            "allow_overdraft": True,
        }
    )
    assert inflight_response.inflight_expiry_date == "2026-12-31T23:59:59Z"
    assert inflight_response.inflight_commit_date == "2024-04-22T15:28:03+00:00"
    assert inflight_response.allow_overdraft is True
