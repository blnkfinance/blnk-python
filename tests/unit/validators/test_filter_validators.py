"""Unit tests for `validate_filter_params` —
`filter validators` (4 cases).
"""

from __future__ import annotations

from blnk_sdk.validators.search_validators import validate_filter_params


def test_validate_filter_params_accepts_api_valid_payload() -> None:
    """ValidateFilterParams accepts API-valid payload"""
    assert (
        validate_filter_params(
            {
                "filters": [
                    {"field": "status", "operator": "eq", "value": "APPLIED"},
                    {"field": "currency", "operator": "in", "values": ["USD", "EUR"]},
                ],
                "logical_operator": "and",
                "sort_by": "created_at",
                "sort_order": "desc",
                "include_count": True,
                "limit": 20,
                "offset": 0,
            }
        )
        is None
    )


def test_validate_filter_params_accepts_valueless_operators() -> None:
    """ValidateFilterParams accepts valueless operators"""
    assert (
        validate_filter_params(
            {
                "filters": [{"field": "identity_id", "operator": "isnull"}],
            }
        )
        is None
    )


def test_validate_filter_params_rejects_missing_values_for_in_operator() -> None:
    """ValidateFilterParams rejects missing values for in operator"""
    assert (
        validate_filter_params(
            {
                "filters": [{"field": "currency", "operator": "in"}],
            }
        )
        == 'filters[0].values must be a non-empty array for operator "in"'
    )


def test_validate_filter_params_rejects_invalid_logical_operator() -> None:
    """ValidateFilterParams rejects invalid logical_operator"""
    assert (
        validate_filter_params(
            {
                "filters": [{"field": "status", "operator": "eq", "value": "APPLIED"}],
                "logical_operator": "xor",
            }
        )
        == 'logical_operator must be "and" or "or" if provided'
    )
