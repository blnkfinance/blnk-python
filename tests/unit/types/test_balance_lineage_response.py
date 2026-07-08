"""Unit tests for `BalanceLineageResponse`
(root `BalanceLineageResponse API shape`, 2 cases).

The response DTO is constructed from both the string and the numeric
minor-unit representations and its fields asserted.
"""

from __future__ import annotations

import dataclasses

from blnk_sdk.types.ledger_balances import (
    BalanceLineageResponse,
    LineageProviderBreakdown,
)

REFERENCE_RESPONSE = BalanceLineageResponse(
    balance_id="bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f",
    aggregate_balance_id="bln_aggregate_shadow_balance_id",
    total_with_lineage="7500",
    providers=[
        LineageProviderBreakdown(
            provider="stripe",
            amount="10000",
            available="7500",
            spent="2500",
            shadow_balance_id="bln_shadow_balance_id",
        )
    ],
)


def test_accepts_core_api_reference_response() -> None:
    """accepts Core API reference response"""
    assert REFERENCE_RESPONSE.balance_id == "bln_5ce86029-3c2e-4e2a-aae2-7fb931ca4c4f"
    assert len(REFERENCE_RESPONSE.providers) == 1
    assert REFERENCE_RESPONSE.providers[0].provider == "stripe"


def test_accepts_numeric_minor_unit_amounts() -> None:
    """accepts numeric minor-unit amounts"""
    numeric_response = dataclasses.replace(
        REFERENCE_RESPONSE,
        total_with_lineage=7500,
        providers=[
            dataclasses.replace(
                REFERENCE_RESPONSE.providers[0],
                amount=10000,
                available=7500,
                spent=2500,
            )
        ],
    )

    # bool is an int subclass, so it is excluded explicitly below.
    assert isinstance(numeric_response.total_with_lineage, (int, float))
    assert not isinstance(numeric_response.total_with_lineage, bool)
