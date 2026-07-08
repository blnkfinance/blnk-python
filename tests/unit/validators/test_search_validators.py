"""Unit tests for the search validators —
`search validators` (5 cases).

Error-message assertions are byte-exact `==`.
"""

from __future__ import annotations

from blnk_sdk.validators.search_validators import (
    validate_search_collection,
    validate_search_params,
)


def test_validate_search_collection_accepts_identities() -> None:
    """ValidateSearchCollection accepts identities"""
    assert validate_search_collection("identities") is None
    assert validate_search_collection("ledgers") is None


def test_validate_search_collection_rejects_unknown_collection() -> None:
    """ValidateSearchCollection rejects unknown collection"""
    assert (
        validate_search_collection("accounts")
        == "collection must be ledgers, transactions, balances, or identities"
    )


def test_validate_search_params_accepts_api_valid_payload() -> None:
    """ValidateSearchParams accepts API-valid payload"""
    assert (
        validate_search_params(
            {
                "q": "*",
                "query_by": "first_name,last_name,email_address",
                "filter_by": "identity_type:=individual",
                "sort_by": "created_at:desc",
                "page": 1,
                "per_page": 25,
            }
        )
        is None
    )


def test_validate_search_params_rejects_empty_q() -> None:
    """ValidateSearchParams rejects empty q"""
    assert validate_search_params({"q": ""}) == 'Field "q" must be filled'


def test_validate_search_params_rejects_invalid_page() -> None:
    """ValidateSearchParams rejects invalid page"""
    assert (
        validate_search_params({"q": "*", "page": 0})
        == "page must be a positive integer if provided"
    )
