"""Unit tests for `BulkTransactionResponse`
(6 cases under `BulkTransactionResponse API shape`)."""

from __future__ import annotations

from blnk_sdk.types.transactions import BulkTransactionResponse
from tests.fixtures.core_bulk_transaction_response import (
    core_bulk_transaction_async_reference_response,
    core_bulk_transaction_reference_response,
)


def test_accepts_core_api_reference_sync_bulk_response():
    """BulkTransactionResponse API shape > accepts Core API reference sync bulk response"""
    response = BulkTransactionResponse.from_dict(
        core_bulk_transaction_reference_response
    )
    assert response.batch_id == "bulk_c62f200b-905f-4983-a349-cadd279234aa"
    assert response.status == "applied"
    assert response.transaction_count == 4


def test_accepts_core_api_reference_async_bulk_response():
    """BulkTransactionResponse API shape > accepts Core API reference async bulk response"""
    response = BulkTransactionResponse.from_dict(
        core_bulk_transaction_async_reference_response
    )
    assert response.batch_id == "bulk_c62f200b-905f-4983-a349-cadd279234aa"
    assert response.status == "queued"
    assert response.message == "Bulk transaction processing started"


def test_batch_id_field_is_present_on_reference_response():
    """BulkTransactionResponse API shape > batch_id field is present on reference response"""
    response = BulkTransactionResponse.from_dict(
        core_bulk_transaction_reference_response
    )
    assert response.batch_id


def test_status_field_is_present_on_reference_response():
    """BulkTransactionResponse API shape > status field is present on reference response"""
    response = BulkTransactionResponse.from_dict(
        core_bulk_transaction_reference_response
    )
    assert isinstance(response.status, str)


def test_transaction_count_is_optional_on_async_response():
    """BulkTransactionResponse API shape > transaction_count is optional on async response"""
    response = BulkTransactionResponse.from_dict(
        core_bulk_transaction_async_reference_response
    )
    assert response.transaction_count is None


def test_accepts_inflight_bulk_status():
    """BulkTransactionResponse API shape > accepts inflight bulk status"""
    inflight_response = BulkTransactionResponse(
        batch_id="bulk_4192d961-5b0e-46ca-bf2f-9386763057f8",
        status="inflight",
        transaction_count=2,
    )
    assert inflight_response.status == "inflight"
    assert inflight_response.transaction_count == 2
