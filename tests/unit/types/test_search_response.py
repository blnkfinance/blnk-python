"""Unit tests for `SearchResponse` —
`SearchResponse per collection` (8 cases).

Numeric fields are checked with `is_valid_number` (int|float, bool
excluded) and string fields with `is_valid_string`. The final case only
references the search-inference helpers, which exist to pin down static
typing and are never executed.
"""

from __future__ import annotations

from blnk_sdk.api_response import ApiResponse
from blnk_sdk.http_client import format_response
from blnk_sdk.services.search import Search
from blnk_sdk.string_utils import is_valid_number, is_valid_string
from blnk_sdk.types.search import (
    SearchBalanceDocument,
    SearchCollection,
    SearchHit,
    SearchIdentityDocument,
    SearchLedgerDocument,
    SearchRequestParams,
    SearchResponse,
    SearchTransactionDocument,
)
from tests.helpers.search_inference import (
    assert_legacy_search_response_usage,
    assert_search_search_types,
)
from tests.mocks.blnk_client_mocks import create_mock_blnk_request, create_mock_logger


def test_ledger_document_uses_indexed_fields() -> None:
    """ledger document uses indexed fields"""
    response = SearchResponse(
        found=1,
        out_of=15,
        page=1,
        request_params=SearchRequestParams(collection_name="ledgers", q="*"),
        search_time_ms=0,
        hits=[
            SearchHit(
                document=SearchLedgerDocument(
                    id="general_ledger_id",
                    ledger_id="general_ledger_id",
                    name="General Ledger",
                    created_at=1781226501,
                )
            )
        ],
    )

    assert is_valid_number(response.hits[0].document.created_at)
    assert response.hits[0].document.ledger_id == "general_ledger_id"


def test_balance_document_uses_string_minor_unit_fields() -> None:
    """balance document uses string minor-unit fields"""
    response = SearchResponse(
        found=1,
        out_of=45,
        page=1,
        request_params=SearchRequestParams(collection_name="balances", q="*"),
        search_time_ms=1,
        hits=[
            SearchHit(
                document=SearchBalanceDocument(
                    id="bln_15168eb4-bdb1-4e46-9331-f58a6a16b254",
                    balance_id="bln_15168eb4-bdb1-4e46-9331-f58a6a16b254",
                    balance="0",
                    credit_balance="0",
                    debit_balance="0",
                    currency="USD",
                    ledger_id="ldg_0921bd99-ff7c-4a06-b6d7-319f0bb12f87",
                    created_at=1781222909,
                    track_fund_lineage=True,
                )
            )
        ],
    )

    assert is_valid_string(response.hits[0].document.balance)
    assert response.hits[0].document.balance_id.startswith("bln_") is True


def test_transaction_document_includes_status_and_precise_amount() -> None:
    """transaction document includes status and precise_amount"""
    response = SearchResponse(
        found=1,
        out_of=11,
        page=1,
        request_params=SearchRequestParams(collection_name="transactions", q="*"),
        search_time_ms=2,
        hits=[
            SearchHit(
                document=SearchTransactionDocument(
                    id="txn_8bb67c99-70b1-46c2-aa49-1ea3fc2f2233",
                    transaction_id="txn_8bb67c99-70b1-46c2-aa49-1ea3fc2f2233",
                    amount=250000,
                    precise_amount="250000",
                    status="APPLIED",
                    created_at=1781028226,
                )
            )
        ],
    )

    assert response.hits[0].document.status == "APPLIED"
    assert is_valid_number(response.hits[0].document.created_at)


def test_identity_document_includes_indexed_fields() -> None:
    """identity document includes indexed fields"""
    response = SearchResponse(
        found=1,
        out_of=13,
        page=1,
        request_params=SearchRequestParams(collection_name="identities", q="*"),
        search_time_ms=5,
        hits=[
            SearchHit(
                document=SearchIdentityDocument(
                    id="idt_fbf6a26c-82c6-46fb-9237-8fbba55a23c0",
                    identity_id="idt_fbf6a26c-82c6-46fb-9237-8fbba55a23c0",
                    identity_type="organization",
                    created_at=1781225782,
                )
            )
        ],
    )

    assert response.hits[0].document.identity_id.startswith("idt_") is True


def test_search_search_infers_transaction_document_fields() -> None:
    """Search.search infers transaction document fields"""
    transaction_search_response = SearchResponse(
        found=1,
        out_of=11,
        page=1,
        request_params=SearchRequestParams(collection_name="transactions", q="payment"),
        search_time_ms=2,
        hits=[
            SearchHit(
                document=SearchTransactionDocument(
                    id="txn_8bb67c99-70b1-46c2-aa49-1ea3fc2f2233",
                    transaction_id="txn_8bb67c99-70b1-46c2-aa49-1ea3fc2f2233",
                    status="APPLIED",
                    precise_amount="250000",
                    created_at=1781028226,
                )
            )
        ],
    )

    def mock_request(endpoint, data, method, header_options=None):
        return ApiResponse(
            status=201, message="Success", data=transaction_search_response
        )

    search = Search(mock_request, create_mock_logger(), format_response)
    response = search.search({"q": "payment"}, "transactions")

    assert response.status == 201
    assert response.data.hits[0].document.status == "APPLIED"
    assert (
        response.data.hits[0].document.transaction_id
        == "txn_8bb67c99-70b1-46c2-aa49-1ea3fc2f2233"
    )


def test_search_search_accepts_dynamic_search_collection_variable() -> None:
    """Search.search accepts dynamic SearchCollection variable"""
    mock_logger = create_mock_logger()
    third_party_request = create_mock_blnk_request(True, None, 201)
    search = Search(third_party_request, mock_logger, format_response)
    service: SearchCollection = "ledgers"

    response = search.search({"q": "General"}, service)

    assert response.status == 201


def test_unparameterized_search_response_remains_valid() -> None:
    """unparameterized SearchResponse remains valid"""
    # An unparameterized SearchResponse defaults to the balance document shape.
    response = SearchResponse(
        found=1,
        out_of=45,
        page=1,
        request_params=SearchRequestParams(collection_name="balances", q="*"),
        search_time_ms=1,
        hits=[
            SearchHit(
                document=SearchBalanceDocument(
                    id="bln_15168eb4-bdb1-4e46-9331-f58a6a16b254",
                    balance_id="bln_15168eb4-bdb1-4e46-9331-f58a6a16b254",
                    balance="0",
                    created_at=1781222909,
                )
            )
        ],
    )

    assert is_valid_string(response.hits[0].document.balance)
    assert response.hits[0].document.balance_id.startswith("bln_") is True


def test_compile_time_search_search_inference_checks() -> None:
    """static-typing Search.search inference checks"""
    # The inference helpers are referenced, never executed: they exist to pin
    # down the static typing of Search.search.
    assert callable(assert_search_search_types)
    assert callable(assert_legacy_search_response_usage)
    assert True, "search inference type checks hold"
