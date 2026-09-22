"""Unit tests for the search validators —
`search validators` (10 cases).

Error-message assertions are byte-exact `==`.
"""

from __future__ import annotations

from blnk_sdk.validators.search_validators import (
    validate_multi_search_params,
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


def test_validate_multi_search_params_accepts_well_formed_body() -> None:
    """ValidateMultiSearchParams accepts a well-formed body"""
    assert (
        validate_multi_search_params(
            {
                "searches": [
                    {"collection": "ledgers", "q": "savings"},
                    {"collection": "identities", "q": "jane", "per_page": 5},
                ]
            }
        )
        is None
    )


def test_validate_multi_search_params_rejects_missing_searches() -> None:
    """ValidateMultiSearchParams rejects null, missing, and empty searches"""
    assert (
        validate_multi_search_params(None)
        == "Multi-search params must be a valid object"
    )
    assert validate_multi_search_params({}) == "searches must be a non-empty array"
    assert (
        validate_multi_search_params({"searches": []})
        == "searches must be a non-empty array"
    )
    assert (
        validate_multi_search_params({"searches": "ledgers"})
        == "searches must be a non-empty array"
    )


def test_validate_multi_search_params_rejects_non_object_entry() -> None:
    """ValidateMultiSearchParams rejects a non-object entry"""
    assert (
        validate_multi_search_params({"searches": ["ledgers"]})
        == "searches[0] must be a valid object"
    )


def test_validate_multi_search_params_rejects_bad_collection() -> None:
    """ValidateMultiSearchParams rejects a missing or unknown collection"""
    assert (
        validate_multi_search_params({"searches": [{"q": "x"}]})
        == "searches[0].collection must be ledgers, transactions, balances, or identities"
    )
    assert (
        validate_multi_search_params(
            {
                "searches": [
                    {"collection": "ledgers", "q": "x"},
                    {"collection": "Ledgers", "q": "x"},
                ]
            }
        )
        == "searches[1].collection must be ledgers, transactions, balances, or identities"
    )


def test_validate_multi_search_params_prefixes_param_errors() -> None:
    """ValidateMultiSearchParams prefixes per-entry param errors"""
    assert (
        validate_multi_search_params(
            {
                "searches": [
                    {"collection": "ledgers", "q": "x"},
                    {"collection": "balances", "q": "x", "per_page": 500},
                ]
            }
        )
        == "searches[1]: per_page must be an integer between 1 and 250 if provided"
    )
